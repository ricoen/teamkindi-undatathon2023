import get_data as get
from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd
import dash_leaflet as dl


app = Dash(__name__)

O3_df = pd.read_csv('data/nrti_O3.csv')
NO2_df = pd.read_csv('data/nrti_NO2.csv')

O3_plot = get.plot_chem_data(
    O3_df, get.O3_concentration, 
    'Mean NRTI O3 in Malang City',
    'Tropospheric Column of O3 (mol/m^2)')
NO2_plot = get.plot_chem_data(
    NO2_df, get.NO2_concentration, 
    'Mean NRTI NO2 in Malang City',
    'Vertical Column of NO2 (mol/m^2)')
land_cover = get.plot_cover_data()
malang_map = 'assets/map.html'

app.layout = html.Div(children=[
    html.H1(children='Dashboard'),

    html.Div(children='''
        
    '''),

    html.Div(id='map', children=[
        html.Iframe(
            src=malang_map,
            style={'height': '400px', 'width': '100%'},
        )
    ]),

    dcc.Graph(
        id='land_cover',
        figure=land_cover,
        style={
            'width': '100%', 'margin-left': 'auto'}
    ),
    dcc.Graph(
        id='O3_plot',
        figure=O3_plot,
        style={
            'width': '100%', 'margin-left': 'auto'}
    ),
    dcc.Graph(
        id='NO2_plot',
        figure=NO2_plot,
        style={
            'width': '100%', 'margin-left': 'auto'}
    ),
])

if __name__ == '__main__':
    app.run(debug=True)