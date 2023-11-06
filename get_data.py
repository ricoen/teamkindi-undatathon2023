import ee
import geemap as geemap
import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime as dt, date
from geemap import geojson_to_ee, ee_to_geojson
from ipyleaflet import GeoJSON


m = geemap.Map()

# Get geojson
def get_geojson():
    file_path = os.path.abspath('data/kota_malang/malang.geojson')

    with open(file_path) as f:
        malang_json = json.load(f)

    return malang_json

def esa_land_cover():
    esa_cover = ee.ImageCollection('ESA/WorldCover/v200').first()
    esa_cover_vis = {'bands': ['Map'],}

    return (esa_cover, esa_cover_vis)

# Clip raster
def clip_raster():
    malang_json = get_geojson()
    esa_cover, _ = esa_land_cover()
    
    features = malang_json['features']
    fc = ee.FeatureCollection(features)
    esa_cover_clip = esa_cover.clipToCollection(fc)

    return (fc, esa_cover_clip)

def export_image():
    fc, esa_cover_clip = clip_raster()
    
    parent_dir = os.path.join('images')
    file_name = os.path.join(parent_dir, 'land_cover.tif')

    image = esa_cover_clip.unmask()
    geemap.ee_export_image(
    image, filename=file_name, scale=90, 
    region=fc.geometry(), 
    file_per_band=False)

def calculate_land_cover():
    fc, esa_cover_clip = clip_raster()

    parent_dir = os.path.join('data')
    land_cover_stats = os.path.join(parent_dir, 'land_cover.csv')

    geemap.zonal_statistics_by_group(
        esa_cover_clip,
        fc,
        land_cover_stats,
        statistics_type='PERCENTAGE',
        denominator=1000000,
        decimal_places=2,
    )

aoi = geojson_to_ee(get_geojson())
nrti_prod = 'COPERNICUS/S5P/NRTI/L3_O3'
O3_concentration = 'O3_column_number_density'
NO2_concentration = 'NO2_column_number_density'
file_name = 'nrti_O3.csv'

def get_chem_raster():
    start_date = '2023-01-01'
    latest_date = date.today().strftime('%Y-%m-%d')
    nrti_chem = ee.ImageCollection(nrti_prod)\
        .select(concentration)\
            .filterDate(start_date, latest_date)

    return nrti_chem

def reduce_region(image):
    dict = image.reduceRegion(ee.Reducer.mean(), geometry=aoi)
    
    return image.set(dict)

def filter_nrti_chem():
    nrti_chem = get_chem_raster()
    
    nrti_chem_fc = ee.FeatureCollection(nrti_chem.map(reduce_region))
    nrti_chem_filtered = nrti_chem_fc.filter(ee.Filter.notNull(nrti_chem.first().bandNames()))

    return nrti_chem_filtered

def fc_to_dict(fc):
    prop_names = fc.first().propertyNames()
    prop_lists = fc.reduceColumns(
        reducer=ee.Reducer.toList().repeat(prop_names.size()),
        selectors=prop_names).get('list')

    return ee.Dictionary.fromLists(prop_names, prop_lists)

def dict_to_df():
    nrti_chem_filtered = filter_nrti_chem()
    
    nrti_chem_dict = fc_to_dict(nrti_chem_filtered).getInfo()
    nrti_chem_df = pd.DataFrame(nrti_chem_dict)

    return nrti_chem_df

# Get time
def get_time():
    nrti_chem_df = dict_to_df()
    
    time = nrti_chem_df["system:time_start"]
    # Convert from miliseconds to true time (local time with 24-H format)
    date = [x // 1000 for x in time]
    captured = [dt.utcfromtimestamp(i).strftime("%c GMT") for i in date]
    captured = pd.Series(captured)
    converted_date = pd.to_datetime(captured).dt.tz_localize("Asia/Jakarta").dt.tz_convert("UTC")

    return converted_date

def get_chem_value():
    nrti_chem_df = dict_to_df()
    
    chem_density = nrti_chem_df[concentration]
    chem_density = chem_density.round(decimals=6)
    
    return chem_density

def time_series_data(concentration):
    converted_date = get_time()
    chem_density = get_chem_value()
    
    df = pd.concat([converted_date, chem_density], axis=1)
    df.columns = ["date", concentration]

    print('Please wait ...')

    return df

def df_to_csv(df, file_name):
    out_dir = os.path.join('data')
    nrti_chem_data = os.path.join(out_dir, file_name)

    df.to_csv(nrti_chem_data, index=False)

def plot_chem_data(df, concentration, plot_title, yaxis_title):
    # df = pd.read_csv('data/nrti_O3.csv')

    #Define x and y values
    fig = px.line(
        df, x='date', y=concentration, 
        title=plot_title, markers=True
    )
    fig.update_layout(
        xaxis_title="Date", 
        yaxis_title=yaxis_title,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    #Show the figure
    return fig

# def create_map():
#     start_date = '2023-09-01'
#     latest_date = date.today().strftime('%Y-%m-%d')
#     fc, esa_cover_clip =  clip_raster()
#     _, esa_cover_vis = esa_land_cover()

#     collection = ee.ImageCollection(
#         'COPERNICUS/S5P/OFFL/L3_NO2').select(
#             'tropospheric_NO2_column_number_density').filterDate(
#                 start_date, latest_date)

#     band_viz = {
#         'min': 0,
#         'max': 0.0002,
#         'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red'],
#         'opacity': 0.5,
#     }

#     m.setCenter(lat=-7.983, lon=112.621, zoom=8)

#     m.add_layer(fc, {}, 'Malang City')
#     m.add_layer(
#         esa_cover_clip, 
#         esa_cover_vis, 
#         'Land Cover'
#     )
#     m.add_layer(
#         collection.mean(),
#         band_viz,
#         'NRTI NO2'
#     )

#     m.add_legend(builtin_legend='ESA_WorldCover')

#     map_file = os.path.join('assets', 'map.html')
#     m.save(map_file)

#     return m

def plot_cover_data():
    df = pd.read_csv('data/land_cover.csv')

    colors = ['#fa0000', '#f096ff', '#ffff4c', '#006400']
    
    hist_data = ['Class_50', 'Class_40', 
    'Class_30', 'Class_10']
    data = df[hist_data].values.flatten().round(decimals=3)*100
    group_labels = ['Built-up', 'Cropland', 
    'Grassland', 'Tree cover']
    
    #Define x and y values
    fig = go.Figure(
        data=[go.Bar(
            x=group_labels, y=data, 
            marker_color=colors
            )
        ]
    )

    fig.update_layout(
        title='Land Cover Prone to Emission',
        xaxis_title="Land Cover", 
        yaxis_title="Percentage (%)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    #Show the figure
    return fig


def main():
    export_image()
    calculate_land_cover()
    df = time_series_data(O3_concentration)
    print('Done')
    df_to_csv(df, file_name)
    # plot_chem_data()
    # create_map()
    # plot_cover_data()

if __name__=="__main__":
    main()