from discord import Embed
from datetime import datetime

from typing import Optional


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


def loading_embed(title: str, description: Optional[str] = None) -> Embed:
    embed = Embed(description=description,
                  timestamp=datetime.now(),
                  color=2469096)

    embed.set_author(name=title,
                     icon_url="https://cdn.discordapp.com/emojis/1241417265778262086.gif?"
                              "size=48&quality=lossless&name=Loading")

    return embed
