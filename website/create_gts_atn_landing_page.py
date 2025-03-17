# This script run once creates a catalog landing page based on the *_config.json file
# reference when called. E.g., python create_gts_regional_landing_page.py EcoSys_config.json

from bs4 import BeautifulSoup
import datetime as dt
from jinja2 import Environment, FileSystemLoader
import json
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly
import requests

def write_html_index(template, configs, org_config):
    root = os.path.dirname(os.path.abspath(__file__))
    # root = path to output directory
    filename = os.path.join(root, "deploy", "gts_atn.html")
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(template.render(org_config=org_config, configs=configs))


def load_template():
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("gts_atn_landing_page.html")
    return template


def write_templates(configs, org_config):
    template = load_template()
    write_html_index(template, configs, org_config)


def timeseries_plot(output):

    output["date"] = pd.to_datetime(output.index.strftime("%Y-%m"))

    table = output[["date","total"]].copy()
    table["date"] = table.index.strftime("%Y-%m")

    figure = go.Figure(
        layout=go.Layout(height=600, width=1500)
    )

    fig = make_subplots(
        rows=1,
        cols=3,
        specs=[
            [{"type": "table"}, {"colspan": 2, "type": "bar"}, None]
            ],
        figure=figure,
    )

    fig.add_trace(
        go.Table(
            header=dict(
                values=table.keys().tolist(), font=dict(size=10), align="right"
            ),
            cells=dict(values=[table[k].tolist() for k in table], align="right"),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=output["date"],
            y=output["total"],
        ),
        row=1,
        col=2,
    )

    fig = plotly.io.to_html(fig, full_html=False)

    return fig


def get_atn_gts_metrics():

    # recursively search the https index for bufr messages
    url = "https://stage-ndbc-bufr.srv.axds.co/platforms/atn/smru/profiles/"

    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    df_out = pd.DataFrame()

    for deployment in soup.find_all("a"):
        depl_url = url + deployment.text
        depl_html = requests.get(depl_url).text

        depl_soup = BeautifulSoup(depl_html, "html.parser")

        # some content is not in an html node, so we have to parse line by line
        files = depl_soup.get_text().split("\r\n")[1:-1]

        for file in files:
            content = file.split()

            if ".bufr" in content[0]:
                # save the index file information to DF.
                fname = deployment.text + content[0]
                df_file = pd.DataFrame(
                    {
                        "fname": [fname],
                        "date": pd.to_datetime([content[1] + "T" + content[2]]),
                        "size": [content[3]],
                    }
                )

                df_out = pd.concat([df_out, df_file])

    # mask for FY Quarter
    df_out = df_out.set_index("date").sort_index()

    # groupby month and save data
    group = df_out.groupby(pd.Grouper(freq="ME"))

    s = group["fname"].count()

    s.index = s.index.to_period("M")

    s = s.rename("total")

    return pd.DataFrame(s)


def main(org_config):

    output = get_atn_gts_metrics()

    table = output.to_html(
        index=False,
        index_names=False,
        col_space=70,
        justify="right",
        table_id="GTS ATN",
    )

    table = table.replace("<td>", '<td style="text-align: right;">')

    fig = timeseries_plot(output)

    configs = {
        "data": f,
        "table": table,
        "figure": fig,
    }
    
    configs['today'] = dt.datetime.now().strftime("%Y-%m-%d")

    write_templates(configs, org_config)


if __name__ == "__main__":
    org_config_file = "gts_atn_config.json"
    with open(org_config_file) as f:
        org_config = json.load(f)
    main(org_config)
