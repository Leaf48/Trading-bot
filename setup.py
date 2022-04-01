import os
import platform

modules = ["git+https://github.com/MtkN1/pybybit.git", "bybit", "line-bot-sdk", "rich", "discord.py"]


def get_platform():
    p = platform.system()
    print(p)
    return p


def clear(p):
    if p == "Windows":
        return os.system("cls")
    elif p == "Linux":
        return os.system("clear")


for i in modules:
    os.system(f"pip install {i}")

clear(get_platform())
