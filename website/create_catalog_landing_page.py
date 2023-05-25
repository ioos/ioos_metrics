# This script run once creates a catalog landing page based on the *_config.json file
# reference when called. E.g., python create_catalog_landing_page.py EcoSys_config.json
from jinja2 import Environment, FileSystemLoader
import json
import os
import pandas as pd


def write_html_index(template, configs, org_config):
    root = os.path.dirname(os.path.abspath(__file__))
    # root = path to output directory
    filename = os.path.join(root, "deploy", "browse.html")
    with open(filename, "w") as fh:
        fh.write(template.render(configs=configs, org_config=org_config))


def load_template():
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("catalog_landing_page.html")
    return template


def write_templates(configs, org_config):
    template = load_template()
    write_html_index(template, configs, org_config)


def main(org_config):
    for f in os.listdir(org_config["location_of_metrics"]):
        filename = os.path.join(org_config["location_of_metrics"], f)
        output = pd.read_csv(filename)
        f_out = filename.replace(".csv", ".html").replace(
                org_config["location_of_metrics"], "deploy"
            )

        s = output.style.set_properties(**{'text-align': 'right'})
        s.to_html(f_out)
        # output.to_html(
        #     f_out,
        #     col_space=100,
        #     justify='right',
        #     index=False,
        # )


#    write_templates(allthemodels, org_config)

if __name__ == "__main__":
    org_config_file = "Browse_config.json"
    with open(org_config_file) as f:
        org_config = json.load(f)
    main(org_config)
