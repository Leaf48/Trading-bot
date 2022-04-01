from methods.BybitClient import Bybit
from rich import print
from datetime import datetime, timedelta

TESTKEYS = {
    "APIKEY": "",
    "APISECRET": ""
}

client = Bybit(TESTKEYS["APIKEY"], TESTKEYS["APISECRET"]).client


def timestampToDate(timestamp: int):
    return datetime.fromtimestamp(timestamp)


position = client.rest.linear.private_position_list(
    symbol="BTCUSDT"
).json()
print(position["result"][0]["unrealised_pnl"])