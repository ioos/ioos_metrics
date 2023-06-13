# This script run once creates a catalog landing page based on the *_config.json file
# reference when called. E.g., python create_gts_regional_landing_page.py EcoSys_config.json
import base64
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly


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
    table = output.copy()

    output["date"] = pd.to_datetime(output["date"])

    figure = go.Figure(
        # data=[go.Bar(x=[1, 2, 3], y=[1, 3, 2])],
        layout=go.Layout(height=600, width=1500)
    )

    fig = make_subplots(
        rows=1,
        cols=3,
        #        vertical_spacing=0.03,
        specs=[
            [{"type": "table"}, {"colspan": 2, "type": "bar"}, None]
        ],  # {"type": "bar"},{'colspan': 1}]],
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
    #     title="ATN Messages sent to the GTS via NDBC",
    #     width=800,
    #     height=600,
    #     )
    # )
    #
    # fig.update_xaxes(
    #     title_text="Date",
    #     dtick="M3",
    #     tickformat="%b\n%Y",
    #     rangeslider_visible=True,
    #     rangeselector={
    #         "buttons": [
    #             dict(count=3, label="3m", step="month", stepmode="backward"),
    #             dict(count=6, label="6m", step="month", stepmode="backward"),
    #             dict(count=9, label="9m", step="month", stepmode="backward"),
    #             dict(count=1, label="1y", step="year", stepmode="backward"),
    #             dict(step="all"),
    #         ]
    #     },
    # )
    #
    # fig.update_yaxes(title_text="Messages Delivered to the GTS")

    fig = plotly.io.to_html(fig, full_html=False)

    return fig


def main(org_config):
    configs = dict()

    file = "GTS_ATN_monthly_totals.csv"

    filename = os.path.join(org_config["location_of_metrics"], file)
    output = pd.read_csv(filename)
    f_out = filename.replace(".csv", ".html").replace(
        org_config["location_of_metrics"], "deploy"
    )

    print(f_out)
    # key = "{} {}".format(f_out.split("\\")[-1].split("_")[0], f_out.split("_")[1])

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
        "name": f_out,
        "data": f,
        "table": table,
        "figure": fig,
    }

    write_templates(configs, org_config)


if __name__ == "__main__":
    org_config_file = "gts_atn_config.json"
    with open(org_config_file) as f:
        org_config = json.load(f)
    main(org_config)
