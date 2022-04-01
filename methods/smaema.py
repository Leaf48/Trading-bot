from BybitClient import Bybit
from rich import print
from datetime import datetime, timedelta
from time import sleep
from DiscordWebhook import postWebhook
import discord
import asyncio
from multiprocessing import Process
import threading
import concurrent.futures

TESTKEYS = {
    "APIKEY": "",
    "APISECRET": ""
}

OPTIONS = {
    "symbol": "BTCUSDT",
    "qty": 0.013
}

client = Bybit(TESTKEYS["APIKEY"], TESTKEYS["APISECRET"]).client


def timestampToDate(timestamp: int):
    return datetime.fromtimestamp(timestamp)


def get_myWallet(coin="USDT"):
    wallet = client.rest.inverse.private_wallet_balance(
        coin=coin
    ).json()
    try:
        return int(wallet["result"][coin]["equity"])
    except Exception as e:
        print(e)
        return 0


def get_price(intervalTime: int = 60, getTimeFrom: int = 200):
    # seconds | 何秒前から取得するか | 秒数指定必須
    getTimeFrom = 3600 * getTimeFrom
    time = int((datetime.now() - timedelta(seconds=getTimeFrom)).timestamp())
    """
    1 - 1 minute
    60 - 1 hour
    D - 1 day
    W - 1 week
    M - 1 month
    """
    result = client.rest.linear.public_kline(OPTIONS["symbol"], interval=intervalTime, from_=time).json()

    """
        :return
            "id": 3866948,
            "symbol": "BTCUSDT",
            "period": "1",
            "start_at": 1577836800, // Abandoned!!
            "volume": 1451.59,
            "open": 7700,           // Abandoned!!
            "high": 999999,
            "low": 0.5,
            "close": 6000,
            "interval": 1,
            "open_time": 1577836800,
            "turnover": 2.4343353100000003,
    """
    return result["result"]


flags = {
    "position": {
        "available": False,
        "side": None,
    },
    "goldencross": False,
    "deadcross": False,
    "wallet": get_myWallet(),
    "profit": {
        "take_profit": False,
        "profit": 20,
    }
}


# before に入る数字は マイナス
def get_sma(period: int, data: dict = get_price(60, 200), before: int = None):
    # ~ 200h
    data1 = data
    # 200h ~ 400h
    data2 = get_price(60, 400)
    # # 400 ~ 600h
    data3 = get_price(60, 600)
    # 600時間分のデータ
    data = data3 + data2 + data1

    # before = -1 でひとつ前のデータ | get_price関数を使っても最新のデータは取得できなかった
    if before is not None:
        # print("if")
        sma = sum([i["close"] for i in data[-1 * period + before:before]]) / period

    # beforeで指定しない場合ひとつ前のデータ(-1)を返す
    else:
        # print("else")
        sma = sum([i["close"] for i in data[-1 * (period + 1):-1]]) / period
    return sma


def get_ema(period: int, data: dict, before: int = None):
    # ~ 200h
    data1 = data
    # 200h ~ 400h
    data2 = get_price(60, 400)
    # # 400 ~ 600h
    data3 = get_price(60, 600)
    # 600時間分のデータ
    data = data3 + data2 + data1

    # beforeで指定するときは一つ前のデータを-1とする。
    # なので2つ前のデータの場合は-2
    if before is not None:
        # print("if")
        sma = sum([i["close"] for i in data[-2 * period + before: -1 * period + before]]) / period
        ema = sma
        for i in range(period):
            ema = data[-1 * period + i + before]["close"] * (2 / (period + 1)) + (1 - 2 / (period + 1)) * ema

    # beforeで指定しない場合は-1(一つ前のデータ)が選択される
    else:
        # print("else")
        sma = sum([i["close"] for i in data[-2 * period + -2: -1 * period + -2]]) / period
        ema = sma
        for i in range(period):
            ema = data[-1 * period + i + -2]["close"] * (2 / (period + 1)) + (1 - 2 / (period + 1)) * ema

    return ema


def goldencross(data: dict, flag: dict = flags):
    print("goldencross")
    # goldencrossが Trueの場合はFalseに変換されてここは動作しない
    # この処理は最初の買いの処理だけを一回行い、それ以降はdeadcrossが発動するまではelseの処理を行う
    if not flag["goldencross"]:
        # EMA25が右肩上がりの場合
        if get_ema(25, data, -1) > get_ema(25, data, -2) > get_ema(25, data, -3):
            print("EMA25が右肩上がりの場合 | 1/5")
            # EMA50が右肩上がりの場合
            if get_ema(50, data, -1) > get_ema(50, data, -2) > get_ema(50, data, -3):
                print("EMA50が右肩上がりの場合 | 2/5")
                # 3つ前のEMA25が3つ前のEMA50より小さい場合
                if get_ema(25, data, -3) < get_ema(50, data, -3):
                    print("3つ前のEMA25が3つ前のEMA50より小さい場合 | 3/5")
                    # 2つ前のEMA25が2つ前のEMA50より小さい場合
                    if get_ema(25, data, -2) < get_ema(50, data, -2):
                        print("2つ前のEMA25が2つ前のEMA50より小さい場合 | 4/5")
                        # 1つ前のEMA25が1つ前のEMA50より大きい場合 | 1つ前 = 最新のデータより1つ前 / ここでは最新のデータとする
                        if get_ema(25, data, -1) > get_ema(50, data, -1):
                            print("1つ前のEMA25が1つ前のEMA50より大きい場合 | 5/5")
                            flag["goldencross"] = True
                            return True
    else:
        print("GOLDENCROSSが発動しています")
        return False


def deadcross(data: dict, flag: dict = flags):
    print("deadcross")
    # deadcrossが Trueの場合はFalseに変換されてここは動作しない
    # この処理は最初の売りの処理だけを一回行い、それ以降はgoldencrossが発動するまではelseの処理を行う
    if not flag["deadcross"]:
        # EMA25が右肩下がりの場合
        if get_ema(25, data, -1) < get_ema(25, data, -2) < get_ema(25, data, -3):
            print("EMA25が右肩下がりの場合 | 1/5")
            # EMA50が右肩下がりの場合
            if get_ema(50, data, -1) < get_ema(50, data, -2) < get_ema(50, data, -3):
                print("EMA50が右肩下がりの場合 | 2/5")
                # 3つ前のEMA25が3つ前のEMA50より大きい場合
                if get_ema(25, data, -3) > get_ema(50, data, -3):
                    print("3つ前のEMA25が3つ前のEMA50より大きい場合 | 3/5")
                    # 2つ前のEMA25が2つ前のEMA50より大きい場合
                    if get_ema(25, data, -2) > get_ema(50, data, -2):
                        print("2つ前のEMA25が2つ前のEMA50より大きい場合 | 4/5")
                        # 1つ前のEMA25が1つ前のEMA50より小さい場合 | 1つ前 = 最新のデータより1つ前 / ここでは最新のデータとする
                        if get_ema(25, data, -1) < get_ema(50, data, -1):
                            print("1つ前のEMA25が1つ前のEMA50より小さい場合 | 5/5")
                            flag["deadcross"] = True
                            return True
    else:
        print("DEADCROSSが発動しています")
        return False


def buy(data: dict, flag: dict = flags):
    place = client.rest.linear.private_order_create(
        symbol=OPTIONS["symbol"],
        side="Buy",
        order_type="Market",
        qty=OPTIONS["qty"],
        time_in_force="GoodTillCancel",
        reduce_only=False,
        close_on_trigger=False
    ).json()
    print(place)
    flag["position"]["available"] = True
    flag["position"]["side"] = "Buy"


def sell(data: dict, flag: dict = flags):
    place = client.rest.linear.private_order_create(
        symbol=OPTIONS["symbol"],
        side="Sell",
        order_type="Market",
        qty=OPTIONS["qty"],
        time_in_force="GoodTillCancel",
        reduce_only=False,
        close_on_trigger=False
    ).json()
    print(place)
    flag["position"]["available"] = True
    flag["position"]["side"] = "Sell"


def close_position(data: dict, flag: dict = flags):
    latestPosition = client.rest.linear.private_order_list(
        symbol=OPTIONS["symbol"]
    ).json()
    positionPrice = float(latestPosition["result"]["data"][0]["last_exec_price"])

    nowPrice = float(client.rest.inverse.public_tickers(
        symbol=OPTIONS["symbol"]
    ).json()["result"][0]["last_price"])

    if flag["position"]["side"] == "Buy":
        # 買った時の価額より今の価額のほうが大きい場合 = プラスになっている
        if positionPrice < nowPrice:
            position = client.rest.linear.private_position_tradingstop(
                symbol=OPTIONS["symbol"],
                side="Buy",
                take_profit=nowPrice
            ).json()
        # 買った時の価額より今の価額のほうが小さい場合 = マイナスになっている
        else:
            position = client.rest.linear.private_position_tradingstop(
                symbol=OPTIONS["symbol"],
                side="Buy",
                stop_loss=nowPrice
            ).json()

        flag["position"]["available"] = False
        flag["position"]["side"] = None

        discord_content = {
            "content": "<@>",
            "embeds": [
                {
                    "title": "決済しました- Buy",
                    "color": 15258703,
                    "fields": [
                        {
                            "name": "Date",
                            "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                            "inline": False
                        },
                        {
                            "name": "Wallet",
                            "value": f"{get_myWallet()}$",
                            "inline": False
                        },
                        {
                            "name": "Profit",
                            "value": get_myWallet() - flag["wallet"],
                            "inline": False
                        }
                    ],
                }
            ]
        }
        postWebhook(discord_content)
        flag["wallet"] = get_myWallet()

    elif flag["position"]["side"] == "Sell":
        # 売った時の価額より今の価額のほうが小さい場合 = プラスになっている
        if positionPrice > nowPrice:
            position = client.rest.linear.private_position_tradingstop(
                symbol=OPTIONS["symbol"],
                side="Sell",
                take_profit=nowPrice
            ).json()
        # 売った時の価額より今の価額のほうが大きい場合 = マイナスになっている
        else:
            position = client.rest.linear.private_position_tradingstop(
                symbol=OPTIONS["symbol"],
                side="Sell",
                stop_loss=nowPrice
            ).json()

        flag["position"]["available"] = False
        flag["position"]["side"] = None

        discord_content = {
            "content": "<@>",
            "embeds": [
                {
                    "title": "決済しました- Sell",
                    "color": 15258703,
                    "fields": [
                        {
                            "name": "Date",
                            "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                            "inline": False
                        },
                        {
                            "name": "Wallet",
                            "value": f"{get_myWallet()}$",
                            "inline": False
                        },
                        {
                            "name": "Profit",
                            "value": get_myWallet() - flag["wallet"],
                            "inline": False
                        }
                    ],
                }
            ]
        }
        postWebhook(discord_content)
        flag["wallet"] = get_myWallet()


class Client(discord.Client):
    async def on_ready(self):
        print(f"Bot has been started!")
        await self.change_presence(activity=discord.Game(name=f"USDT: {get_myWallet()}$", type=1))
        while True:
            await self.change_presence(activity=discord.Game(name=f"{get_myWallet()}$", type=1))
            # print("test")
            await asyncio.sleep(10)

    async def on_message(self, message):
        if message.author.bot:
            return

        try:
            if message.content.startswith("/btc"):
                args = message.content.split()

                if args[1] == "p":
                    print("Profit")
                    try:
                        if type(int(args[2])) == int:
                            flags["profit"]["profit"] = int(args[2])
                            embed = discord.Embed(
                                title="利確の設定を更新しました",
                                color=0xe67e22
                            )
                            embed.add_field(
                                name="position-available",
                                value=f'{flags["position"]["available"]}'
                            )
                            embed.add_field(
                                name="position-side",
                                value=f'{flags["position"]["side"]}'
                            )
                            embed.add_field(
                                name="goldencross",
                                value=f'{flags["goldencross"]}'
                            )
                            embed.add_field(
                                name="deadcross",
                                value=f'{flags["deadcross"]}'
                            )
                            embed.add_field(
                                name="wallet",
                                value=f'{flags["wallet"]}$'
                            )
                            embed.add_field(
                                name="profit-take_profit",
                                value=f'{flags["profit"]["take_profit"]}'
                            )
                            embed.add_field(
                                name="profit-profit",
                                value=f'{flags["profit"]["profit"]}'
                            )
                            await message.channel.send(embed=embed)
                    except:
                        pass

                elif args[1] == "tp":
                    print("TakeProfit")

                    try:
                        if args[2] == "True" or args[2] == "true":
                            print("True")
                            flags["profit"]["take_profit"] = True
                        else:
                            print("False")
                            flags["profit"]["take_profit"] = False

                        embed = discord.Embed(
                            title=f"利確の設定を{flags['profit']['take_profit']}にしました",
                            color=0xe67e22
                        )
                        embed.add_field(
                            name="position-available",
                            value=f'{flags["position"]["available"]}'
                        )
                        embed.add_field(
                            name="position-side",
                            value=f'{flags["position"]["side"]}'
                        )
                        embed.add_field(
                            name="goldencross",
                            value=f'{flags["goldencross"]}'
                        )
                        embed.add_field(
                            name="deadcross",
                            value=f'{flags["deadcross"]}'
                        )
                        embed.add_field(
                            name="wallet",
                            value=f'{flags["wallet"]}$'
                        )
                        embed.add_field(
                            name="profit-take_profit",
                            value=f'{flags["profit"]["take_profit"]}'
                        )
                        embed.add_field(
                            name="profit-profit",
                            value=f'{flags["profit"]["profit"]}'
                        )
                        await message.channel.send(embed=embed)

                    except:
                        pass

                elif args[1] == "gc":
                    print("GoldenCross")
                    try:
                        if args[2] == "True" or args[2] == "true":
                            print("True")
                            flags["goldencross"] = True
                        else:
                            print("False")
                            flags["goldencross"] = False

                        embed = discord.Embed(
                            title=f"ゴールデンクロスを{flags['goldencross']}にしました",
                            color=0xe67e22
                        )
                        embed.add_field(
                            name="position-available",
                            value=f'{flags["position"]["available"]}'
                        )
                        embed.add_field(
                            name="position-side",
                            value=f'{flags["position"]["side"]}'
                        )
                        embed.add_field(
                            name="goldencross",
                            value=f'{flags["goldencross"]}'
                        )
                        embed.add_field(
                            name="deadcross",
                            value=f'{flags["deadcross"]}'
                        )
                        embed.add_field(
                            name="wallet",
                            value=f'{flags["wallet"]}$'
                        )
                        embed.add_field(
                            name="profit-take_profit",
                            value=f'{flags["profit"]["take_profit"]}'
                        )
                        embed.add_field(
                            name="profit-profit",
                            value=f'{flags["profit"]["profit"]}'
                        )

                        await message.channel.send(embed=embed)

                    except:
                        pass

                elif args[1] == "dc":
                    print("DeadCross")
                    try:
                        if args[2] == "True" or args[2] == "true":
                            print("True")
                            flags["deadcross"] = True
                        else:
                            print("False")
                            flags["deadcross"] = False

                        embed = discord.Embed(
                                title=f"デッドクロスを{flags['deadcross']}にしました",
                            color=0xe67e22
                        )
                        embed.add_field(
                            name="position-available",
                            value=f'{flags["position"]["available"]}'
                        )
                        embed.add_field(
                            name="position-side",
                            value=f'{flags["position"]["side"]}'
                        )
                        embed.add_field(
                            name="goldencross",
                            value=f'{flags["goldencross"]}'
                        )
                        embed.add_field(
                            name="deadcross",
                            value=f'{flags["deadcross"]}'
                        )
                        embed.add_field(
                            name="wallet",
                            value=f'{flags["wallet"]}$'
                        )
                        embed.add_field(
                            name="profit-take_profit",
                            value=f'{flags["profit"]["take_profit"]}'
                        )
                        embed.add_field(
                            name="profit-profit",
                            value=f'{flags["profit"]["profit"]}'
                        )

                        await message.channel.send(embed=embed)
                    except:
                        pass

                elif args[1] == "av":
                    try:
                        if args[2] == "True" or args[2] == "true":
                            print("True")
                            flags["position"]["available"] = True
                        else:
                            print("False")
                            flags["position"]["available"] = False

                        embed = discord.Embed(
                            title=f"ポジションを{flags['position']['available']}にしました",
                            color=0xe67e22
                        )
                        embed.add_field(
                            name="position-available",
                            value=f'{flags["position"]["available"]}'
                        )
                        embed.add_field(
                            name="position-side",
                            value=f'{flags["position"]["side"]}'
                        )
                        embed.add_field(
                            name="goldencross",
                            value=f'{flags["goldencross"]}'
                        )
                        embed.add_field(
                            name="deadcross",
                            value=f'{flags["deadcross"]}'
                        )
                        embed.add_field(
                            name="wallet",
                            value=f'{flags["wallet"]}$'
                        )
                        embed.add_field(
                            name="profit-take_profit",
                            value=f'{flags["profit"]["take_profit"]}'
                        )
                        embed.add_field(
                            name="profit-profit",
                            value=f'{flags["profit"]["profit"]}'
                        )

                        await message.channel.send(embed=embed)

                    except:
                        pass

                elif args[1] == "s":
                    try:
                        if args[2].lower() == "buy":
                            flags["position"]["side"] = "Buy"
                        elif args[2].lower() == "sell":
                            flags["position"]["side"] = "Sell"
                        else:
                            flags["position"]["side"] = None

                        embed = discord.Embed(
                            title=f"ポジションのサイドを{flags['position']['side']}にしました",
                            color=0xe67e22
                        )
                        embed.add_field(
                            name="position-available",
                            value=f'{flags["position"]["available"]}'
                        )
                        embed.add_field(
                            name="position-side",
                            value=f'{flags["position"]["side"]}'
                        )
                        embed.add_field(
                            name="goldencross",
                            value=f'{flags["goldencross"]}'
                        )
                        embed.add_field(
                            name="deadcross",
                            value=f'{flags["deadcross"]}'
                        )
                        embed.add_field(
                            name="wallet",
                            value=f'{flags["wallet"]}$'
                        )
                        embed.add_field(
                            name="profit-take_profit",
                            value=f'{flags["profit"]["take_profit"]}'
                        )
                        embed.add_field(
                            name="profit-profit",
                            value=f'{flags["profit"]["profit"]}'
                        )

                        await message.channel.send(embed=embed)

                    except:
                        pass

                else:
                    embed = discord.Embed(
                        title="Usage",
                        color=0xe67e22,
                        description="/btc **args**"
                    )
                    embed.add_field(
                        name="p",
                        value="何ドルで利益確定するかを設定します"
                    )
                    embed.add_field(
                        name="tp",
                        value="take_profit設定を有効にするか設定します"
                    )
                    embed.add_field(
                        name="gc",
                        value="ゴールデンクロスを設定します"
                    )
                    embed.add_field(
                        name="dc",
                        value="デッドクロスを設定します"
                    )
                    embed.add_field(
                        name="av",
                        value="ポジションの設定をします"
                    )
                    embed.add_field(
                        name="s",
                        value="ポジションのサイドを設定します"
                    )
                    await message.channel.send(embed=embed)

        except IndexError:
            embed = discord.Embed(
                title="Current Config",
                color=0xe67e22
            )
            embed.add_field(
                name="position-available",
                value=f'{flags["position"]["available"]}'
            )
            embed.add_field(
                name="position-side",
                value=f'{flags["position"]["side"]}'
            )
            embed.add_field(
                name="goldencross",
                value=f'{flags["goldencross"]}'
            )
            embed.add_field(
                name="deadcross",
                value=f'{flags["deadcross"]}'
            )
            embed.add_field(
                name="wallet",
                value=f'{flags["wallet"]}$'
            )
            embed.add_field(
                name="profit-take_profit",
                value=f'{flags["profit"]["take_profit"]}'
            )
            embed.add_field(
                name="profit-profit",
                value=f'{flags["profit"]["profit"]}'
            )
            await message.channel.send(embed=embed)


def main():
    while True:
        price = get_price()

        # profitで終了する設定が有効の場合
        if flags["position"]["available"]:
            if flags["profit"]["take_profit"]:
                position = client.rest.linear.private_position_list(
                    symbol=OPTIONS["symbol"]
                ).json()
                # 現在の利益
                pnl = float(position["result"][0]["unrealised_pnl"])
                # 設定した利益より大きい場合
                if pnl > float(flags["profit"]["profit"]):
                    close_position(price, flags)
                    flags["deadcross"] = False
                    flags["goldencross"] = False

                    discord_content = {
                        "content": "<@>",
                        "embeds": [
                            {
                                "title": "指定された利益まで到達したので自動的に利確しました",
                                "color": 15258703,
                                "fields": [
                                    {
                                        "name": "Date",
                                        "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                                        "inline": False
                                    },
                                    {
                                        "name": "Wallet",
                                        "value": f"{get_myWallet()}$",
                                        "inline": False
                                    },
                                ],
                            }
                        ]
                    }
                    postWebhook(discord_content)

        if goldencross(price):
            discord_content = {
                "content": "<@>",
                "embeds": [
                    {
                        "title": "GoldenCross",
                        "color": 15258703,
                        "fields": [
                            {
                                "name": "Date",
                                "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                                "inline": False
                            },
                            {
                                "name": "Wallet",
                                "value": f"{get_myWallet()}$",
                                "inline": False
                            },
                        ],
                    }
                ]
            }
            postWebhook(discord_content)

            if flags["deadcross"]:
                flags["deadcross"] = False
                close_position(price, flags)
            buy(price, flags)

        if deadcross(price):
            discord_content = {
                "content": "<@>",
                "embeds": [
                    {
                        "title": "DeadCross",
                        "color": 15258703,
                        "fields": [
                            {
                                "name": "Date",
                                "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                                "inline": False
                            },
                            {
                                "name": "Wallet",
                                "value": f"{get_myWallet()}$",
                                "inline": False
                            },
                        ],
                    }
                ]
            }
            postWebhook(discord_content)

            if flags["goldencross"]:
                flags["goldencross"] = False
                close_position(price, flags)
            sell(price, flags)

        sleep(10)


# main()


if __name__ == "__main__":
    # t1 = threading.Thread(target=cl.run, args=("",))

    loop = asyncio.get_event_loop()

    cl = Client()
    print("1")

    loop.create_task(main())
    print("2")
    loop.create_task(cl.run(""))
    print("3")

    loop.run_forever()
    print("4")
    loop.close()
    print("5")
