import numpy as np
import pandas as pd
import geopandas as gpd
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px

###########################
# Model / Data manipulation
###########################

filenames = ['confirmed', 'deaths', 'recovered']
baseURL = "https://raw.github.com/CSSEGISandData/COVID-19/master/" \
          "csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_"

df_list = [pd.read_csv(baseURL + i + '_global.csv') for i in filenames]
for df, kind in zip(df_list, filenames):
    df['kind'] = kind
df = pd.concat(df_list)
df.rename(columns={'Country/Region': 'Country'}, inplace=True)

df = df.groupby(['Country', 'kind']).sum()
df.reset_index(inplace=True)
df_melt = df.drop(['Lat', 'Long'], axis=1).melt(
    id_vars=['Country', 'kind'], value_name='value', var_name='date')
df_melt.date = pd.to_datetime(df_melt.date)

lastday = df_melt.date.max()

df_lastday = df_melt.query('kind == "deaths" and date == @lastday')[['Country', 'value']]
df_lastday = df_lastday.groupby('Country').sum().sort_values(by='value', ascending=False).reset_index()

world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
world.name.replace({'Bosnia and Herz.': 'Bosnia and Herzegovina',
                    'Macedonia': 'North Macedonia'},
                   inplace=True)
world.loc[world.name == 'France', 'iso_a3'] = "FRA"
world.loc[world.name == 'Norway', 'iso_a3'] = "NOR"
world.rename(columns={'name': 'Country'}, inplace=True)
world = world.set_index('Country').join(df_lastday.set_index('Country'), on='Country')
world.reset_index(inplace=True)
world.value.fillna(0, inplace=True)
world['logvalue'] = world.value.apply(lambda x: np.log(x + 1))  # Use log for better data display

fig = px.choropleth(world,
                    locations="iso_a3",
                    scope='europe',
                    color="logvalue",
                    hover_name="Country",
                    labels={'value': 'deaths'},
                    height=1000,
                    width=1000,
                    hover_data=["value"],

                    color_continuous_scale="OrRd")
fig.layout.coloraxis.showscale = False
fig.layout.dragmode = False

def create_time_series(df, title):
    return {
        'data': [dict(
            x=df['date'],
            y=df['value'],
            mode='lines+markers'
        )],
        'layout': {
            'height': 200,
            'margin': {'l': 20, 'b': 30, 'r': 10, 't': 10},
            'annotations': [{
                'x': 0, 'y': 0.85, 'xanchor': 'left', 'yanchor': 'bottom',
                'xref': 'paper', 'yref': 'paper', 'showarrow': False,
                'align': 'left', 'bgcolor': 'rgba(255, 255, 255, 0.5)',
                'text': title
            }],
            'yaxis': {'type': 'linear'},
            'xaxis': {'showgrid': False}
        }
    }


##########################
# View / Layout definition
##########################

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.Div([
        dcc.Graph(
            id='main',
            figure=fig
        ),
        dcc.Graph(
            id='time-series',
            figure=create_time_series(df_melt.query("Country == 'Italy' and kind == 'deaths'"), "Italy")),
    ], style={'width': '80%', 'display': 'inline-block', 'padding': '0'}),
 #   html.Div([
 #       dcc.Textarea(
 #           placeholder='Enter a value...',
 #           value='This is a TextArea component',
 #           id='textbox',
 #           style={'width': '100%'}
 #       )
 #   ]),

])


#####################################
# Controller / Component interactions
#####################################

#@app.callback(
#    Output('textbox', 'value'),
#    [Input('main', 'hoverData')])
#def display_hover_data(hoverData):
#    return json.dumps(hoverData, indent=2)


@app.callback(
    dash.dependencies.Output('time-series', 'figure'),
    [dash.dependencies.Input('main', 'hoverData')])
def update_timeseries(hoverData):
    country = hoverData['points'][0]['hovertext']
    dfx = df_melt.query("Country == @country and kind == 'deaths'")
#    title = '<b>{}</b><br>{}'.format(country)
    return create_time_series(dfx, country)


if __name__ == '__main__':
    app.run_server(debug=True)
