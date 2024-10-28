import sqlite3
from tinkoff.invest import Client
import pandas as pd
import csv
import sqlalchemy
class Get_data:
    @staticmethod
    def Get_candels(token, figi, ot, do, candle_interval):
        with Client(token) as client:
            CandlesData = client.market_data.get_candles(figi=figi,
                                                         from_=ot,
                                                         to=do,
                                                         interval=candle_interval).candles
            Candles = pd.DataFrame([{
                'time': row.time,
                'volume': row.volume,
                'open': Get_data.coin(row.open),
                'close': Get_data.coin(row.close),
                'high': Get_data.coin(row.high),
                'low': Get_data.coin(row.low)
            } for row in CandlesData])
            return Candles

    @staticmethod
    def coin(coins):
        return coins.units + coins.nano / 1e9

    @staticmethod
    def _token_read():
        try:
            with open('tokens.csv', mode='r', newline='', encoding='utf-8') as file:
                csvreader = csv.reader(file)
                token = ''
                for row in csvreader:
                    token = row[1]
                return token
        except FileNotFoundError:
            print("Файл с токеном не найден, введите токен вручную:")
            return token
class Get_instr:

    @staticmethod
    def dataframe_maker(token):
        with Client(token) as client:
            SharesData = client.instruments.shares(instrument_status=1).instruments
            Shares = pd.DataFrame([{
                'name': row.name,
                'ticker': row.ticker.lower(),
                'figi': row.figi
            } for row in SharesData])
            con = sqlite3.connect('data_base.db')
            Shares.to_sql(name='shares',con=con, if_exists='replace', index=True, index_label=None)
            con.close()

    @staticmethod
    def dataframe_reader():
        con = sqlite3.connect('data_base.db')
        Data = pd.read_sql(sql='SELECT * FROM shares',con=con)
        con.close()
        return Data

    @staticmethod
    def figi_finder(ticker):
        Data = Get_instr.dataframe_reader()
        filtered_str = Data.loc[Data['ticker'] == ticker.lower()]
        return repr(filtered_str.figi.squeeze()).replace("'", "")
