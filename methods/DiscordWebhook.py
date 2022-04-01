import json
from rich import print
import requests

WEBHOOK = f""


def postWebhook(content, url=WEBHOOK):
    """EXAMPLE = {
        "content": "<@>",
        "embeds": [
            {
                "title": "Bot has been started!",
                "color": 15258703,
                "fields": [
                    {
                        "name": "Date",
                        "value": "{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}",
                        "inline": False
                    },
                    {
                        "name": "Wallet",
                        "value": "{get_myWallet('USDT')}$",
                        "inline": False
                    },
                ],
            }
        ]
    }"""

    requests.post(url, json.dumps(content), headers={'Content-Type': 'application/json'})