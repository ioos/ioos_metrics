import datetime as dt
import pandas as pd
from fiscalyear import *

start_date = dt.datetime(2018, 1, 1)

for date in pd.date_range(start_date, dt.datetime.now(), freq="Q"):
    year = int(date.strftime("%Y"))
    month = int(date.strftime("%m"))
    day = int(date.strftime("%d"))

    fd = FiscalDate(year, month, day)

    fq = FiscalQuarter(fd.fiscal_year, fd.fiscal_quarter)

    # gather FY start/end dates for previous quarter
    # fq = FiscalQuarter.current().prev_fiscal_quarter

    start_date = fq.start.strftime("%Y-%m-%d")
    end_date = fq.end.strftime("%Y-%m-%d")

    start = dt.datetime.strptime(start_date, "%Y-%m-%d")
    end = dt.datetime.strptime(end_date, "%Y-%m-%d")

    # build an array for days between dates
    date_array = (start + dt.timedelta(days=x) for x in range(0, (end - start).days))

    # get a unique list of year-months for url build
    months = []
    for date_object in date_array:
        months.append(date_object.strftime("%Y-%m"))
    months = sorted(set(months))

    df = pd.DataFrame(columns=["locationID", "region", "sponsor", "met", "wave"])
    for month in months:
        url = (
            "https://www.ndbc.noaa.gov/ioosstats/rpts/%s_ioos_regional.csv"
            % month.replace("-", "_")
        )
        print("Loading %s" % url)
        df1 = pd.read_csv(url, dtype={"met": int, "wave": int})
        df1["date"] = pd.to_datetime(month)
        df = pd.concat([df, df1])

    df["date"] = pd.to_datetime(df["date"])
    # Remove time-zone info for easier plotting, it is all UTC.
    df["date"] = df["date"].dt.tz_localize(None)

    groups = df.groupby(pd.Grouper(key="date", freq="M"))

    s = groups[
        ["met", "wave"]
    ].sum()  # reducing the columns so the summary is digestable

    totals = s.assign(total=s["met"] + s["wave"])
    totals.index = totals.index.to_period("M")

    fname = "gts/GTS_regional_totals_FY%s_Q%s.csv" % (fq.fiscal_year, fq.fiscal_quarter)

    totals.to_csv(fname)
