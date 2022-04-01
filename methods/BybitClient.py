from bybit import bybit
import pybybit


class Bybit:
    def __init__(self, api, apiSec, symbol="BTCUSDT"):
        # default symbol
        self.symbol = symbol

        # api settings
        self.api = api
        self.apiSec = apiSec
        self.client = pybybit.API(key=self.api, secret=self.apiSec, testnet=True)
        # self.client = bybit(test=True, api_key=self.api, api_secret=self.apiSec)