import aiohttp
import asyncio
import shutil
import discord
from datetime import datetime
from os.path import basename
import json

from discord import Message
from aiohttp import ClientResponse
from os import PathLike
from typing import List, Mapping, Union, Optional, Any, Iterable, NoReturn

from .visuals import display_exception


def slice_list(iterable: Iterable[Any], n: int) -> List[List[Any]]:
    return [iterable[i:i + n] for i in range(0, len(iterable), n)]


def define_status(flag: bool) -> str:
    return "Enabled" if flag else "Disabled"


def load_file(file_path: Union[str, PathLike]) -> Union[Any, NoReturn]:
    file_name = basename(file_path)

    try:
        return json.load(open(file_path, "r"))

    except json.JSONDecodeError:
        return display_exception(f"Failed to decode \"{file_name}\"")

    except FileNotFoundError:
        return display_exception(f"File \"{file_name}\" was not found")

    except Exception as err:
        return display_exception(f"Failed to load \"{file_name}\" file: {err}")


def check_for_update() -> None:
    res = requests.get("https://pastefy.app/Y6d1Goby/raw").content

    try:
        version = res.decode().strip().split("VERSION = \"")[1].split("\"")[0]
    except IndexError:
        return

    if version != VERSION:
        return display_exception("New version on github is out\n")


def min_sale_price(price: int) -> int:
    profit = price // 2

    while (price // 2) >= profit:
        price -= 1

    return price + 1


class ItemTypes:
    types = {8: "Hat", 41: "HairAccessory", 42: "FaceAccessory", 43: "NeckAccessory",
             44: "ShoulderAccessory", 45: "FrontAccessory", 46: "BackAccessory",
             47: "WaistAccessory", 64: "TShirtAccessory", 65: "ShirtAccessory",
             66: "PantsAccessory", 67: "JacketAccessory", 68: "SweaterAccessory",
             69: "ShortsAccessory", 72: "DressSkirtAccessory"}

    @classmethod
    def integers(cls) -> List[int]:
        return list(cls.types.keys())

    @classmethod
    def names(cls) -> List[str]:
        return list(cls.types.values())


class Auth:
    def __init__(self, cookie: str) -> None:
        self.cookie = cookie

        self.user_id = None
        self.name = None
        self.username = None
        self.has_premium = None

        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=None),
            trust_env=True,
            cookies={".ROBLOSECURITY": self.cookie}
        )

        asyncio.create_task(self.update_csrf_token())

    async def close_session(self):
        await self.session.close()

    async def update_csrf_token(self, csrf_token: str | None = None) -> None:
        if csrf_token is None:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        "https://economy.roblox.com/",
                        cookies={".ROBLOSECURITY": self.cookie}
                ) as response:
                    csrf_token = response.headers.get("x-csrf-token")

        self.session.headers.update({"x-csrf-token": csrf_token})

    async def update_auth_info(self) -> None:
        async with self.session.get("https://users.roblox.com/v1/users/authenticated") as response:
            data = await response.json()

            if response.status != 200 or data.get("errors") and data["errors"][0].get("code") == 0:
                return None

            self.user_id = data.get("id")
            self.name = data.get("displayName")
            self.username = data.get("name")

            return None

    async def get_premium_owning(self) -> bool:
        if self.user_id is None:
            self.update_auth_info()

        async with self.session.get(f"https://premiumfeatures.roblox.com/v1/users/{self.user_id}/validate-membership") as response:
            self.has_premium = await response.json()
            return self.has_premium


class Collectible:
    def __init__(
            self,
            _id: int,
            name: str,
            thumbnail: str,
            quantity: int,
            price: int,
            lowest_resale_price: int,
            offered_price: int,
            creator_id: int,
            creator_name: str,
            item_id: str,
            *,
            auth: Optional[Auth] = None
    ) -> None:

        self.id = _id
        self.name = name
        self.link = f"https://www.roblox.com/catalog/{self.id}/{'-'.join(self.name.split())}"

        self.creator_id = creator_id
        self.creator_name = creator_name
        self.creator_link = f"https://www.roblox.com/groups/{self.creator_id}/{'-'.join(self.creator_name.split())}"

        self.price = price
        self.lowest_resale_price = lowest_resale_price
        self.price_to_sell = offered_price

        self.thumbnail = thumbnail
        self.quantity = quantity

        self.item_id = item_id

        self._collectibles = []
        self.current_index = 0

        self.auth = auth

    @property
    def collectibles(self):
        return self._collectibles

    @property
    def current(self):
        return self._collectibles[self.current_index]

    def next(self):
        self.current_index = (self.current_index + 1) % len(self._collectibles)

    def add(
            self,
            serial: int,
            on_sale: Optional[bool] = None,
            instance_id: Optional[str] = None,
            product_id: Optional[str] = None,
    ) -> None:
        new_col = {}

        for i, col in enumerate(self._collectibles):
            if col.get("serial") == serial:
                new_col = col
                self._collectibles.pop(i)
                break

        if new_col.get("serial") is None:
            new_col["serial"] = serial
        if new_col.get("on_sale") is None and product_id is not None:
            new_col["on_sale"] = on_sale
        if new_col.get("instance_id") is None and instance_id is not None:
            new_col["instance_id"] = instance_id
        if new_col.get("product_id") is None and product_id is not None:
            new_col["product_id"] = product_id

        self._collectibles.append(new_col)

    async def sell(self, price: Optional[int] = None) -> Union[ClientResponse.status, None]:
        if self.auth is None:
            return None
        if self.current.get("product_id") is None or self.current.get("instance_id") is None:
            await self.fetch_collectibles()

        payload = {
            "collectibleProductId": self.current["product_id"],
            "isOnSale": True,
            "price": self.price_to_sell if price is None else price,
            "sellerId": self.auth.user_id,
            "sellerType": "User"
        }

        async with self.auth.session.patch(
                f"https://apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/instance/{self.current['instance_id']}/resale",
                json=payload,
                ssl=False
        ) as response:
            return response.status

    async def take_off_sale(self) -> Union[ClientResponse.status, None]:
        if self.auth is None:
            return None

        payload = {
            "collectibleProductId": self.current["product_id"],
            "isOnSale": False,
            "price": price,
            "sellerId": self.auth.user_id,
            "sellerType": "User"
        }

        async with self.auth.session.patch(
                f"https://apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/instance/{self.current['instance_id']}/resale",
                json=payload,
                ssl=False
        ) as response:
            return response.status

    async def get_resales(self) -> Union[List[Mapping[str, Union[str, int, dict]]], ClientResponse.status, None]:
        if self.auth is None:
            return None

        async with self.auth.session.get(
                f"https://apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/resellers?limit=999999999",
                ssl=False
        ) as response:
            if response.status != 200:
                return response.status

            return await response.json()

    async def fetch_collectibles(self) -> None:
        if self.auth is None: #  or [col for col in self._collectibles if None in [col.get("serial"), col.get("on_sale"), co.get("instance_id"), col.get("product_id")]]:
            return None

        cursor = ""

        while True:
            async with self.auth.session.get(
                    f"https://apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/resellable-instances?"
                    f"cursor={cursor}&ownerType=User&ownerId={self.auth.user_id}&limit=999999999"
            ) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                for instance in data["itemInstances"]:
                    self.add(
                        instance["serialNumber"],
                        True if instance["saleState"] == "OnSale" else False,
                        instance["collectibleInstanceId"],
                        instance["collectibleProductId"],
                    )

                cursor = data["nextPageCursor"]

                if cursor is None:
                    return None

    def make_embed(self, seller: Optional[object] = None) -> discord.Embed:
        embed = discord.Embed(title=self.name,
                              url=self.link,
                              timestamp=datetime.now(),
                              color=2469096,
                              description=f"Sell this item for `{self.price_to_sell:,}` robux")

        embed.add_field(name=f"Price", value=f"`{self.price:,}`", inline=True)
        embed.add_field(name=f"Lowest Resale Price", value=f"`{self.lowest_resale_price:,}`", inline=True)
        embed.add_field(name=f"Quantity", value=f"`{self.quantity:,}`", inline=True)

        embed.set_author(name=self.creator_name, url=self.creator_link)
        embed.set_thumbnail(url=self.thumbnail)

        if seller is not None:
            embed.set_footer(text=f"Viewing {seller.current_index}/{len(seller)}")

        return embed

    def __len__(self):
        return len(self._collectibles)

    def __str__(self):
        return str(self.id)

    __repr__ = __str__
