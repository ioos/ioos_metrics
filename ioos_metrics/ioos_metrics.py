"""
Code extracted from IOOS_BTN.ipynb

"""

import io

import pandas as pd
import requests


def previous_metrics():
    ioos_btn_df = pd.read_csv(
        "https://github.com/ioos/ioos_metrics/raw/main/ioos_btn_metrics.csv"
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
