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


def update_metrics():
    """
    Load previous metrics and update the spreadsheet.

    """
    df = previous_metrics()

    federal_partners_number = federal_partners()
    glider_days = ngdac_gliders()
    comt_number = comt()
    ras = regional_associations()

    _TODO = [
        # "NGDAC Glider Days", (TODO: change to data days)
        "HF Radar Stations",  # It is a hardcoded number at the moment
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
    ]

    today = pd.Timestamp.strftime(pd.Timestamp.today(tz="UTC"), "%Y-%m-%d")
    new_metric_row = pd.DataFrame(
        [today, federal_partners_number, glider_days, comt_number, ras],
        index=[
            "date_UTC",
            "Federal Partners",
            "NGDAC Glider Days",
            "COMT Projects",
            "Regional Associations",
        ],
    ).T
    # only update numbers if it's a new day
    if today not in df["date_UTC"].to_list():
        df = pd.concat(
            [df, new_metric_row],
            ignore_index=True,
            axis=0,
        )

    return df
