# This script run once creates a catalog landing page based on the *_config.json file
# reference when called. E.g., python create_gts_regional_landing_page.py EcoSys_config.json
from jinja2 import Environment, FileSystemLoader
import json
import os
import pandas as pd


def write_html_index(template, configs, org_config):
    root = os.path.dirname(os.path.abspath(__file__))
    # root = path to output directory
    filename = os.path.join(root, "deploy", "gts_atn.html")
    with open(filename, "w") as fh:
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


def main(org_config):
    configs = dict()

    #files = os.listdir(org_config["location_of_metrics"])

    files = ['GTS_ATN_monthly_totals.csv']
    #files = sorted(files)

    for f in files:
        filename = os.path.join(org_config["location_of_metrics"], f)
        output = pd.read_csv(filename)
        f_out = filename.replace(".csv", ".html").replace(
            org_config["location_of_metrics"], "deploy"
        )

        #output = output.style.set_table_styles([{'selector': 'td', 'props': 'text-align: right; font-weight: bold;'}])#properties(**{'text-align': 'right'})

        print(f_out)
        key = '{} {}'.format(f_out.split("\\")[-1].split('_')[0], f_out.split('_')[1])

        table = output.to_html(
            index=False,
            index_names=False,
            col_space=70,
            justify='right',
            table_id=key)

        table = table.replace("<td>","<td style=\"text-align: right;\">")

        configs[key] = {'name': f_out,
                        'data': f,
                        'table': table}

    # myKeys = list(configs.keys())
    # myKeys.sort()
    # configs_sorted = {i: configs[i] for i in myKeys}

#        configs = {'fname': f_out}
        # output.to_html(
        #     f_out,
        #     col_space=100,
        #     justify='right',
        #     index=False,
        # )


    write_templates(configs, org_config)

if __name__ == "__main__":
    org_config_file = "gts_atn_config.json"
    with open(org_config_file) as f:
        org_config = json.load(f)
    main(org_config)
