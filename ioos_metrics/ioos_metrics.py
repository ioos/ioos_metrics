"""Code extracted from IOOS_BTN.ipynb."""

import functools
import io
import logging

import httpx
import joblib
import pandas as pd
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from gliderpy.fetchers import GliderDataFetcher
from shapely.geometry import LineString, Point

from ioos_metrics.national_platforms import national_platforms

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="metrics.log",
    encoding="utf-8",
    level=logging.INFO,
)

ua = UserAgent()
_HEADERS = {
    "User-Agent": ua.random,
}


@functools.lru_cache(maxsize=128)
def previous_metrics():
    """Loads the previous metrics as a DataFrame for updating."""
    df = pd.read_csv(
        "https://github.com/ioos/ioos_metrics/raw/main/ioos_btn_metrics.csv",
    )

    number_cols = [
        "Federal Partners",
        "Regional Associations",
        "HF Radar Stations",
        "NGDAC Glider Days",
        "National Platforms",
        "Regional Platforms",
        "ATN Deployments",
        "MBON Projects",
        "OTT Projects",
        "HAB Pilot Projects",
        "QARTOD Manuals",
        "IOOS Core Variables",
        "Metadata Records",
        "IOOS",
        "COMT Projects",
    ]
    df[number_cols] = df[number_cols].astype("Int64")
    return df


def _compare_metrics(column, num) -> str:
    """Compares last stored metric against the new one and report if it is up, down, or the same."""
    last_row = previous_metrics().iloc[-1]
    date = last_row["date_UTC"]
    if num is None:
        return f"[{date}] : {column} failed."

    old = last_row[column]
    if old == num:
        msg = f"[{date}] : {column} equal {num} = {old}."
    elif num < old:
        msg = f"[{date}] : {column} down {num} < {old}."
    elif num > old:
        msg = f"[{date}] : {column} up {num} > {old}."
    else:
        msg = f"[{date}] : {column} failed."
    return msg


@functools.lru_cache(maxsize=128)
def federal_partners():
    """ICOOS Act/COORA.

    Typically 17, from https://ioos.noaa.gov/community/national#federal.

    """
    url = "https://ioos.noaa.gov/community/national#federal"

    html = requests.get(url, headers=_HEADERS, timeout=10).text

    df = pd.read_html(io.StringIO(html))
    df_clean = df[1].drop(columns=[0, 2])
    df_fed_partners = pd.concat([df_clean[1], df_clean[3]]).dropna().reset_index()
    logger.info(f"{df_fed_partners[0].to_string()=}")
    return df_fed_partners.shape[0]


@functools.lru_cache(maxsize=128)
def ngdac_gliders_fast(min_time="2000-01-01T00:00:00Z", max_time="2023-12-31T23:59:59Z") -> int:
    """NGDAC Glider Days.

    This version uses the AllDatasets entry to compute the glider days.
    It will include NaNs and, b/c of that, will return an "overestimation" for that metric.
    One could argue that this is correct b/c a glider day at sea, with or without data, is a glider day.
    However, for an "accurate" glider day estimation that uses only where data is collected, use ngdac_gliders.

    Gliders monitor water currents, temperature, and conditions that reveal effects from storms,
    impacts on fisheries, and the quality of our water.
    This information creates a more complete picture of what is happening in the ocean,
    as well as trends scientists might be able to detect.
    U.S. IOOS began counting “Glider days” in 2008 with the intent to better coordinate across
    U.S. glider operations and to increase the data sharing and data management of this technology.
    One "Glider Day" is defined as 1 glider in the water collecting data for 1 day.

    From https://gliders.ioos.us/erddap/info/index.html?page=1&itemsPerPage=1000

    Cumulative from 2008 - present

    Conditions on our calculations:
    * drops all datasets with `datasetID` containing `delayed`.
    * duration is calculated based on the metadata ERDDAP generates
      (time_coverage) which usually over-estimate a bit b/c it includes empty data (NaN).
      Note that data with NaN can be real glider day with lost data. Which is OK for this metric.

    """
    df = pd.read_csv(
        "https://gliders.ioos.us/erddap/tabledap/allDatasets.csvp?minTime,maxTime,datasetID",
    )

    # We don't want allDatasets in our numbers.
    df = df.loc[~(df["datasetID"] == "allDatasets")]

    # Check if any value is NaN and report it.
    if df.isna().sum().sum():
        rows = df.loc[df.isna().sum(axis=1).astype(bool)]
        logger.warning(f"The following rows have missing data:\n{rows}")

    df = df.dropna(
        axis=0,
    )

    # drop delayed datasets
    df = df.loc[~df["datasetID"].str.contains("delayed")]

    df[["minTime (UTC)", "maxTime (UTC)"]] = df[["minTime (UTC)", "maxTime (UTC)"]].apply(pd.to_datetime)

    min_time = pd.to_datetime(min_time)
    max_time = pd.to_datetime(max_time)

    df = df.loc[(df["minTime (UTC)"] >= min_time) & (df["maxTime (UTC)"] <= max_time)]

    df = df["maxTime (UTC)"].apply(lambda x: x.ceil("D")) - df["minTime (UTC)"].apply(
        lambda x: x.floor("D"),
    )
    return df.sum().days


@functools.lru_cache(maxsize=128)
def _ngdac_gliders(*, min_time, max_time, min_lat, max_lat, min_lon, max_lon) -> pd.DataFrame:  # noqa: PLR0913
    """Loops over all datasets found within the bounding box and time-range,
    and returns a more accurate estimate for this metric.

    This approach can compute more refined metrics and other variables,
    like glider profiles and hurricane overlaps.
    """

    def _extra_info(info_df, attribute_name) -> str:
        """Get 'Attribute Name' 'Value' metadata."""
        att = info_df.loc[info_df["Attribute Name"] == attribute_name]["Value"].squeeze()
        if hasattr(att, "empty"):
            att = "unknown"
        return att

    def _fix_glider_call_names(fname: str) -> str:
        fname = fname.split("-")
        fname.pop()
        return "-".join(fname).strip()

    def _metadata(info_df) -> dict:
        """Build the metadata a specific dataset_id."""
        return {
            "wmo_id": _extra_info(info_df, attribute_name="wmo_id"),
            "time_coverage_start": _extra_info(
                info_df,
                attribute_name="time_coverage_start",
            ),
            "time_coverage_end": _extra_info(
                info_df,
                attribute_name="time_coverage_end",
            ),
            "glider": _fix_glider_call_names(dataset_id),
            "geospatial_lat_min": _extra_info(
                info_df,
                attribute_name="geospatial_lat_min",
            ),
            "geospatial_lat_max": _extra_info(
                info_df,
                attribute_name="geospatial_lat_max",
            ),
            "geospatial_lon_min": _extra_info(
                info_df,
                attribute_name="geospatial_lon_min",
            ),
            "geospatial_lon_max": _extra_info(
                info_df,
                attribute_name="geospatial_lon_max",
            ),
            "institution": _extra_info(info_df, attribute_name="institution"),
            "sea_name": _extra_info(info_df, attribute_name="sea_name"),
            "acknowledgment": _extra_info(
                info_df,
                attribute_name="acknowledgment",
            ),
        }

    def _make_track_geom(df) -> "pd.DataFrame":
        geom = Point if df.shape[0] == 1 else LineString

        return geom(
            (lon, lat)
            for (lon, lat) in zip(
                df["longitude (degrees_east)"],
                df["latitude (degrees_north)"],
                strict=False,
            )
        )

    def _computed_metadata(dataset_id) -> dict:
        """Download the minimum amount of data possible for the computed
        metadata.

        Note that we cannot get first and last b/c the profile_id is not a
        contiguous sequence.
        """
        glider_grab.fetcher.dataset_id = dataset_id
        glider_grab.fetcher.variables = [
            "profile_id",
            "latitude",
            "longitude",
            "time",
        ]
        df = glider_grab.fetcher.to_pandas(distinct=True)
        df["time (UTC)"] = pd.to_datetime(df["time (UTC)"])
        df = df.set_index("time (UTC)")
        df = df.sort_index()
        track = _make_track_geom(df)
        days = df.index[-1].ceil("D") - df.index[0].floor("D")
        return {
            "deployment_lat": df["latitude (degrees_north)"].iloc[0],
            "deployment_lon": df["longitude (degrees_east)"].iloc[0],
            "num_profiles": len(df),
            # Profiles are not unique! Cannot use this!!
            # "num_profiles": len(set(df['profile_id']))
            "days": days,
            "track": track,
        }

    glider_grab = GliderDataFetcher()

    df = glider_grab.query(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        min_time=min_time,
        max_time=max_time,
        delayed=False,  # We do not want delayed gliders.
    )

    metadata = {}
    for _, row in list(df.iterrows()):
        dataset_id = row["Dataset ID"]
        info_url = row["info_url"].replace("html", "csv")
        info_df = pd.read_csv(info_url)
        info = _metadata(info_df)
        try:
            info.update(_computed_metadata(dataset_id=dataset_id))
        except (httpx.HTTPError, httpx.HTTPStatusError):
            print(  # noqa: T201
                f"Could not fetch glider {dataset_id=}. "
                "This could be a server side error and the metrics will be incomplete!",
            )
            continue
        metadata.update({dataset_id: info})
    return pd.DataFrame(metadata).T


def ngdac_gliders():
    """Runs _ngdac_gliders for the whole server and returns only the glider days to compare with ngdac_gliders_fast."""
    metadata = _ngdac_gliders()
    return metadata["days"].sum().days


@functools.lru_cache(maxsize=128)
def comt():
    """The COMT serves as a conduit between the federal operational
    and research communities and allows sharing of numerical models,
    observations and software tools.
    The COMT supports integration, comparison,
    scientific analyses and archiving of data and model output needed to elucidate,
    prioritize, and resolve federal and regional operational coastal ocean issues associated with
    a range of existing and emerging coastal oceanic,
    hydrologic, and ecological models.
    The Testbed has enabled significant community building
    (within the modeling community as well as enhancing academic and federal operational relations)
    which has dramatically improved model development.

    Number of Active Projects via personal communication from COMT program manager.
    """
    url = "https://ioos.noaa.gov/project/comt/"

    html = requests.get(url, headers=_HEADERS, timeout=10).text

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("h2"):
        if tag.text == "Current Projects":
            logger.info(f"{tag.next_sibling.find_all('li')=}")
            comt = len(tag.next_sibling.find_all("li"))

    return comt


@functools.lru_cache(maxsize=128)
def regional_associations():
    """Finds the current IOOS Regional Associations."""
    ras = 0
    url = "https://ioos.noaa.gov/regions/regions-at-a-glance/"

    html = requests.get(url, headers=_HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("a"):
        if tag.find("strong") is not None:
            logger.info(f"{tag.find('strong').text=}")
            ras += 1

    return ras


@functools.lru_cache(maxsize=128)
def regional_platforms():
    """Regional platforms are calculated from the annual IOOS asset inventory submitted by each Regional Association.
    More information about the IOOS asset inventory can be found at https://github.com/ioos/ioos-asset-inventory.

    The data from 2020 can be found
    [here](https://github.com/ioos/ioos-asset-inventory/tree/main/2020)
    and is available on [ERDDAP](http://erddap.ioos.us/erddap/tabledap/processed_asset_inventory.html).

    """
    url = "https://erddap.ioos.us/erddap/tabledap/processed_asset_inventory.json?station_long_name&distinct()"
    df = pd.read_json(url)
    return len(df.loc["rows"].iloc[0])


@functools.lru_cache(maxsize=128)
def atn_deployments():
    """See Deployments at https://portal.atn.ioos.us/#."""
    headers = {"Accept": "application/json"}

    raw_payload = requests.get(
        "https://search.axds.co/v2/search?portalId=99",
        headers=headers,
        timeout=10,
    )
    json_payload = raw_payload.json()
    for plt in json_payload["types"]:
        if plt["id"] == "platform2":
            atn = plt["count"]
            break
    return atn


@functools.lru_cache(maxsize=128)
def ott_projects():
    """The IOOS Ocean Technology Transition project sponsors the transition of emerging marine observing technologies,
    for which there is an existing operational requirement
    and a demonstrated commitment to integration and use by the ocean observing community,
    to operational mode.
    Each year IOOS supports 2-4 projects.
    The number here reflects the total number projects supported by this effort.

    These are the current active OTT projects which was provided by the OTT Program Manager.
    Hopefully, we can find a good place to harvest these numbers from.

    For now, we have the
    [website](https://ioos.noaa.gov/project/ocean-technology-transition/)
    and personal communication that there are 8 live projects.

    """
    url = "https://ioos.noaa.gov/project/ocean-technology-transition/"

    html = requests.get(url, headers=_HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find(attrs={"class": "fg-text-dark ffb-one-desc-2-2"})
    table = str(table)

    df = pd.read_html(
        io.StringIO(table),
        header=0,
    )

    ott_projects = 0
    for entry in df[0]:
        logger.info(f"{df[0][entry][0].count('new in')=}")
        ott_projects += df[0][entry][0].count("new in")
    return ott_projects


@functools.lru_cache(maxsize=128)
def qartod_manuals():
    """As of the last update there are twelve QARTOD manuals in-place for IOOS.
    These manuals establish authoritative QA/QC procedures for oceanographic data.

    The five year plan lists 16 manuals/papers.
    There's 13 QC manuals plus the Flags document,
    the QA paper and the Glider DAC paper.
    The Glider DAC paper is an implementation plan of the TS QC manual,
    and it's posted under the Implementation tab on the QARTOD home page,
    at https://cdn.ioos.noaa.gov/media/2017/12/Manual-for-QC-of-Glider-Data_05_09_16.pdf.


    https://ioos.noaa.gov/project/qartod/

    """
    url = "https://ioos.noaa.gov/project/qartod/"

    soup = BeautifulSoup(
        requests.get(url, headers=_HEADERS, timeout=10).text,
        "html.parser",
    )
    qartod = 0
    for tag in soup.find_all("li"):
        if "Real-Time Quality Control of" in tag.text:
            logger.info(f"{tag.text=}")
            qartod += 1

    return qartod


@functools.lru_cache(maxsize=128)
def ioos_core_variables():
    """The IOOS Core Variables are presented on
    [this website](https://www.iooc.us/task-teams/core-ioos-variables/).

    """
    url = "https://mmisw.org/ont/api/v0/ont?format=rj&iri=http://mmisw.org/ont/ioos/core_variable"

    df = pd.read_json(url, orient="index")

    # Drop the rows where 'name' doesn't exist.
    df = df.dropna(
        axis="index",
        how="any",
        subset="http://mmisw.org/ont/ioos/core_variable/name",
    )

    return len(df.index.tolist())


@functools.lru_cache(maxsize=128)
def metadata_records():
    """These are the number of metadata records currently available through the
    [IOOS Catalog](https://data.ioos.us).
    Previously the number of records was on the order of 8,600.
    Below are three different mechanisms to calculate this metric,
    however they do differ and the reason for that difference is unclear.

    """
    from ckanapi import RemoteCKAN

    url = "https://data.ioos.us"
    user_agent = "ckanapiioos/1.0 (+https://ioos.us/)"

    ioos_catalog = RemoteCKAN(url, user_agent=user_agent)
    datasets = ioos_catalog.action.package_search()
    return datasets["count"]


@functools.lru_cache(maxsize=128)
def ioos() -> int:
    """Represents the one IOOS Office."""
    return 1


@functools.lru_cache(maxsize=128)
def mbon_projects():
    """Living marine resources are essential to the health and recreational needs of billions of people,
    yet marine biodiversity and ecosystem processes remain major frontiers in ocean observing.
    IOOS has a critical role in implementing operational,
    sustained programs to observe biology and catalogue biodiversity to ensure these data are available for science,
    management, and the public.
    IOOS is leading development of the Marine Biodiversity Observation Network,
    with core funding from NOAA, NASA and BOEM.
    MBON connects regional networks of scientists, resource managers,
    and users and integrates data from existing long-term programs to understand human-
    and climate-induced change and its impacts on marine life.
    MBON partners are pioneering application of new remote sensing methods, imaging,
    molecular approaches (eDNA and omics),
    and other technologies and integrating these with traditional research methods
    and coordinated experiments to understand changing patterns of biodiversity.

    These are the currently funded MBON projects.
    At this time, we are manually checking https://marinebon.org/ and counting the number of U.S. projects.

    We hope to be able to use the resources
    [here](https://github.com/marinebon/www_marinebon2/tree/master/content/project)
    to automatically harvest these metrics in the future.

    """
    url = "https://ioos.noaa.gov/project/mbon/"
    html = requests.get(url, headers=_HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    mbon_projects = 0
    for tag in soup.find_all("h3"):
        if "class" in tag.attrs:
            continue  # we don't need the other headers
        mbon_projects += 1

    return mbon_projects


@functools.lru_cache(maxsize=128)
def hab_pilot_projects():
    """These are the National Harmful Algal Bloom Observing Network Pilot Project awards.
    Currently these were calculated from the
    [award announcement pdf](https://cdn.ioos.noaa.gov/media/2021/10/NHABON-Funding-Awards-FY21_v2.pdf)
    which states that there are 9 total.

    Might be able to parse the pdf and calculate this on the fly.

    """
    from pdfminer.high_level import extract_text

    url = "https://cdn.ioos.noaa.gov/media/2022/10/NHABON-Funding-Awards-FY22.pdf"

    data = requests.get(url, timeout=10)

    with io.BytesIO(data.content) as f:
        pdf = extract_text(f)

    content = pdf.split("\n")

    nhabon_projects = sum("Funded amount" in s for s in content)
    return nhabon_projects + 1  # Gulf of Mexico project


@functools.lru_cache(maxsize=128)
def hf_radar_installations():
    """The previous number of 181 included all locations where
    a HFR station had ever been sighted as part of the IOOS National Network,
    but doesn't appear to me to have accounted for temporary installations,
    HFRs unfunded by IOOS operated by international partners,
    or instances where an HFR being relocated from one site to another caused it to be double-counted.
    Even the number 165 represents a "high water mark" for simultaneously operating HFRs,
    since HFRs routinely are taken offline for periods of time,
    for both planned preventative maintenance and in response to other exigent issues.

    From http://hfrnet.ucsd.edu/sitediag/stationList.php

    """
    # This is a hardcoded number at the moment!
    return 165


@functools.lru_cache(maxsize=128)
def mbon_stats():
    """Collects download statistics about MBON affiliated datasets shared with the Ocean Biodiversity
    Information System (OBIS) and the Global Biodiversity Information Framework (GBIF). The function returns a
    dataframe with rows corresponding to each paper citing a dataset.
    """
    import urllib.parse

    import pyobis

    # collect dataset information from OBIS
    institution_id = 23070
    query = pyobis.dataset.search(instituteid=institution_id)
    df = pd.DataFrame(query.execute())
    df_obis = pd.DataFrame.from_records(df["results"])
    df_obis.columns = [f"obis_{col}" for col in df_obis.columns]

    df_mapping = pd.DataFrame()
    base_url = "https://api.gbif.org"
    # iterate through each OBIS dataset to gather uuid from GBIF
    # create a mapping table
    for title in df_obis["obis_title"]:
        string = title
        query = f"{base_url}/v1/dataset/search?q={urllib.parse.quote(string)}"
        df = pd.read_json(query, orient="index").T

        # build a DataFrame with the info we need more accessible
        df_mapping = pd.concat(
            [
                df_mapping,
                pd.DataFrame(
                    {
                        "gbif_uuid": df["results"].to_numpy()[0][0]["key"],
                        "title": [df["results"].to_numpy()[0][0]["title"]],
                        "obis_id": [df_obis.loc[df_obis["obis_title"] == title, "obis_id"].to_string(index=False)],
                        "doi": [df["results"].to_numpy()[0][0]["doi"]],
                    },
                ),
            ],
            ignore_index=True,
        )

    df_gbif = pd.DataFrame()
    for key in df_mapping["gbif_uuid"]:
        url = f"https://api.gbif.org/v1/literature/export?format=CSV&gbifDatasetKey={key}"
        df2 = pd.read_csv(url)  # collect literature cited information
        df2.columns = ["literature_" + str(col) for col in df2.columns]
        df2["gbif_uuid"] = key

        df_gbif = pd.concat([df2, df_gbif], ignore_index=True)

    # merge the OBIS and GBIF data frames together
    df_obis = df_obis.merge(df_mapping, on="obis_id")

    # add gbif download stats

    for key in df_obis["gbif_uuid"]:
        url = f"https://api.gbif.org/v1/occurrence/download/statistics/export?datasetKey={key}"
        df2 = pd.read_csv(url, sep="\t")
        df2_group = df2.groupby("year").agg({"number_downloads": "sum"})

        df_obis.loc[df_obis["gbif_uuid"] == key, "gbif_downloads"] = str(df2_group.to_dict())

    return df_gbif.merge(df_obis, on="gbif_uuid")


def update_metrics(*, debug=False):
    """Load previous metrics and update the spreadsheet."""
    df = previous_metrics()
    today = pd.Timestamp.strftime(pd.Timestamp.today(tz="UTC"), "%Y-%m-%d")

    new_row = {
        "date_UTC": today,
    }

    functions = {
        "ATN Deployments": atn_deployments,
        "COMT Projects": comt,
        "Federal Partners": federal_partners,
        "HAB Pilot Projects": hab_pilot_projects,
        "HF Radar Stations": hf_radar_installations,
        "IOOS Core Variables": ioos_core_variables,
        "IOOS": ioos,
        "MBON Projects": mbon_projects,
        "Metadata Records": metadata_records,
        "National Platforms": national_platforms,
        "NGDAC Glider Days": ngdac_gliders_fast,
        "OTT Projects": ott_projects,
        "QARTOD Manuals": qartod_manuals,
        "Regional Associations": regional_associations,
        "Regional Platforms": regional_platforms,
    }

    # We cannot write the log in parallel. When debugging we should run the queries in seral mode.
    if debug:
        for column, function in functions.items():
            try:
                num = function()
            except Exception:
                logger.exception(f"{column=} failed.")
                num = None
            new_row.update({column: num})
            # Log status.
            message = _compare_metrics(column=column, num=num)
            logger.info(f"{message}")
    else:
        cpu_count = joblib.cpu_count()
        parallel = joblib.Parallel(n_jobs=cpu_count, return_as="generator")

        values = parallel(joblib.delayed(function)() for function in functions.values())
        columns = dict(zip(functions.keys(), values, strict=False))
        new_row.update(columns)

    new_row = pd.DataFrame.from_dict(data=new_row, orient="index").T

    # only update numbers if it's a new day
    if today not in df["date_UTC"].to_list():
        df = pd.concat(
            [df, new_row],
            ignore_index=True,
            axis=0,
        )

    return df
