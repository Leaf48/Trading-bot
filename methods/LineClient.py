from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
from rich import print


class LineClient:
    def __init__(self, secret):
        self.secret = secret
        self.linebot = LineBotApi(self.secret)

    def push(self, message):
        try:
            print(self.linebot.get_bot_info())
            self.linebot.push_message('', TextSendMessage(text=message))

        except LineBotApiError as e:
            pass