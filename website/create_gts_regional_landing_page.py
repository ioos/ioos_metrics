# This script run once creates a catalog landing page based on the *_config.json file
# reference when called. E.g., python create_gts_regional_landing_page.py EcoSys_config.json

import datetime as dt
from fiscalyear import FiscalDate, FiscalQuarter
from erddapy import ERDDAP
from jinja2 import Environment, FileSystemLoader
import json
import os
import pandas as pd
import plotly.express as px
import plotly


def write_html_index(template, configs, org_config):
    root = os.path.dirname(os.path.abspath(__file__))
    # root = path to output directory
    filename = os.path.join(root, "deploy", "gts_regional.html")
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(template.render(org_config=org_config, configs=configs))


def load_template():
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("gts_regional_landing_page.html")
    return template


def write_templates(configs, org_config):
    template = load_template()
    write_html_index(template, configs, org_config)


def timeseries_plot(output):
    output["date"] = pd.to_datetime(output.index.strftime("%Y-%m"))

    fig = px.bar(
        output,
        x="date",
        y=["met", "wave"],
        title="Number of IOOS Regional Observations sent to the GTS via NDBC",
        hover_data=["total"],
    )

    fig.update_xaxes(
        title_text="Date",
        dtick="M3",
        tickformat="%b\n%Y",
        rangeslider_visible=True,
        rangeselector={
            "buttons": [
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=9, label="9m", step="month", stepmode="backward"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all"),
            ]
        },
    )

    fig.update_yaxes(title_text="Messages Delivered to the GTS")

    fig = plotly.io.to_html(fig, full_html=False)

    return fig

def stacked_bar_plot(totals):

    fig1 = px.bar(totals,
                  x=totals.index,
                  y="met",
                  color="source",
                  title="Number of meteorological messages delivered to the GTS via NDBC by source",
                  labels={'met': 'Messages Delivered to the GTS'},
                  )

    fig2 = px.bar(totals,
                  x=totals.index,
                  y="wave",
                  color="source",
                  title="Number of wave messages delivered to the GTS via NDBC by source",
                  labels={'wave': 'Messages Delivered to the GTS'},
                  )

    #fig.update_yaxes(title_text="Messages Delivered to the GTS")

    fig1 = plotly.io.to_html(fig1, full_html=False)
    fig2 = plotly.io.to_html(fig2, full_html=False)

    return fig1, fig2

def get_ioos_regional_stats():

    e = ERDDAP(
        server="https://erddap.ioos.us/erddap",
        protocol="tabledap",
    )

    e.response = "csv"
    e.dataset_id = "gts_regional_statistics"

    df = e.to_pandas(
        index_col="time (UTC)",
        parse_dates=True
    )

    groups = df.groupby(pd.Grouper(
        freq="ME",
    ))

    s = groups[
        ["met", "wave"]
    ].sum()  # reducing the columns so the summary is digestable

    totals = s.assign(total=s["met"] + s["wave"])
    totals.index = totals.index.to_period("M")

    return totals, e

def get_ndbc_full_stats():

    e = ERDDAP(
        server="https://erddap.ioos.us/erddap",
        protocol="tabledap",
    )

    e.response = "csv"

    dsets = {"IOOS": "gts_regional_statistics",
             "NDBC": "gts_ndbc_statistics",
             "non-NDBC": "gts_non_ndbc_statistics"}

    df_out = pd.DataFrame()

    for key, value in dsets.items():
        e.dataset_id = value

        df = e.to_pandas(
            index_col="time (UTC)",
            parse_dates=True
        )
        df["source"] = key

        df_out = pd.concat([df_out,df])

    group = df_out.groupby(by=["source", pd.Grouper(freq="ME")])

    s = group[
            ["met", "wave"]
        ].sum()  # reducing the columns so the summary is digestable

    totals = s.assign(total=s["met"] + s["wave"])

    totals.reset_index(["source"], inplace=True)

    totals.index = totals.index.to_period("M").strftime("%Y-%m")

    return totals

def main(org_config):

    # Go get the data from IOOS ERDDAP
    # compute monthly totals
    # Compute Fiscal Year Quarter totals
    # generate html tables
    # generate html figures
    # write to html page

    totals, e = get_ioos_regional_stats()

    #totals = df_out.loc[df_out['source'] == 'IOOS']

    start_date = dt.datetime(2018, 1, 1)

    configs = dict()

    today = dt.datetime.now()

    for date in pd.date_range(start_date, today, freq="QE"):
        year = int(date.strftime("%Y"))
        month = int(date.strftime("%m"))
        day = int(date.strftime("%d"))

        fd = FiscalDate(year, month, day)

        fq = FiscalQuarter(fd.fiscal_year, fd.fiscal_quarter)

        start_date = fq.start.strftime("%Y-%m-%d")
        end_date = fq.end.strftime("%Y-%m-%d")

        totals_subset = totals[start_date:end_date]

        totals_subset['date'] = totals_subset.index.strftime("%Y-%m")

        table = totals_subset[['date','met','wave','total']].to_html(
            index=False, index_names=False, col_space=70, justify="right", table_id=fq
        )

        table = table.replace("<td>", '<td style="text-align: right;">')

        configs[fq] = {"name": e.dataset_id,
                       "data": '{}&time%3E={}&time%3C={}'.format(e.get_download_url(),start_date,end_date),
                       "table": table}

    fig = timeseries_plot(totals)

    configs["figure"] = fig

    ndbc_totals = get_ndbc_full_stats()

    fig1, fig2 = stacked_bar_plot(ndbc_totals)

    configs["figure1"] = fig1
    configs["figure2"] = fig2
    configs["today"] = today.strftime("%Y-%m-%d")

    write_templates(configs, org_config)


if __name__ == "__main__":
    org_config_file = "gts_regional_config.json"
    with open(org_config_file) as f:
        org_config = json.load(f)
    main(org_config)
