# This script run once creates a catalog landing page based on the *_config.json file
# reference when called. E.g., python create_gts_regional_landing_page.py EcoSys_config.json
from jinja2 import Environment, FileSystemLoader
import json
import os
import pandas as pd
import geopandas
import plotly.express as px
import plotly
import folium


def write_html_index(template, configs, org_config):
    root = os.path.dirname(os.path.abspath(__file__))
    # root = path to output directory
    filename = os.path.join(root, "deploy", "asset_inventory.html")
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(template.render(org_config=org_config, configs=configs))


def load_template():
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("asset_inventory_page.html")
    return template


def write_templates(configs, org_config):
    template = load_template()
    write_html_index(template, configs, org_config)


def map_plot(gdf):

    m = folium.Map(tiles=None,
                   zoom_start=1,
                   )

    # Base Layers
    tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}"
    gh_repo = "https://github.com/ioos/ioos-metrics"
    attr = f"Tiles &copy; Esri &mdash; Sources: GEBCO, NOAA, CHS, OSU, UNH, CSUMB, National Geographic, DeLorme, NAVTEQ, and Esri | <a href=\"{gh_repo}\" target=\"_blank\">{gh_repo}</a>"
    folium.raster_layers.TileLayer(
        name="Ocean",
        tiles=tiles,
        attr=attr,
    ).add_to(m)

    folium.raster_layers.TileLayer(
        'cartodbdark_matter',
        name="CartoDB",
    ).add_to(m)

    folium.raster_layers.TileLayer(
        name="Toner",
        tiles="Stamen Toner",
    ).add_to(m)

    tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}"
    folium.raster_layers.TileLayer(
        tiles=tiles,
        name="OceanRef",
        attr=attr,
        overlay=True,
        control=False,
    ).add_to(m)

    columns = gdf.columns.tolist()
    columns.remove('geometry')
    #print(columns)
    for name, group in gdf.groupby(by='RA'):
        #group["ref"] = [f"<a href=\"{url}\" target=\"_blank\">{url}</a>" for url in group["url"]]

        folium.GeoJson(
            data=group,
            name="{}".format(name),
            marker=folium.CircleMarker(radius=1, color='black'),
            tooltip=folium.features.GeoJsonTooltip(
                fields=["RA","station_long_name"],
#                aliases=["",""],
            ),
            popup=folium.features.GeoJsonPopup(
                fields=columns,
                #aliases=[""],
            ), show=True,
        ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)

    m.fit_bounds(m.get_bounds())
    #m.save("test.html")

    map_out = m._repr_html_()

    return map_out


def main(org_config):
    configs = dict()

    file = org_config["location_of_metrics"]

    gdf = geopandas.read_file(file)

    #print(gdf)

    fig = map_plot(gdf)

    #print(fig)

    configs = {'table': gdf.to_html(), 'figure': fig}

    write_templates(configs, org_config)


if __name__ == "__main__":
    org_config_file = "asset_inventory_config.json"
    with open(org_config_file) as f:
        org_config = json.load(f)
    main(org_config)
