"""
Code extracted from IOOS_BTN.ipynb

"""

import functools
import io
import logging
import warnings

import pandas as pd
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logging.basicConfig(filename="metric.log", encoding="utf-8", level=logging.DEBUG)

ua = UserAgent()
_HEADERS = {
    "User-Agent": ua.random,
}


@functools.lru_cache(maxsize=128)
def previous_metrics():
    """
    Loads the previous metrics as a DataFrame for updating.

    """
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


def _compare_metrics(column, num):
    """
    Compares last stored metric against the new one and report if it is up, down, or the same.

    """
    last_row = previous_metrics().iloc[-1]
    date = last_row["date_UTC"]
    if num is None:
        return f"[{date}] : {column} failed."
    old = last_row[column]
    if old == num:
        return f"[{date}] : {column} equal {num} = {old}."
    elif num < old:
        return f"[{date}] : {column} down {num} < {old}."
    elif num > old:
        return f"[{date}] : {column} up {num} > {old}."
    else:
        return f"[{date}] : {column} failed."


def federal_partners():
    """
    ICOOS Act/COORA

    Typically 17, from https://ioos.noaa.gov/community/national#federal.

    """

    url = "https://ioos.noaa.gov/community/national#federal"

    html = requests.get(url, headers=_HEADERS).text

    df = pd.read_html(io.StringIO(html))
    df_clean = df[1].drop(columns=[0, 2])
    df_fed_partners = pd.concat([df_clean[1], df_clean[3]]).dropna().reset_index()
    logging.info(f"{df_fed_partners[0].to_string()=}")
    return df_fed_partners.shape[0]


def ngdac_gliders(start_date="2000-01-01", end_date="2023-12-31"):
    """
    NGDAC Glider Days

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
    * duration is calculated based on the metadata ERDDAP generates (time_coverage) which usually over-estimate a bit b/c it includes empty data (NaN).
      Note that data with NaN can be real glider day with lost data. Which is OK for this metric.

    """
    df = pd.read_csv(
        "https://gliders.ioos.us/erddap/tabledap/allDatasets.csvp?minTime,maxTime,datasetID",
    )

    # We don't want allDatasets in our numbers.
    df = df.loc[~(df["datasetID"] == "allDatasets")]
    df.describe().T["count"]

    # Check if any value is NaN and report it.
    if df.isnull().sum().sum():
        rows = df.loc[df.isnull().sum(axis=1).astype(bool)]
        logging.warning(f"The following rows have missing data:\n{rows}")

    df.dropna(
        axis=0,
        inplace=True,
    )

    # drop delayed datasets
    df = df.loc[df["datasetID"].str.contains("delayed") == False]

    df[["minTime (UTC)", "maxTime (UTC)"]] = df[
        ["minTime (UTC)", "maxTime (UTC)"]
    ].apply(pd.to_datetime)

    df = df["maxTime (UTC)"].apply(lambda x: x.ceil("D")) - df["minTime (UTC)"].apply(
        lambda x: x.floor("D"),
    )
    return df.sum().days


def comt():
    """
    The COMT serves as a conduit between the federal operational and research communities and allows sharing of numerical models,
    observations and software tools.
    The COMT supports integration, comparison, scientific analyses and archiving of data and model output needed to elucidate,
    prioritize, and resolve federal and regional operational coastal ocean issues associated with a range of existing and emerging coastal oceanic,
    hydrologic, and ecological models.
    The Testbed has enabled significant community building (within the modeling community as well as enhancing academic and federal operational relations) which has dramatically improved model development.

    Number of Active Projects via personal communication from COMT program manager.
    """

    url = "https://ioos.noaa.gov/project/comt/"

    html = requests.get(url, headers=_HEADERS).text

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("h2"):
        if tag.text == "Current Projects":
            logging.info(f"{tag.next_sibling.find_all('li')=}")
            comt = len(tag.next_sibling.find_all("li"))

    return comt


def regional_associations():
    """
    Finds the current IOOS Regional Associations.

    """
    ras = 0
    url = "https://ioos.noaa.gov/regions/regions-at-a-glance/"

    html = requests.get(url, headers=_HEADERS).text
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("a"):
        if tag.find("strong") is not None:
            logging.info(f"{tag.find('strong').text=}")
            ras += 1

    return ras


def regional_platforms():
    """
    Regional platforms are calculated from the annual IOOS asset inventory submitted by each Regional Association.
    More information about the IOOS asset inventory can be found at https://github.com/ioos/ioos-asset-inventory

    The data from 2020 can be found
    [here](https://github.com/ioos/ioos-asset-inventory/tree/main/2020)
    and is available on [ERDDAP](http://erddap.ioos.us/erddap/tabledap/processed_asset_inventory.html).

    """

    url = "https://erddap.ioos.us/erddap/tabledap/processed_asset_inventory.json?station_long_name&distinct()"
    df = pd.read_json(url)
    return len(df.loc["rows"].iloc[0])


def atn_deployments():
    """
    See Deployments at https://portal.atn.ioos.us/#

    """

    headers = {"Accept": "application/json"}

    raw_payload = requests.get(
        "https://search.axds.co/v2/search?portalId=99",
        headers=headers,
    )
    json_payload = raw_payload.json()
    for plt in json_payload["types"]:
        if plt["id"] == "platform2":
            atn = plt["count"]
            break
    return atn


def ott_projects():
    """
    The IOOS Ocean Technology Transition project sponsors the transition of emerging marine observing technologies,
    for which there is an existing operational requirement and a demonstrated commitment to integration and use by the ocean observing community,
    to operational mode.
    Each year IOOS supports 2-4 projects.
    The number here reflects the total number projects supported by this effort.

    These are the current active OTT projects which was provided by the OTT Program Manager.
    Hopefully, we can find a good place to harvest these numbers from.

    For now, we have the [website](https://ioos.noaa.gov/project/ocean-technology-transition/) and personal communication that there are 8 live projects.

    """
    url = "https://ioos.noaa.gov/project/ocean-technology-transition/"

    html = requests.get(url, headers=_HEADERS).text
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find(attrs={"class": "fg-text-dark ffb-one-desc-2-2"})
    table = str(table)

    df = pd.read_html(
        io.StringIO(table),
        header=0,
    )

    ott_projects = 0
    for entry in df[0]:
        logging.info(f"{df[0][entry][0].count('new in')=}")
        ott_projects += df[0][entry][0].count("new in")
    return ott_projects


def qartod_manuals():
    """
    As of the last update there are twelve QARTOD manuals in-place for IOOS.
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

    soup = BeautifulSoup(requests.get(url, headers=_HEADERS).text, "html.parser")
    qartod = 0
    for tag in soup.find_all("li"):
        if "Real-Time Quality Control of" in tag.text:
            logging.info(f"{tag.text=}")
            qartod += 1

    return qartod


def ioos_core_variables():
    """
    The IOOS Core Variables are presented on
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


def metadata_records():
    """
    These are the number of metadata records currently available through the
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


def ioos():
    """
    This represents the one IOOS Office.
    """
    return 1


def mbon_projects():
    """
    Living marine resources are essential to the health and recreational needs of billions of people,
    yet marine biodiversity and ecosystem processes remain major frontiers in ocean observing.
    IOOS has a critical role in implementing operational,
    sustained programs to observe biology and catalogue biodiversity to ensure these data are available for science,
    management, and the public.
    IOOS is leading development of the Marine Biodiversity Observation Network,
    with core funding from NOAA, NASA and BOEM.
    MBON connects regional networks of scientists, resource managers,
    and users and integrates data from existing long-term programs to understand human- and climate-induced change and its impacts on marine life.
    MBON partners are pioneering application of new remote sensing methods, imaging,
    molecular approaches (eDNA and ‘omics),
    and other technologies and integrating these with traditional research methods and coordinated experiments to understand changing patterns of biodiversity.

    These are the currently funded MBON projects.
    At this time, we are manually checking https://marinebon.org/ and counting the number of U.S. projects.

    We hope to be able to use the resources [here](https://github.com/marinebon/www_marinebon2/tree/master/content/project) to automatically harvest these metrics in the future.

    """

    url = "https://ioos.noaa.gov/project/mbon/"
    html = requests.get(url, headers=_HEADERS).text
    soup = BeautifulSoup(html, "html.parser")

    mbon_projects = 0
    for tag in soup.find_all("h3"):
        if "class" in tag.attrs.keys():
            continue  # we don't need the other headers
        mbon_projects += 1

    return mbon_projects


def hab_pilot_projects():
    """
    These are the National Harmful Algal Bloom Observing Network Pilot Project awards.
    Currently these were calculated from the
    [award announcement pdf](https://cdn.ioos.noaa.gov/media/2021/10/NHABON-Funding-Awards-FY21_v2.pdf)
    which states that there are 9 total.

    Might be able to parse the pdf and calculate this on the fly.

    """
    from pdfminer.high_level import extract_text

    url = "https://cdn.ioos.noaa.gov/media/2022/10/NHABON-Funding-Awards-FY22.pdf"

    data = requests.get(url)

    with io.BytesIO(data.content) as f:
        pdf = extract_text(f)

    content = pdf.split("\n")

    nhabon_projects = sum("Funded amount" in s for s in content)
    nhabon_projects = nhabon_projects + 1  # Gulf of Mexico project
    return nhabon_projects


def update_metrics():
    """
    Load previous metrics and update the spreadsheet.

    """

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
        "IOOS Core Variables": ioos_core_variables,
        "IOOS": ioos,
        "MBON Projects": mbon_projects,
        "Metadata Records": metadata_records,
        "NGDAC Glider Days": ngdac_gliders,
        "OTT Projects": ott_projects,
        "QARTOD Manuals": qartod_manuals,
        "Regional Associations": regional_associations,
        "Regional Platforms": regional_platforms,
    }

    for column, function in functions.items():
        try:
            num = function()
        except Exception as err:
            logging.error(f"{err}")
            num = None
        new_row.update({column: num})
        # Log status.
        message = _compare_metrics(column=column, num=num)
        logging.info(f"{message}")

    new_row = pd.DataFrame.from_dict(data=new_row, orient="index").T

    # only update numbers if it's a new day
    if today not in df["date_UTC"].to_list():
        df = pd.concat(
            [df, new_row],
            ignore_index=True,
            axis=0,
        )

    return df
