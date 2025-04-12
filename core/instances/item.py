import asyncio
from datetime import datetime

from typing import Optional, List, Any, Union

from ..clients import Auth
from ..utils import IgnoreNew
from ..visuals import Display
from .collectible import Collectible

__all__ = ("Item",)


class Item:
    __slots__ = ("_id", "item_id", "_link", "name", "thumbnail",
                 "price", "quantity", "lowest_resale_price",
                 "_creator_id", "creator_name", "_creator_link",
                 "recent_average_price", "has_resales", "latest_sale",
                 "has_sales", "price_to_sell", "auth", "_collectibles",
                 "resales", "sales")

    def __init__(
        self,
        item_info: dict,
        item_details: dict,
        *,
        thumbnail: Optional[str] = None,
        price_to_sell: Optional[int] = None,
        auth: Optional[Auth] = None
    ) -> None:
        self._id = item_info["assetId"]
        self.item_id = item_info["collectibleItemId"]
        self._link = f"https://www.roblox.com/catalog/{self._id}"
        self.name = item_info["assetName"]
        self.thumbnail = thumbnail
        self.price = item_details.get("price")
        self.quantity = item_details.get("totalQuantity")
        self.lowest_resale_price = item_details["lowestResalePrice"]

        self._creator_id = item_details.get("creatorTargetId")
        self.creator_name = item_details.get("creatorName")
        self._creator_link = f"https://www.roblox.com/groups/{self._creator_id}"

        self.recent_average_price = None
        self.has_resales = None
        self.latest_sale = None
        self.has_sales = None

        self.price_to_sell = price_to_sell
        self.auth = auth

        self._collectibles = {}
        self.resales = []
        self.sales = []

    id = IgnoreNew()
    link = IgnoreNew()

    creator_id = IgnoreNew()
    creator_link = IgnoreNew()

    @property
    def collectibles(self) -> List[Collectible]:
        return list(self._collectibles.values())

    def get_collectible(self, serial: int, default: Optional[Any] = None) -> Union[Collectible, Any]:
        return self._collectibles.get(serial, default)

    def remove_collectible(self, serial: int) -> None:
        return self._collectibles.pop(serial)

    @staticmethod
    def __define_status(value: str, state: str, name: str):
        def decorator(_):
            def wrapper(instance: "Item") -> str:
                match getattr(instance, state):
                    case True:
                        return f"{getattr(instance, value):,}"
                    case False:
                        return f"No {name.capitalize()}"
                    case _:
                        return "Failed to Fetch"

            return wrapper
        return decorator

    @__define_status("lowest_resale_price", "has_resales", "resales")
    def define_lowest_resale_price(self, state) -> str: ...

    @__define_status("recent_average_price", "has_sales", "sales")
    def define_recent_average_price(self) -> str: ...

    @__define_status("latest_sale", "has_sales", "sales")
    def define_latest_sale(self) -> str: ...

    def add_collectible(
        self,
        serial: Optional[int] = None,
        on_sale: Optional[bool] = None,
        sale_price: Optional[int] = None,
        item_id: Optional[int] = None,
        instance_id: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> None:
        col = self.get_collectible(serial)

        if not col and serial is not None:
            new = Collectible(
                serial=serial,
                on_sale=on_sale,
                sale_price=sale_price,
                item_id=(item_id or self.item_id),
                instance_id=instance_id,
                product_id=product_id
            )
            self._collectibles.update({serial: new})
        elif col:
            col.set_values(
                on_sale=on_sale,
                sale_price=sale_price,
                item_id=(item_id or self.item_id),
                instance_id=instance_id,
                product_id=product_id
            )

    @Auth.has_auth
    async def sell_collectibles(
        self,
        price: Optional[int] = None,
        skip_on_sale: Optional[bool] = False,
        skip_if_cheapest: Optional[bool] = False,
        log: Optional[bool] = True,
        retries: Optional[int] = 3
    ) -> Optional[int]:
        await self.fetch_collectibles()

        sold_amount = 0
        price_to_sell = (price or self.price_to_sell)

        for col in self.collectibles:
            tries = 0

            if col.skip_on_sale:
                continue

            elif col.sale_price == price_to_sell:
                if log: Display.skipping(f"This collectible is already on sale for the same price [g(#{col.serial})]")
                continue

            elif col.on_sale:
                if skip_on_sale:
                    if log: Display.skipping(f"This collectible is already on sale [g(#{col.serial})]")
                    continue

                elif skip_if_cheapest and self.lowest_resale_price == col.sale_price:
                    if log: Display.skipping(f"You are already selling this collectible for the cheapest price [g(#{col.serial})]")
                    continue

            while True:
                status = await col.sell(price_to_sell, self.auth)

                match status:
                    case 200:
                        if log: Display.success(f"Successfully sold for $[g{price_to_sell} (#{col.serial})]")

                        sold_amount += 1
                        break
                    case 429:
                        if log: Display.error("You got rate limited! Trying again in 30 seconds...")
                        tries += 1
                        await asyncio.sleep(30)
                    case 403 | 412:
                        if log: Display.skipping("Item is not resable. Skipping it")
                        return None
                    case None:
                        break
                    case _:
                        if log: Display.error(f"Failed to sell limited ({status})")

                        tries += 1
                        await asyncio.sleep(3)

                if tries > retries:
                    break

        return sold_amount

    @Auth.has_auth
    async def fetch_sales(self, *,
                          save_sales: Optional[bool] = True,
                          save_rap: Optional[bool] = True,
                          save_latest_sale: Optional[bool] = True) -> None:
        async with self.auth.get(
                f"apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/resale-data"
        ) as response:
            if response.status != 200:
                return None

            data = await response.json()

            if save_sales:
                for price, amount in zip(data["priceDataPoints"], data["volumeDataPoints"]):
                    data = {
                        "price": price["value"],
                        "amount": amount["value"],
                        "date": datetime.strptime(price["date"], "%Y-%m-%dT%H:%M:%SZ")
                    }
                    self.sales.append(data)

            if save_rap:
                self.recent_average_price = round(data.get("recentAveragePrice", 0))

            if save_latest_sale:
                if data["priceDataPoints"] and data["priceDataPoints"][0]["value"]:
                    self.latest_sale = data["priceDataPoints"][0]["value"]
                    self.has_sales = True
                else:
                    self.has_sales = False

    @Auth.has_auth
    async def fetch_resales(self, *,
                            save_resales: Optional[bool] = True,
                            save_lrp: Optional[bool] = True) -> None:
        async with self.auth.get(f"apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/resellers?limit=99") as response:
            try:
                data = (await response.json()).get("data")
            except:
                return None

            if data is None:
                return None

            if save_resales:
                for resale in data:
                    seller = resale["seller"]

                    data = {
                        "lowest_resale_price": resale["price"],
                        "serial": resale["serialNumber"],
                        "seller_id": seller["sellerId"],
                        "seller_name": seller["name"]
                    }
                    self.resales.append(data)

            if save_lrp:
                if data:
                    self.lowest_resale_price = data[0]["price"]
                    self.has_resales = True
                else:
                    self.has_resales = False

    @Auth.has_auth
    async def fetch_collectibles(self) -> None:
        cursor = ""

        while True:
            async with self.auth.get(
                    f"apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/resellable-instances?"
                    f"cursor={cursor}&ownerType=User&ownerId={self.auth.user_id}&limit=9999999"
            ) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                serials_list = []

                for instance in data.get("itemInstances"):
                    col_serial = instance["serialNumber"]

                    self.add_collectible(
                        serial=col_serial,
                        on_sale=(True if instance["saleState"] == "OnSale" else False),
                        sale_price=instance.get("price"),
                        item_id=instance["collectibleItemId"],
                        instance_id=instance["collectibleInstanceId"],
                        product_id=instance["collectibleProductId"]
                    )
                    serials_list.append(col_serial)

                for serial in list(self._collectibles):
                    if serial not in serials_list:
                        self.remove_collectible(serial)

                cursor = data.get("nextPageCursor")

                if cursor == data.get("previousPageCursor"):
                    return None

    def __len__(self) -> int:
        return len(self.collectibles)
