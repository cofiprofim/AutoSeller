from discord import Embed
from datetime import datetime


def exception_embed(exc: str):
    embed = Embed(title="An error occurred:",
                  description=f"```py\n{exc}```",
                  color=16711680)

    return embed


def custom_embed(title: str, description: str) -> Embed:
    embed = Embed(title=title,
                  description=description,
                  color=2469096,
                  timestamp=datetime.now())

    return embed
