import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, set_props
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from tinkoff.invest.schemas import CandleInterval
from datetime import datetime, timedelta
from Gd import Get_data as Gd
from Gd import Get_instr as Gi
from flask import request, abort, g, Flask, render_template, flash
import os
from FDataBase import FDataBase
import sqlite3

"""Error_handler"""


def instr_error_handler(err):
    set_props("error-output", dict(is_open=True))


"""Configuration"""

DATABASE = '/tmp/data_base.db'
DEBUG = True
SECRET_KEY = 'rdtfyghujkmlfyghj'

"""Read Data"""

token = Gd._token_read()
Gi.dataframe_maker(token)

Data = Gi.dataframe_reader()
filtered_data = Data[["name", "ticker"]]
instruments = dict(zip(filtered_data['ticker'], filtered_data['name']))

candle_interval_selector = dcc.Dropdown(
    id='candle_selector',
    value=CandleInterval.CANDLE_INTERVAL_HOUR,
    options=[],
    multi=False,
    clearable=False
)

instrument_select = dcc.Dropdown(
    id='instrument_selector',
    value='lkoh',
    options=instruments,
    multi=False,
    clearable=False
)
time_range_select = dcc.DatePickerRange(
    id='my-date-picker-range',
    min_date_allowed=(datetime.today() - timedelta(days=365)).date(),
    max_date_allowed=datetime.today().date() - timedelta(days=1),
    initial_visible_month=datetime.today().date(),
    start_date=datetime.today().date() - timedelta(days=2),
    end_date=datetime.today().date() - timedelta(days=1)

)

server = Flask(__name__)
server.config.from_object(__name__)

server.config.update(dict(DATABASE=os.path.join(server.root_path, 'data_base.db')))


def connect_db():
    conn = sqlite3.connect((server.config['DATABASE']))
    conn.row_factory = sqlite3.Row
    return conn


def create_db():
    db = connect_db()
    with server.open_resource('sq_db.sql', mode='r') as f:
        db.cursor().executescript(f.read())
        db.commit()
        db.close()


def get_db():
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db


@server.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()


@server.route('/')
def index():
    db = get_db()
    dbase = FDataBase(db)
    return render_template('index.html', menu=dbase.getMenu(), posts=dbase.getPostsAnonce())


@server.route('/contact', methods=["POST", "GET"])
def contact():
    db = get_db()
    dbase = FDataBase(db)
    if request.method == "POST":
        if len(request.form['username']) > 2:
            flash('Message sent', category='success')
        else:
            flash('Send error', category='error')
    return render_template('contact.html', title='Feedback', menu=dbase.getMenu())


@server.route('/add_post', methods=["POST", "GET"])
def addPost():
    db = get_db()
    dbase = FDataBase(db)
    if request.method == "POST":
        if len(request.form['name']) > 4 and len(request.form['post']) > 10:
            res = dbase.addPost(request.form['name'], request.form['post'])
            print(res)
            if not res:
                flash('Error', category='error')
            else:
                flash('Post added successfully', category='success')
        else:
            flash('Error', category='error')
    return render_template('add_post.html', menu=dbase.getMenu(), title='Add post')


@server.route('/post/<int:id_post>')
def showPost(id_post):
    db = get_db()
    dbase = FDataBase(db)
    title, post = dbase.getPost(id_post)
    if not title:
        abort(404)
    return render_template('post.html', menu=dbase.getMenu(), title=title, post=post)


@server.errorhandler(404)
def pageNotFound(error):
    return render_template('page404.html', title='Page not found'), 404


"""DASH_APP"""

app = dash.Dash(server=server, routes_pathname_prefix="/dash/", external_stylesheets=[dbc.themes.BOOTSTRAP])

"""Layout"""

app.layout = dbc.Container([
    dbc.Row([html.H1('Welcome to build Japanese candles', style={'margin-bottom': 20})]),
    dbc.Row([dbc.Col([
        dbc.Alert(
            "Unfortunately, data for the tool is not available. Choose another",
            id="error-output",
            dismissable=True,
            fade=True,
            is_open=False,
            duration=4000,
            color='danger'
        )], width=4, align='start')], style={'margin-bottom': 10}),
    dbc.Row([
        dbc.Col([
            html.Div('Select a time interval')
        ], width=3)
    ], style={'margin-bottom': 10}),
    dbc.Row([
        dbc.Col([
            html.Div(time_range_select)
        ], width=3)
    ], style={'margin-bottom': 20}),
    dbc.Row([
        dbc.Col([
            html.Div('Select a candle interval'),
        ], width=2, align='start'),
        dbc.Col([
            html.Div('Select a name of instrument'),
        ], width=2, align='start')
    ], style={'margin-bottom': 10}, justify='start'),
    dbc.Row([
        dbc.Col([
            html.Div(candle_interval_selector)
        ], width=2, align='center'),
        dbc.Col([
            html.Div(instrument_select)
        ], width=2, align='center')
    ], style={'margin-bottom': 30}),
    dbc.Row(dbc.Col([html.Button('Plot graph', id='data_button', n_clicks=0, className='mr-2')], width=1),
            style={'margin-bottom': 10}),
    dbc.Row(dbc.Col([dcc.Graph(id='candle_graph')], width=6))
], style={'margin-left': '40px', 'margin-right': '80px', 'margin-top': '20px'}, fluid=True)

"""Callback"""


@app.callback(Output('candle_selector', 'options'),
              Output('candle_selector', 'value'),
              Input('my-date-picker-range', 'start_date'),
              Input('my-date-picker-range', 'end_date')
              )
def candle_interval_limiter(start_date, end_date):
    candle_selector_options = []
    date_range = datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)
    if date_range <= timedelta(days=7):
        candle_selector_options.append({'label': 'hour', 'value': CandleInterval.CANDLE_INTERVAL_HOUR})
    if date_range > timedelta(weeks=1):
        candle_selector_options.append({'label': 'week', 'value': CandleInterval.CANDLE_INTERVAL_WEEK})
    if date_range > timedelta(days=32):
        candle_selector_options.append({'label': 'month', 'value': CandleInterval.CANDLE_INTERVAL_MONTH})
    if date_range > timedelta(days=1):
        candle_selector_options.append({'label': 'day', 'value': CandleInterval.CANDLE_INTERVAL_DAY})
        interval = CandleInterval.CANDLE_INTERVAL_DAY
    else:
        interval = CandleInterval.CANDLE_INTERVAL_HOUR
    return candle_selector_options, interval


@app.callback(Output(component_id='candle_graph', component_property='figure'),
              Input(component_id='data_button', component_property='n_clicks'),
              State(component_id='my-date-picker-range', component_property='start_date'),
              State(component_id='my-date-picker-range', component_property='end_date'),
              State(component_id='candle_selector', component_property='value'),
              State(component_id='instrument_selector', component_property='value'),
              on_error=instr_error_handler

              )
def drow_candle(n, start_date, end_date, interval, ticker):
    ot = datetime.fromisoformat(start_date)
    do = datetime.fromisoformat(end_date)
    figi = Gi.figi_finder(ticker)
    Data = Gd.Get_candels(
        token,
        figi,
        ot,
        do, interval)
    figg = go.Figure(data=[go.Candlestick(x=Data['time'],
                                          open=Data['open'],
                                          high=Data['high'],
                                          low=Data['low'],
                                          close=Data['close'])])
    return figg


if __name__ == '__main__':
    server.run(debug=True)
