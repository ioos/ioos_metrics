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

import io
import logging
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logging.basicConfig(
    filename="national_platforms.log",
    encoding="utf-8",
    level=logging.DEBUG,
)

ua = UserAgent()
_HEADERS = {
    "User-Agent": ua.random,
}


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

    return sum(1 for _ in re.finditer(r"\b%s\b" % re.escape("station name"), xml))


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
    )

    df_final = pd.concat([df[0], df[1]])

    return df_final.shape[0]
