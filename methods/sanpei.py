from BybitClient import Bybit
from time import sleep
from datetime import datetime, timedelta
from rich import print
from LineClient import LineClient
from DiscordWebhook import postWebhook
import platform
import os
import sys


# 各OSのclearコマンドを取得
def clear():
    p = platform.platform()
    if p == "Windows":
        os.system("cls")
    elif p == "Linux":
        os.system("clear")
    else:
        return print("このOSはclearコマンドに対応していません")


# Lineで通知するかDiscordで通知するか決める
try:
    if sys.argv[1]:
        notify = "Discord"
except:
    notify = "Line"


def notification(discord, Line):
    if notify == "Discord":
        postWebhook(discord)
    else:
        line.push(Line)


# 起動時のロゴ
print("""
                            ***********************
                       ***********************************
                   *******************************************%
               /**************************************************
             ********************************************************
          /****************************  ******************************         
        ******************************     ***     **********************       
       *********************   ******,    ****    ************************      
     (**********************              ***     **************************    
    ***************************                   ,**************************   
   (****************************                       ***********************  
   *****************************        *******.         *********************# 
  *****************************        **********         ********************* 
  ****************************,       .**********         *********************&
 #****************************                           ***********************
 ****************************                         **************************
 ****************************        *******           *************************
  **************************        ***********.         **********************&
  ********************   ,*        *************         ********************** 
   ******************              ,***********          *********************# 
   (*******************,                                **********************  
    *************************                         ***********************   
     &**********************     ***     ****,.,,***************************    
       *********************    ****    **********************************      
        %**************************     *********************************       
          /************************************************************         
             *******************************************************            
               /**************************************************              
                   *******************************************%                 
                       ***********************************                      
                             (**********************                            
""")

# Bybit API用の環境変数
TESTKEYS = {
    "APIKEY": "",
    "APISECRET": ""
}
MAINKEYS = {
    "APIKEY": "",
    "APISECRET": ""
}

# Bybit用のクライアント作成
bot = Bybit(TESTKEYS["APIKEY"], TESTKEYS["APISECRET"]).client

# Line用のBot作成
CHANNEL_KEY = ""
line = LineClient(CHANNEL_KEY)

# トレード時の設定等
option = {
    "symbol": "BTCUSDT",
    "qty": 0.089
}


# タイムスタンプを日付に変換する
def timestampToDate(timestamp: int):
    return datetime.fromtimestamp(timestamp)


# 今の所持金を取得する
def get_myWallet(coin, user=bot):
    wallet = user.rest.inverse.private_wallet_balance(coin=coin).json()
    try:
        # wallet + 未実現損益
        return int(wallet["result"][coin]["equity"])
    except Exception as e:
        print(e)
        return 0


# ローソク足のデータを取得
def get_kline(user, num=60):
    # 何分前からのを取得するか
    td = num
    # ローソクが何分足か指定
    interval = 1

    t = int((datetime.now() - timedelta(minutes=td)).timestamp())

    kline = user.rest.linear.public_kline(
        symbol=option["symbol"],
        interval=str(interval),
        from_=t
    ).json()

    data = kline["result"][-2]
    return {  # ローソク足のデータを返す
        "id": data["id"],
        "open_time": data["start_at"],
        "open": data["open"],
        "high": data["high"],
        "low": data["low"],
        "close": data["close"],
    }


# open high low closeを表示する
def get_ohlc(data):
    print(f"--------------------")
    print("ID", data["id"])
    print("START AT/ OPEN TIME", timestampToDate(int(data["open_time"])))
    print("始値", data["open"])
    print("高値", data["high"])
    print("安値", data["low"])
    print("終値", data["close"])
    print(f"--------------------")


# ローソクを調べる
def check_candle(data, side):
    while True:
        try:
            realbody_rate = abs(float(data["close"]) - float(data["open"])) / (float(data["high"]) - float(data["low"]))
        except ZeroDivisionError:
            realbody_rate = 0
        try:
            increase_rate = float(data["close"]) / float(data["open"]) - 1
        except ZeroDivisionError:
            increase_rate = 0
        break

    # buy
    if side == "Buy":
        print("Buy")
        # 始値が終値より高い位置にある場合 / まだ伸びる(上昇)と予想されるためFalseを返す
        if int(data["close"]) < int(data["open"]):
            print("まだ伸びそう")
            return False
        # 始値の1.0025倍よりも小さい場合
        elif increase_rate < 0.00025:
            print("increase_rate", increase_rate)
            return False
        # 実体部分の割合(ヒゲ抜き)が10%以下だった場合
        elif realbody_rate < 0.1:
            print("realbody_rate", realbody_rate)
            return False
        # どれにも該当しない場合
        else:
            print("どれにも該当しません")
            return True
    # sell
    else:
        print("Sell")
        # 始値が終値より低い位置にある場合 / まだ伸びる(減少)と予想されるためFalseを返す
        if int(data["close"]) > int(data["open"]):
            print("まだ伸びそう")
            return False
        # 始値の1.0025倍よりも小さい場合
        elif increase_rate > -0.00025:
            print("increase_rate", increase_rate)
            return False
        # 実体部分の割合(ヒゲ抜き)が10%以下だった場合
        elif realbody_rate < 0.1:
            print("realbody_rate", realbody_rate)
            return False
        else:  # どれにも該当しない場合
            print("どれにも該当しません")
            return True


def check_ascend(data, oldData):  # 増加傾向か調べる
    # 新しいデータが前データより始値が高くかつ、終値が高ければTrueを返す
    if data["open"] > oldData["open"] and data["close"] > oldData["close"]:
        return True
    else:
        return False


def check_descend(data, oldData):
    # 新しいデータが前データより始値が低くかつ、終値が低くければTrueを返す
    if data["open"] < oldData["open"] and data["close"] < oldData["close"]:
        return True
    else:
        return False


# 買い を出す
def buy_signal(user, data, oldData, flag):
    # 1本
    if flag["buy_signal"] == 0 and check_candle(data, "Buy"):
        print("1本 陽線")
        flag["buy_signal"] = 1
    # 2本
    elif flag["buy_signal"] == 1 and check_candle(data, "Buy") and check_ascend(data, oldData):
        print("2本連続で陽線")
        flag["buy_signal"] = 2
    # 3本
    elif flag["buy_signal"] == 2 and check_candle(data, "Buy") and check_ascend(data, oldData):
        print("3本連続で陽線なので" + str(data["close"]) + "で買い逆指値")
        flag["buy_signal"] = 3

        # 逆指値
        order = user.rest.linear.private_stoporder_create(
            side="Buy",
            symbol=option["symbol"],
            order_type="Market",
            qty=option["qty"],
            base_price=data["open"],
            stop_px=data["close"],  # trigger
            time_in_force="GoodTillCancel",
            reduce_only=False,
            trigger_by="LastPrice",
        ).json()
        order

        flag["order"]["exist"] = True
        flag["order"]["side"] = "Buy"

        # BOTが起動したときに送信するメッセージ
        discord_content = {
            "content": "<@>",
            "embeds": [
                {
                    "title": "BUY - 逆指値",
                    "color": 15258703,
                    "fields": [
                        {
                            "name": "Date(JST)",
                            "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                            "inline": False
                        },
                        {
                            "name": "Stop Limit",
                            "value": data["close"],
                            "inline": False
                        },
                        {
                            "name": "Open",
                            "value": data["open"],
                            "inline": True
                        },
                        {
                            "name": "High",
                            "value": data["high"],
                            "inline": True
                        },
                        {
                            "name": "Low",
                            "value": data["low"],
                            "inline": True
                        },
                        {
                            "name": "Close",
                            "value": data["close"],
                            "inline": True
                        },
                        {
                            "name": "Wallet",
                            "value": f"{get_myWallet('USDT')}$",
                            "inline": False
                        },
                    ],
                }
            ]
        }
        line_content = f"""##### BUY - 逆指値
#### Date(JST): {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
### Stop Limit: {data["close"]}
## Open {data["open"]}
## High {data["high"]}
## Low {data["low"]}
## Close {data["close"]}
# Wallet: {get_myWallet('USDT')}$"""
        notification(discord_content, line_content)

        # 現在の所持金を入れる
        flag["wallet"] = get_myWallet("USDT")

    else:
        flag["buy_signal"] = 0

    return flag  # flag["order"]の["exist"]と["side"]を返す


# 売り注文
def sell_signal(user, data, oldData, flag):
    # 1本
    if flag["sell_signal"] == 0 and check_candle(data, "Sell"):
        print("1本 陰線")
        flag["sell_signal"] = 1
    # 2本
    elif flag["sell_signal"] == 1 and check_candle(data, "Sell") and check_descend(data, oldData):
        print("2本連続で陰線")
        flag["sell_signal"] = 2
    # 3本
    elif flag["sell_signal"] == 2 and check_candle(data, "Sell") and check_descend(data, oldData):
        print("3本連続で陰線なので" + str(data["close"]) + "で売り指値")
        flag["sell_signal"] = 3

        # 逆指値
        order = user.rest.linear.private_stoporder_create(
            side="Sell",
            symbol=option["symbol"],
            order_type="Market",
            qty=option["qty"],
            base_price=data["close"],
            stop_px=data["open"],  # trigger
            time_in_force="GoodTillCancel",
            reduce_only=False,
            trigger_by="LastPrice",
        ).json()
        order

        flag["order"]["exist"] = True
        flag["order"]["side"] = "Sell"

        # BOTが起動したときに送信するメッセージ
        discord_content = {
            "content": "<@>",
            "embeds": [
                {
                    "title": "SELL - 逆指値",
                    "color": 15258703,
                    "fields": [
                        {
                            "name": "Date(JST)",
                            "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                            "inline": False
                        },
                        {
                            "name": "Stop Limit",
                            "value": data["close"],
                            "inline": False
                        },
                        {
                            "name": "Open",
                            "value": data["open"],
                            "inline": True
                        },
                        {
                            "name": "High",
                            "value": data["high"],
                            "inline": True
                        },
                        {
                            "name": "Low",
                            "value": data["low"],
                            "inline": True
                        },
                        {
                            "name": "Close",
                            "value": data["close"],
                            "inline": True
                        },
                        {
                            "name": "Wallet",
                            "value": f"{get_myWallet('USDT')}$",
                            "inline": False
                        },
                    ],
                }
            ]
        }
        line_content = f"""##### SELL - 逆指値
#### Date(JST): {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
### Stop Limit: {data["close"]}
## Open {data["open"]}
## High {data["high"]}
## Low {data["low"]}
## Close {data["close"]}
# Wallet: {get_myWallet('USDT')}$"""
        notification(discord_content, line_content)

        # 現在の所持金を入れる
        flag["wallet"] = get_myWallet("USDT")

    else:
        flag["sell_signal"] = 0

    return flag  # flag["order"]の["exist"]と["side"]を返す


# ポジションを閉じる
def close(price: float, flag, user=bot):
    # price: 平均参入価格
    nowPrice = user.rest.inverse.public_tickers(
        symbol="BTCUSDT"
    ).json()["result"][0]["last_price"]
    nowPrice = float(nowPrice)

    if flag["position"]["side"] == "Buy":
        if price < nowPrice:
            nowPrice = user.rest.inverse.public_tickers(
                symbol="BTCUSDT"
            ).json()["result"][0]["last_price"]

            position = user.rest.linear.private_position_tradingstop(
                symbol="BTCUSDT",
                side="Buy",
                take_profit=nowPrice
            ).json()
            # print(position)
        else:
            nowPrice = user.rest.inverse.public_tickers(
                symbol="BTCUSDT"
            ).json()["result"][0]["last_price"]

            position = user.rest.linear.private_position_tradingstop(
                symbol="BTCUSDT",
                side="Buy",
                stop_loss=nowPrice
            ).json()
            # print(position)

    elif flag["position"]["side"] == "Sell":
        if price > nowPrice:
            nowPrice = user.rest.inverse.public_tickers(
                symbol="BTCUSDT"
            ).json()["result"][0]["last_price"]

            position = user.rest.linear.private_position_tradingstop(
                symbol="BTCUSDT",
                side="Sell",
                take_profit=nowPrice
            ).json()
            # print(position)

        else:
            nowPrice = user.rest.inverse.public_tickers(
                symbol="BTCUSDT"
            ).json()["result"][0]["last_price"]

            position = user.rest.linear.private_position_tradingstop(
                symbol="BTCUSDT",
                side="Sell",
                stop_loss=nowPrice
            ).json()
            # print(position)


# 保持している注文を決済する
def close_position(user, data, oldData, flag):
    # 保持している注文が 買い の場合
    if flag["position"]["side"] == "Buy":
        # 前回の終値よりも小さくなった場合 / 前回のであって、注文が成立してポジションを保持した時の終値ではない
        if data["close"] < oldData["close"]:
            print("前回の終値を下回ったので" + str(data["close"]) + "あたりで成行で決済します")

            # 成行注文 すぐに売る
            latestPosition = user.rest.linear.private_order_list(symbol=option["symbol"]).json()
            positionPrice = latestPosition["result"]["data"][0]["last_exec_price"]
            close(float(positionPrice), flag)

            # BOTが起動したときに送信するメッセージ
            discord_content = {
                "content": "<@>",
                "embeds": [
                    {
                        "title": "SELL - 成行",
                        "color": 15258703,
                        "fields": [
                            {
                                "name": "Date(JST)",
                                "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                                "inline": False
                            },
                            {
                                "name": "Market",
                                "value": data["close"],
                                "inline": False
                            },
                            {
                                "name": "Open",
                                "value": data["open"],
                                "inline": True
                            },
                            {
                                "name": "High",
                                "value": data["high"],
                                "inline": True
                            },
                            {
                                "name": "Low",
                                "value": data["low"],
                                "inline": True
                            },
                            {
                                "name": "Close",
                                "value": data["close"],
                                "inline": True
                            },
                            {
                                "name": "Profit",
                                "value": f"{get_myWallet('USDT') - flag['wallet']}$",
                                "inline": False
                            },
                            {
                                "name": "Wallet",
                                "value": f"{get_myWallet('USDT')}$",
                                "inline": False
                            },
                        ],
                    }
                ]
            }
            line_content = f"""##### SELL - 成行
#### Date(JST): {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
### Market: {data["close"]}
## Open {data["open"]}
## High {data["high"]}
## Low {data["low"]}
## Close {data["close"]}
# Profit: {get_myWallet('USDT') - flag['wallet']}$
# Wallet: {get_myWallet('USDT')}$"""
            notification(discord_content, line_content)

            # 現在の所持金を入れる
            flag["wallet"] = get_myWallet("USDT")

            # 決済してポジションがないため、Falseに変える
            flag["position"]["exist"] = False

    # 保持している注文が 買い 以外の場合 = 売り
    elif flag["position"]["side"] == "Sell":
        # 前回の終値よりも大きくなった場合 / 前回のであって、注文が成立してポジションを保持した時の終値ではない
        if data["close"] > oldData["close"]:
            print("前回の終値を上回ったので" + str(data["close"]) + "あたりで成行で決済します")

            # 成行注文 すぐに売る
            latestPosition = user.rest.linear.private_order_list(symbol=option["symbol"]).json()
            positionPrice = latestPosition["result"]["data"][0]["last_exec_price"]
            close(float(positionPrice), flag)

            # BOTが起動したときに送信するメッセージ
            discord_content = {
                "content": "<@>",
                "embeds": [
                    {
                        "title": "BUY - 成行",
                        "color": 15258703,
                        "fields": [
                            {
                                "name": "Date(JST)",
                                "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                                "inline": False
                            },
                            {
                                "name": "Market",
                                "value": data["close"],
                                "inline": False
                            },
                            {
                                "name": "Open",
                                "value": data["open"],
                                "inline": True
                            },
                            {
                                "name": "High",
                                "value": data["high"],
                                "inline": True
                            },
                            {
                                "name": "Low",
                                "value": data["low"],
                                "inline": True
                            },
                            {
                                "name": "Close",
                                "value": data["close"],
                                "inline": True
                            },
                            {
                                "name": "Profit",
                                "value": f"{get_myWallet('USDT') - flag['wallet']}$",
                                "inline": False
                            },
                            {
                                "name": "Wallet",
                                "value": f"{get_myWallet('USDT')}$",
                                "inline": False
                            },
                        ],
                    }
                ]
            }
            line_content = f"""##### BUY - 成行
#### Date(JST): {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
### Market: {data["close"]}
## Open {data["open"]}
## High {data["high"]}
## Low {data["low"]}
## Close {data["close"]}
# Profit: {get_myWallet('USDT') - flag['wallet']}$
# Wallet: {get_myWallet('USDT')}$"""
            notification(discord_content, line_content)

            # 現在の所持金を入れる
            flag["wallet"] = get_myWallet("USDT")

            # 決済してポジションがないため、Falseに変える
            flag["position"]["exist"] = False

    return flag  # flag["position"]["exist"]を返す


# BuyかSellかを取得し、保持していない場合はNoneを返す
# position["result"]を引数とする
def get_side(positionResult):
    # 最初に入るのがBuy次がSell
    value = []
    count = 0
    # 基本的に ["result"]が入る / position["result"]
    try:
        for i in positionResult:
            # 価格を入れる配列(value)に価格を入れる
            value.append(i["position_value"])

            # 0以外の場合(ポジションを所持している)
            if i["position_value"] != 0:
                # print("現在のポジション:", i["side"])
                # print(i["side"], i["position_value"])
                # return print("現在のポジション:", i["side"])
                return i["side"]
            # 一周するごとに+1していき、最後の処理になったらvalueの中身を比較して両方とも0(buy == sell)だったらNoneを返す(0 = ポジションがない)
            if count == 1:
                buy = None
                sell = None
                num = 0
                for x in value:
                    if num == 0:
                        buy = x
                    elif num == 1:
                        sell = x
                    num += 1
                if buy == sell:
                    # print("現在ポジションはありません")
                    # return print("現在のポジションはありません")
                    return None
            count += 1
    except:
        return None


def check_order(user, flag):
    # 逆指値のキーがあるか確認する(逆指値の場合のみ設定していない場合は["order_status"]がない)
    def areThereKey(order):
        try:
            if order["result"][0]["order_status"]:
                return True
        except Exception as e:
            print(e)
            return False

    # 取引状況を取得
    position = user.rest.linear.private_position_list(
        symbol=option["symbol"],
    ).json()

    # print(position)
    # 保持している注文(buy, sell)かを取得 / 所持していない未約定の場合は none
    position = position["result"]
    position_side = get_side(position)

    # オーダーを取得（オーダーであって、約定ではない)
    orders = user.rest.linear.private_order_list(
        symbol=option["symbol"]
    ).json()
    # オーダー状況のデータを取得
    # orders = orders["result"]["data"]

    # 逆指値の取引状況を取得
    stopLimitOrders = user.rest.linear.private_stoporder_search(
        symbol=option["symbol"]
    ).json()

    # 保持している注文がある場合
    if position_side is not None:
        # 約定 = ポジションがあるということ だからpositionがNoneの時はポジションがない
        print("注文が約定しました！")
        # オーダーで保持した注文があるため、オーダーがなくなりTrueからFalseに変更
        flag["order"]["exist"] = False
        # オーダー数
        flag["order"]["count"] = 0
        # 保持している注文があるためFalseからTrueに変更
        flag["position"]["exist"] = True
        # 保持している注文のsideにオーダーのsideを入れる
        flag["position"]["side"] = flag["order"]["side"]  # Sell Buy 大文字が返ってくる

        # BOTが起動したときに送信するメッセージ
        discord_content = {
            "content": "<@488361459223494657>",
            "embeds": [
                {
                    "title": f"{position_side} - 約定しました",  # flag['position']['side']
                    "color": 15258703,
                    "fields": [
                        {
                            "name": "Date(JST)",
                            "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                            "inline": False
                        },
                        {
                            "name": "Wallet",
                            "value": f"{get_myWallet('USDT')}$",
                            "inline": False
                        },
                    ],
                }
            ]
        }
        line_content = f"""### {flag["position"]["side"]} - 約定しました
## Date(JST): {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
# Wallet: {get_myWallet('USDT')}$"""
        notification(discord_content, line_content)

    # 保持している注文がない場合
    else:
        # 逆指値のトリガーが設定されているかチェック
        if areThereKey(stopLimitOrders):
            stopLimitOrders = stopLimitOrders["result"]

            print("まだ未実行の逆指値のトリガーがあります")

            # BOTが起動したときに送信するメッセージ
            discord_content = {
                "content": "<@>",
                "embeds": [
                    {
                        "title": f"{flag['position']['side']} - 未実行の逆指値のトリガーがあります",
                        "color": 15258703,
                        "fields": [
                            {
                                "name": "Date(JST)",
                                "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                                "inline": False
                            },
                            {
                                "name": "Wallet",
                                "value": f"{get_myWallet('USDT')}$",
                                "inline": False
                            },
                        ],
                    }
                ]
            }
            line_content = f"""### {flag["position"]["side"]} - 未実行の逆指値のトリガーがあります
## Date(JST): {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
# Wallet: {get_myWallet('USDT')}$"""
            notification(discord_content, line_content)

            # いくつか注文がある場合
            for i in stopLimitOrders:
                if i["order_status"] == "Untriggered":
                    print(i["stop_order_id"])

            flag["order"]["stopLimitOrderCount"] += 1
            print("order", flag["order"]["stopLimitOrderCount"])
            # 1分たったら注文をキャンセルする
            if flag["order"]["stopLimitOrderCount"] > 6:
                flag = cancel_order(stopLimitOrders, flag)

        # order_statusがNew以外場合
        else:
            print("現在有効な注文や逆指値のトリガーはありません")

    return flag  # flag["order"]の["exist"],["count"] / flag["position"]の["exist"],["side"](Buy,Sell)を返す


# オーダーをキャンセル(保持している注文ではない)
def cancel_order(orders, flag, user=bot):
    # 無効のキーを指定するとエラーが発生するため、ここでチェックする
    def areThereKey(check):
        try:
            if check[0]["order_status"] == "Untriggered":
                return True
        except Exception as e:
            print(e)
            return False

    # 逆指値の場合
    if areThereKey(orders):
        for i in orders:
            # BOTが起動したときに送信するメッセージ
            discord_content = {
                "content": "<@>",
                "embeds": [
                    {
                        "title": f"{i['side']} - 逆指値をキャンセルしました",
                        "color": 15258703,
                        "fields": [
                            {
                                "name": "Date(JST)",
                                "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                                "inline": False
                            },
                            {
                                "name": "Wallet",
                                "value": f"{get_myWallet('USDT')}$",
                                "inline": False
                            },
                        ],
                    }
                ]
            }
            line_content = f"""#### {i["side"]} - 逆指値をキャンセルしました
### Date: {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
# Wallet: {get_myWallet('USDT')}$"""
            notification(discord_content, line_content)

            if i["order_status"] == "Untriggered":
                user.rest.linear.private_stoporder_cancel(
                    symbol=option["symbol"],
                    stop_order_id=i["stop_order_id"]
                )
        flag["order"]["stopLimitOrderCount"] = 0

    print("約定していない注文をキャンセルしました")

    # オーダーがキャンセルされてオーダーが存在しないので、TrueからFalseへ
    flag["order"]["exist"] = False

    sleep(20)  # 20秒待機

    # 保持している注文を取得
    position = user.rest.linear.private_position_list(
        symbol=option["symbol"]
    ).json()
    # Buy, Sell どちらかを取得
    try:
        position = position["result"][0]["side"]
    except:
        position = None

    # position is None = False (buy,sell いずれかあるため) | 訳: ポジションがある
    # position is not None = True (buy,sell いずれかあるためFalseになるが、notを使って反転させるためTrue) | 訳: ポジションがない
    # 建玉(建玉) 取引約定後残っている未決済分(保持している注文)
    if position is not None:
        print("現在未決済の建玉はありません")
    else:
        print("現在まだ未決済の建玉があります")
        # 保持している注文があるためTrue
        flag["position"]["exist"] = True
        # Buy, Sell どちらかかを入れる
        flag["position"]["side"] = position
    return flag


def main():
    clear()
    # BOTが起動したときに送信するメッセージ
    discord_content = {
        "content": "<@>",
        "embeds": [
            {
                "title": "Bot has been started!",
                "color": 15258703,
                "fields": [
                    {
                        "name": "Date",
                        "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                        "inline": False
                    },
                    {
                        "name": "Wallet",
                        "value": f"{get_myWallet('USDT')}$",
                        "inline": False
                    },
                ],
            }
        ]
    }
    line_content = f"""───────────────
### BOTが起動しました
## Date: {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
# Wallet: {get_myWallet('USDT')}$"""
    notification(discord_content, line_content)

    # 2分前のデータ
    oldData = get_kline(bot)

    # OHLC表示
    get_ohlc(oldData)

    # 取引状況をここに記入
    flag = {
        "buy_signal": 0,
        "sell_signal": 0,
        "wallet": get_myWallet("USDT"),
        "order": {
            "exist": False,
            "side": "",
            "count": 0,
            "stopLimitOrderCount": 0
        },
        "position": {
            "exist": False,
            "side": ""
        }
    }

    sleep(20)

    while True:
        # BOTが動作しているかチェック
        url = f""
        running = {
            "embeds": [
                {
                    "title": "BOTが動作しています",
                    "color": 0xe74c3c,
                    "fields": [
                        {
                            "name": "Date",
                            "value": f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}",
                            "inline": False
                        },
                    ],
                }
            ]
        }
        postWebhook(running, url)

        try:
            # 注文が存在する場合
            if flag["order"]["exist"]:
                # check_order関数で注文が約定しているか否か判定して、flag配列を返す
                # ここで未約定の注文をキャンセルする処理も行う -> トレンド対策(下がり続けたり、上がり続けたり)
                # return: flag["order"]の["exist"],["count"] / flag["position"]の["exist"],["side"](Buy,Sell)
                flag = check_order(bot, flag)
            # 1分前のデータを取得 / これを最新データとして扱う
            data = get_kline(bot)  # return: ローソク足のデータ
            # 取得したデータと前回のデータの日付の相違がある場合
            if data["open_time"] != oldData["open_time"]:
                # OHLC表示
                get_ohlc(data)
                # 保持している注文がある場合 / ここでcheck_orderで処理した情報が使われる
                if flag["position"]["exist"]:
                    # ここで決済するか否か決定
                    flag = close_position(bot, data, oldData, flag)  # return: flag["position"]["exist"]
                # positionがない場合
                else:
                    # 陽線が3本連続した場合に逆指値を入れる関数
                    # この下二つが実行される
                    # 結局はどちらかの傾向がある方に注文を入れるから二つ実行されても問題はない
                    flag = buy_signal(bot, data, oldData, flag)  # return: flag["order"]の["exist"]と["side"]
                    flag = sell_signal(bot, data, oldData, flag)  # return: flag["order"]の["exist"]と["side"]
                # 前回のデータに今回の日付データを入れる
                oldData["open_time"] = data["open_time"]
                oldData["open"] = data["open"]
                oldData["close"] = data["close"]
            sleep(10)

        except Exception as e:
            discord_content = {
                "content": "<@488361459223494657>",
                "embeds": [
                    {
                        "title": "Error has been occurred!",
                        "color": 15258703,
                        "fields": [
                            {
                                "name": "Date",
                                "value": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                                "inline": False
                            },
                            {
                                "name": "Wallet",
                                "value": f"{get_myWallet('USDT')}$",
                                "inline": False
                            },
                            {
                                "name": "Error",
                                "value": e,
                                "inline": False
                            },
                        ],
                    }
                ]
            }
            line_content = f"""───────────────
#### BOTが起動しました
### Date: {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
## Wallet: {get_myWallet('USDT')}$
## Error: {e}"""
            notification(discord_content, line_content)


main()
