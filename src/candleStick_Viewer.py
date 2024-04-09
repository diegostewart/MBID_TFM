from dash import Dash, dcc, html
from dash.dependencies import Input, Output
from cassandra.cluster import Cluster
import dash_bootstrap_components as dbc
import pandas as pd
import pandas_ta as ta
import plotly.graph_objs as go
import plotly.express as px
from statsmodels.tsa.arima.model import ARIMA


# Connect to Cassandra outside of callback function
cluster = Cluster(['localhost'], port=9042)
session = cluster.connect()
session.set_keyspace('dmsb_tfm')


app = Dash(__name__)

app.layout = html.Div([
    dcc.Interval(id='interval-component', interval=1000, n_intervals=0),
    html.Div([
        html.H3('BTC/EUR REAL-TIME PREDICTION',
                style={'text-align': 'center'})
    ],
        style={'display': 'flex', 'justify-content': 'center',
               'align-items': 'center'}
    ),


    html.Div([
        html.P('Nº of candles to perform ARIMA'),
        dcc.Slider(0, 720, 36, value=720, id="candle_slider",)
    ], style={'width': '80%', 'margin': 'auto', 'text-align': 'center'}),

    html.Div([
        html.P('ARIMA(p,d,q)'),
        dcc.Input(
            id="input_p",
            type='number',
            placeholder="insert p ",
            min=0, max=15, step=1,
            style={'margin-right': '10px'},
        ),
        dcc.Input(
            id="input_d",
            type='number',
            placeholder="insert d",
            min=0, max=15, step=1,
            style={'margin-right': '10px'},
        ),
        dcc.Input(
            id="input_q",
            type='number',
            placeholder="insert q",
            min=0, max=15, step=1,

        ),

    ], style={'width': '80%', 'margin': 'auto', 'text-align': 'center', }),
    html.Div(
        dbc.Button('Save', id='save_btn', n_clicks=0),
        style={'display': 'flex', 'justify-content': 'center',
               'margin-bottom': '20px', 'margin-top': '20px'}
    ),



    dcc.Graph(id='candlestick-graph'),

    html.Div([
        dcc.Slider(5, 60, 5, value=20, id="show_candle_slider",)
    ], style={'width': '80%', 'margin': 'auto', 'text-align': 'center'}),
])


@app.callback(Output('save_btn', 'n_clicks'),  # Dummy output to prevent callback exception
              Input('save_btn', 'n_clicks'),
              Input('candle_slider', 'value'),
              Input('input_p', 'value'),
              Input('input_d', 'value'),
              Input('input_q', 'value'),
              prevent_initial_call=True
              )
def update_config_values(n_clicks, candle_slider, value_p, value_d, value_q):
    if (not any(item is None or item == '' for item in (
            n_clicks, candle_slider, value_p, value_d, value_q))):
        update_query = "UPDATE configuration SET candle_number=%s, ARIMA_p=%s, ARIMA_d=%s, ARIMA_q=%s WHERE symbol='BTCEUR'"
        print(update_query)
        try:
            session.execute(update_query, (candle_slider,
                                           value_p, value_d, value_q))
            print('Values saved correctly')
        except Exception as e:
            print(f'Error saving data: {e}')


@app.callback(Output('candlestick-graph', 'figure'),
              Input('interval-component', 'n_intervals'),
              Input('show_candle_slider', 'value'),
              )
def update_figure(n_intervals, slider_value):
    # print(candle_slider,value_p, value_d, value_q)
    query = "SELECT * FROM candlesticks LIMIT 500"

    result = session.execute(query)
    rows = [row._asdict() for row in result]
    df = pd.DataFrame(rows)

    query = "SELECT * FROM candlesticks_pred LIMIT 300"
    result = session.execute(query)
    rows = [row._asdict() for row in result]
    df_pred = pd.DataFrame(rows)

    # We filter only to have the newest data for each time
    idx = df.groupby('start_time')['event_time'].idxmax()
    df = df.loc[idx]
    df = df.sort_values(by='start_time', ascending=True)

    desired_columns = ['close', 'high', 'low', 'open', 'start_time']

    df_display = df.loc[:, desired_columns]
    df_pred.rename(columns={'open': 'open_pred',
                   'high': 'high_pred',
                            'low': 'low_pred',
                            'close': 'close_pred'}, inplace=True)
    merged_df = pd.merge(df_display, df_pred, on='start_time', how='inner')

    merged_df = merged_df.tail(slider_value)

    candles = go.Figure(
        data=[
            go.Candlestick(
                x=merged_df.start_time,
                open=merged_df.open,
                high=merged_df.high,
                low=merged_df.low,
                close=merged_df.close,
                name='Actual Value',
                opacity=1
            ),
            go.Candlestick(
                x=merged_df.start_time,
                open=merged_df.open_pred,
                high=merged_df.high_pred,
                low=merged_df.low_pred,
                close=merged_df.close_pred,
                name='Predicted Value',
                opacity=0.5
            )
        ]
    )
    # candle_prediction = go.Figure(
    #     data=[
    #         go.Candlestick(
    #             x=merged_df.start_time,
    #             open=merged_df.open_pred,
    #             high=merged_df.high_pred,
    #             low=merged_df.low_pred,
    #             close=merged_df.close_pred
    #         )
    #     ]
    # )

    candles.update_layout(
        xaxis_rangeslider_visible=False,
        height=550,
    )
    # candle_prediction.update_layout(
    #     xaxis_rangeslider_visible=False, height=400)

    # indicator = px.line(x=df.event_time, y=df.rsi, height=300)

    # return candles, indicator
    return candles


if __name__ == '__main__':
    app.run_server(debug=True)
