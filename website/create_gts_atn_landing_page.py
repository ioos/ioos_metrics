# This script run once creates a catalog landing page based on the *_config.json file
# reference when called. E.g., python create_gts_regional_landing_page.py EcoSys_config.json
import base64
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
import json
import os
import pandas as pd
import plotly.express as px
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
    output["date"] = pd.to_datetime(output["date"])

    fig = px.bar(output, x="date", y="total")
    fig = plotly.io.to_html(fig, full_html=False)

    return fig


def main(org_config):
    configs = dict()

    files = ["GTS_ATN_monthly_totals.csv"]

    for f in files:
        filename = os.path.join(org_config["location_of_metrics"], f)
        output = pd.read_csv(filename)
        f_out = filename.replace(".csv", ".html").replace(
            org_config["location_of_metrics"], "deploy"
        )

        print(f_out)
        key = "{} {}".format(f_out.split("\\")[-1].split("_")[0], f_out.split("_")[1])

        table = output.to_html(
            index=False, index_names=False, col_space=70, justify="right", table_id=key
        )

        table = table.replace("<td>", '<td style="text-align: right;">')

        fig = timeseries_plot(output)

        configs[key] = {
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
