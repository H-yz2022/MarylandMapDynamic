# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 01:03:27 2025

@author: huang
"""

from flask import Flask, render_template_string, send_from_directory
import geopandas as gpd
import folium
from branca import colormap
from folium.plugins import GroupedLayerControl
import os

app = Flask(__name__)

# Make a folder to store exported GeoJSON
os.makedirs("static/geojson", exist_ok=True)

@app.route('/')
def index():
    # Load shapefiles
    taz = gpd.read_file("TPBTAZ3722_TPBMod.shp").to_crs(epsg=4326)
    centroid = gpd.read_file("Zonehwy_Line_Centroid_Connectors.shp").to_crs(epsg=4326)
    highway_update = gpd.read_file("I4_Assign_OutputwAWDT.shp").to_crs(epsg=4326)

    # ---- FILTERS ----
    filter1 = highway_update[(highway_update["AWDT_2023"] > 0) & (highway_update["CNT2LOADDIF"] < -20)]
    filter2 = highway_update[highway_update["CNT2LOADPCT"] > 20]
    filter3 = highway_update[(highway_update["AWDT_2023"] > 0) & (highway_update["CNT2LOADDIF"] > 20)]
    filter4 = highway_update[highway_update["ABSPCTDIFF"] > 1]

    # ---- Export each dataset as GeoJSON ----
    taz.to_file("static/geojson/taz.geojson", driver="GeoJSON")
    centroid.to_file("static/geojson/centroid.geojson", driver="GeoJSON")
    filter1.to_file("static/geojson/filter1.geojson", driver="GeoJSON")
    filter2.to_file("static/geojson/filter2.geojson", driver="GeoJSON")
    filter3.to_file("static/geojson/filter3.geojson", driver="GeoJSON")
    filter4.to_file("static/geojson/filter4.geojson", driver="GeoJSON")

    # ---- Colormap ----
    colormapper = colormap.linear.YlGn_09.scale(
        taz['TAZ_Area'].min(),
        taz['TAZ_Area'].max()
    )
    colormapper.caption = "TAZ Area"

    # ---- Base map ----
    m = folium.Map(location=[39.23, -76.68], zoom_start=11, tiles='CartoDB positron')

    # Instead of embedding data directly, load via folium.GeoJson("URL")
    taz_layer = folium.FeatureGroup(name="TAZ Area")
    folium.GeoJson(
        "static/geojson/taz.geojson",
        style_function=lambda feature: {
            'fillColor': "#faded1" if feature['properties']['TAZ_Area'] == 0 else colormapper(feature['properties']['TAZ_Area']),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.4,
        },
        tooltip=folium.GeoJsonTooltip(fields=['TAZ', 'NAME', 'Community', 'TAZ_Area'])
    ).add_to(taz_layer)
    taz_layer.add_to(m)

    centroid_layer = folium.FeatureGroup(name="Centroid Connectors")
    folium.GeoJson(
        "static/geojson/centroid.geojson",
        style_function=lambda feature: {
            'fillColor': 'yellow',
            'color': 'yellow',
            'weight': 0.7,
            'fillOpacity': 0.5,
        },
        tooltip=folium.GeoJsonTooltip(fields=['TAZ', 'ATYPE', 'MDLANE', 'MDLIMIT', 'TIMEPEN'])
    ).add_to(centroid_layer)
    centroid_layer.add_to(m)
    
    filter_layers = []  # keep track of layers

    # Add each filter layer dynamically
    filters = [
        ("Filter1: AWDT>0 & CNT2LOADDIF<-20", "filter1.geojson", 'red', ['AWDT_2023', 'CNT2LOADDIF']),
        ("Filter2: CNT2LOADPCT>20", "filter2.geojson", 'blue', ['CNT2LOADPCT']),
        ("Filter3: AWDT>0 & CNT2LOADDIF>20", "filter3.geojson", 'green', ['AWDT_2023', 'CNT2LOADDIF']),
        ("Filter4: ABSPCTDIFF>1", "filter4.geojson", 'orange', ['ABSPCTDIFF'])
    ]

    for name, file, color, fields in filters:
        layer = folium.FeatureGroup(name=name)
        folium.GeoJson(
            f"static/geojson/{file}",
            style_function=lambda f, c=color: {'color': c, 'weight': 2},
            tooltip=folium.GeoJsonTooltip(fields=fields)
        ).add_to(layer)
        layer.add_to(m)
        filter_layers.append(layer)

    # ---- Layer Control ----
    GroupedLayerControl(
        groups={
            "Zones": [taz_layer, centroid_layer],
            "Filtered Highways": filter_layers   # ✅ use saved list
        },
        exclusive_groups=False,
        collapsed=False
    ).add_to(m)

    # ---- Legend ----
    colormapper.add_to(m)

    # Save small HTML
    m.save("templates/map.html")

    # Return template
    return render_template_string(open("templates/map.html").read())

if __name__ == '__main__':
    app.run(port=8006, debug=True, use_reloader=False)

