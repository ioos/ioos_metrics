"""
Code extracted from IOOS_BTN.ipynb

"""

import io
import warnings

import pandas as pd
import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
}


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
        warnings.warn(f"The following rows have missing data:\n{rows}")

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
            ra = tag.find("strong").text
            # TODO: change to log
            # print(f"Found RA {ra}")
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
        "https://search.axds.co/v2/search?portalId=99", headers=headers
    )
    json_payload = raw_payload.json()
    for plt in json_payload["types"]:
        if plt["id"] == "platform2":
            print(plt["count"])
            atn = plt["count"]
            break
    return atn


def update_metrics():
    """
    Load previous metrics and update the spreadsheet.

    """
    df = previous_metrics()

    federal_partners_number = federal_partners()
    glider_days = ngdac_gliders()
    comt_number = comt()
    ras = regional_associations()
    rps = regional_platforms()
    atn = atn_deployments()

    today = pd.Timestamp.strftime(pd.Timestamp.today(tz="UTC"), "%Y-%m-%d")
    new_row = {
        "date_UTC": today,
        "Federal Partners": federal_partners_number,
        "NGDAC Glider Days": glider_days,
        "COMT Projects": comt_number,
        "Regional Associations": ras,
        "Regional Platforms": rps,
        "ATN Deployments": atn,
    }
    new_row = pd.DataFrame.from_dict(data=new_row, orient="index").T

    # only update numbers if it's a new day
    if today not in df["date_UTC"].to_list():
        df = pd.concat(
            [df, new_row],
            ignore_index=True,
            axis=0,
        )

    return df
