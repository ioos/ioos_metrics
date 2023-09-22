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
from folium.plugins import Search, Fullscreen


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
    m = folium.Map(
        tiles=None,
        zoom_start=1,
    )

    # Base Layers
    tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}"
    gh_repo = "https://github.com/ioos/ioos_metrics"
    attr = f'Tiles &copy; Esri &mdash; Sources: GEBCO, NOAA, CHS, OSU, UNH, CSUMB, National Geographic, DeLorme, NAVTEQ, and Esri | <a href="{gh_repo}" target="_blank">{gh_repo}</a>'
    folium.raster_layers.TileLayer(
        name="Ocean",
        tiles=tiles,
        attr=attr,
    ).add_to(m)

    folium.raster_layers.TileLayer(
        "cartodbdark_matter",
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
    columns.remove("geometry")

    colormap = pd.DataFrame(
        {
            "RA": [
                "AOOS",
                "PACIOOS",
                "NANOOS",
                "CENCOOS",
                "SCCOOS",
                "GLOS",
                "NERACOOS",
                "MARACOOS",
                "SECOORA",
                "GCOOS",
                "CARICOOS",
            ],
            "color": [
                "red",
                "blue",
                "orange",
                "black",
                "SlateBlue",
                "magenta",
                "brown",
                "purple",
                "DarkSlateGrey",
                "grey",
                "green",
            ],
        }
    )
    gdf = gdf.merge(colormap, how="left", on="RA")

    search_group = folium.FeatureGroup(control=False, show=False)
    search_group.add_to(m)

    for name, group in gdf.groupby(by="RA"):
        color = group["color"].unique()[0]

        folium.GeoJson(
            data=group,
            name='<span style="color: {};"><b>{}</b></span>'.format(color, name),
            marker=folium.CircleMarker(
                radius=3, fillColor=color, color=color, fillOpacity=1
            ),
            tooltip=folium.features.GeoJsonTooltip(
                fields=["RA", "station_long_name"],
            ),
            popup=folium.features.GeoJsonPopup(
                fields=[
                    "RA",
                    "latitude",
                    "longitude",
                    "station_long_name",
                    "Platform",
                    "Operational",
                    "station_deployment",
                    "RA_Funded",
                    "Raw_Vars",
                ]
            ),
            show=True,
        ).add_to(m).add_to(search_group)

    Search(
        layer=search_group,
        geom_type="Point",
        placeholder="Search for an station",
        collapsed=False,
        search_label="station_long_name",
        weight=3,
    ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)

    Fullscreen().add_to(m)

    m.fit_bounds(m.get_bounds())
    #m.save("test.html")

    map_out = m._repr_html_()

    return map_out


def main(org_config):

    file = org_config["location_of_metrics"]

    file = file + "?&Year=max(Year)"  # only grab most recent year

    gdf = geopandas.read_file(file)

    gdf["longitude"] = gdf.get_coordinates()["x"]
    gdf["latitude"] = gdf.get_coordinates()["y"]

    # to make a pretty map we need to translate longitudes that are between 130 and 180 to <-180 longitudes
    # but, we still want to show the source longitude on the map so we keep those.
    gdf["longitude2"] = gdf["longitude"]
    gdf.loc[gdf["longitude2"] > 0, "longitude2"] = gdf.loc[gdf["longitude2"] > 0, "longitude2"] - 360

    # recompute the geometry column based on the new longitudes so the map is prettier.
    gdf = geopandas.GeoDataFrame(
        gdf, geometry=geopandas.points_from_xy(gdf['longitude2'], gdf['latitude'], crs=gdf.crs))

    fig = map_plot(gdf)

    columns = [
        "Year",
        "RA",
        "station_long_name",
        "latitude",
        "longitude",
        "Platform",
        "Operational",
        "station_deployment",
        "RA_Funded",
        "Raw_Vars",
    ]

    configs = {
        "table": gdf.to_html(table_id="table", index=False, columns=columns),
        "figure": fig,
    }

    write_templates(configs, org_config)


if __name__ == "__main__":
    org_config_file = "asset_inventory_config.json"
    with open(org_config_file) as f:
        org_config = json.load(f)
    main(org_config)
