"""National Platforms.

The National backbone of IOOS includes buoys,
water level gauges,
as well as coastal and estuary stations run by our federal partners.
Platforms calculated within this total are assets within the EEZ.
For buoys this includes platforms managed by NOAA's National Data Buoy Center,
the NOAA NMFS Chesapeake Bay Interpretive Buoy System (CBIBS),
and the U.S. Army Corps of Engineers' Coastal Data Information Program (CDIP),
Ocean Acidification Program,
Ecosystems and Fishery Oceanography Coordinated Investigations (EcoFOCI).
For gauges, this includes National Water Level Observation Network gauges
operated by the Center for Operational Oceanographic Products and Services (CO-OPS).
The coastal and estuary stations are maintained through NOAA's National Estuarine Research Reserves (NERR)
System-Wide Management Program (SWMP).

"""

import functools
import io
import json
import logging
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

ua = UserAgent()
_HEADERS = {
    "User-Agent": ua.random,
}


@functools.lru_cache(maxsize=128)
def get_coops():
    """Fetches CO-OPS stations.

    * https://opendap.co-ops.nos.noaa.gov/stations/index.jsp
    * as xml: https://opendap.co-ops.nos.noaa.gov/stations/stationsXML.jsp
    * https://tidesandcurrents.noaa.gov/cdata/StationList?type=Current+Data&filter=active

    """
    xml = requests.get(
        "https://opendap.co-ops.nos.noaa.gov/stations/stationsXML.jsp",
        timeout=10,
    ).text

    station_name = re.escape("station name")
    return sum(1 for _ in re.finditer(rf"\b{station_name}\b", xml))


@functools.lru_cache(maxsize=128)
def get_ndbc():
    """Fetches NDBC buoys.

    * Buoys: 106 (103 base-funded)
    * CMAN: 45

    """
    url = "https://www.ndbc.noaa.gov/wstat.shtml"
    html = requests.get(url, headers=_HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    strings_to_find = [
        "Total Base Funded Buoys:",
        "Total Other Buoys:",
        "Total Moored Buoys:",
        "Total Base Funded Stations:",
        "Total Stations:",
    ]

    ndbc_buoys = {}
    for string in strings_to_find:
        for tag in soup.find_all("td", string=string):
            ndbc_buoys[string] = int(tag.next_sibling.string)

    return ndbc_buoys["Total Moored Buoys:"] + ndbc_buoys["Total Base Funded Stations:"]


@functools.lru_cache(maxsize=128)
def get_nerrs():
    """Fetches NERRS stations.

    * https://nosc.noaa.gov/OSC/OSN/index.php
      NERRS SWMP;
      Across 29 NERRS;
      Source = internal access only - NOAA Observing System Council.
    * http://cdmo.baruch.sc.edu/webservices.cfm <- need IP address approval

    """
    url = "https://cdmo.baruch.sc.edu//webservices/station_timing.cfm"
    html = requests.get(url, headers=_HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    df = pd.read_html(
        io.StringIO(str(soup.find(attrs={"class": "row text-center"}))),
        header=0,
        attrs={"class": "table"},
        flavor="bs4",
    )

    df_final = pd.concat([df[0], df[1]])

    return df_final.shape[0]


@functools.lru_cache(maxsize=128)
def get_cbibs():
    """Fetches CBIBS buoys.

    https://buoybay.noaa.gov/locations

    [API docs](https://buoybay.noaa.gov/node/174)

    Base URL: https://mw.buoybay.noaa.gov/api/v1

    """
    apikey = "f159959c117f473477edbdf3245cc2a4831ac61f"

    base_url = "https://mw.buoybay.noaa.gov/api/v1"
    start = "2021-12-08T01:00:00z"
    end = "2021-12-09T23:59:59z"
    var = "Position"

    query_url = f"{base_url}/json/query?key={apikey}&sd={start}&ed={end}&var={var}"
    payload = json.loads(requests.get(query_url, timeout=10).text)
    return len(payload["stations"])


@functools.lru_cache(maxsize=128)
def get_oap():
    """Fetches OAP stations.

    * https://cdip.ucsd.edu/m/stn_table
      Includes overlap with the RAs and other programs

    See buoys and moorings at https://oceanacidification.noaa.gov/WhatWeDo/Data.aspx

    """
    url = "https://oceanacidification.noaa.gov/WhatWeDo/Data.aspx"
    html = requests.get(url, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.find_all(attrs={"data-id": "4fa1cacd"})[0].find_all("h6")[0].text

    res = [int(i) for i in text.split() if i.isdigit()]
    return int(res[0])


@functools.lru_cache(maxsize=128)
def get_cdip():
    """Fetches CDIP stations.

    * https://cdip.ucsd.edu/m/stn_table
      Includes overlap with the RAs

    """
    url = "https://cdip.ucsd.edu/themes/?d2=p1:m:mobile&regions=all&units=standard&zoom=auto&pub_set=public&tz=UTC&ll_fmt=dm&numcolorbands=10&palette=cdip_classic&high=6.096"
    table_list = pd.read_html(url, match="Stn")

    df = table_list[0]

    return df["Stn"].unique().size


def national_platforms() -> int:
    """Adds all the national platforms metrics."""
    return get_cbibs() + get_cdip() + get_coops() + get_ndbc() + get_nerrs() + get_oap()
