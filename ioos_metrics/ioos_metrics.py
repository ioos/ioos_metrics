"""
Code extracted from IOOS_BTN.ipynb

"""

import io

import pandas as pd
import requests


def previous_metrics():
    """
    Loads the previous metrics as a DataFrame for updating.

    """
    ioos_btn_df = pd.read_csv(
        "https://github.com/ioos/ioos_metrics/raw/main/ioos_btn_metrics.csv",
    )

    today = pd.Timestamp.strftime(pd.Timestamp.today(tz="UTC"), "%Y-%m-%d")

    # only update numbers if it's a new day
    if today not in ioos_btn_df["date_UTC"].to_list():
        ioos_btn_df = pd.concat(
            [ioos_btn_df, pd.DataFrame([today], columns=["date_UTC"])],
            ignore_index=True,
            axis=0,
        )
    return ioos_btn_df


def federal_partners():
    """
    ICOOS Act/COORA

    Typically 17, from https://ioos.noaa.gov/community/national#federal.

    """

    url = "https://ioos.noaa.gov/community/national#federal"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
    }

    html = requests.get(url, headers=headers).text

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
