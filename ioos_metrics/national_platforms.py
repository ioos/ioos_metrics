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

import re

import requests


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
