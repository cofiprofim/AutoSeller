import aiohttp
import asyncio
from datetime import datetime
from os.path import basename
from rgbprint import Color
import json

from os import PathLike
from typing import (
    List,
    Union,
    Optional,
    Any,
    Iterable,
    NoReturn,
    Literal,
    Callable
)

from .visuals import Display, GRAY_COLOR


def slice_list(iterable: Iterable[Any], n: int) -> List[List[Any]]:
    return [iterable[i:i + n] for i in range(0, len(iterable), n)]


def define_status(flag: bool) -> str:
    return "Enabled" if flag else "Disabled"


def load_file(file_path: Union[str, PathLike]) -> Union[Any, NoReturn]:
    try:
        return json.load(open(file_path, "r"))

    except json.JSONDecodeError:
        file_name = basename(file_path)
        return Display.exception(f"Failed to decode \"{file_name}\"")

    except FileNotFoundError:
        file_name = basename(file_path)
        return Display.exception(f"File \"{file_name}\" was not found")

    except Exception as err:
        file_name = basename(file_path)
        return Display.exception(f"Failed to load \"{file_name}\" file: {err}")


def min_sale_price(price: int) -> int:
    profit = price // 2

    while (price // 2) >= profit:
        price -= 1

    return price + 1


async def is_webhook_exists(webhook_url: str) -> bool:
    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        return False
    
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(webhook_url, ssl=False) as response:
            return True if (await response.json()).get("name") is not None else False

# Wanted to add this but too complicated

# class TasksManager:
#     success_emoji = "✅"
#     error_emoji = "❌"
#     skip_emoji = "⚫️"
    
#     def __init__(
#         self,
#         char_limit: Optional[int] = 4096,
#         success_emoji: Optional[str] = None,
#         error_emoji: Optional[str] = None
#     ) -> None:
#         self.char_limit = char_limit
#         self._tasks = ""
       
#         if success_emoji is not None:
#             self.success_emoji = success_emoji
#         if error_emoji is not None:
#             self.error_emoji = error_emoji
    
#     def check_tasks(func: callable):
#         def wrapper(self, *args, **kwargs):
#             if len(self.tasks) >= self.char_limit:
#                 self.tasks = ""
            
#             func(self, *args, **kwargs)
#         return wrapper
    
#     @check_tasks
#     def add_new(self, text: str, emoji_type: Literal["success", "error", "skip"]) -> None:
#         if emoji_type == "success":
#             self._tasks = self._tasks + f"{self.success_emoji} {text}\n"
#         elif emoji_type == "error":
#             self._tasks = self._tasks + f"{self.error_emoji} {text}\n"
#         elif emoji_type == "skip":
#             self._tasks = self._tasks + f"{self.skip_emoji} {text}\n"
    
#     @check_tasks
#     def add_success(self, text: str) -> None:
#         self._tasks = self._tasks + f"{self.success_emoji} {text}\n"
    
#     @check_tasks
#     def add_error(self, text: str) -> None:
#         self._tasks = self._tasks + f"{self.error_emoji} {text}\n"
    
#     @check_tasks
#     def add_skip(self, text: str) -> None:
#         self._tasks = self._tasks + f"{self.skip_emoji} {text}\n"
    
#     @property
#     def tasks(self) -> str:
#         return self._tasks
    
#     @classmethod
#     def set_success(cls, new: str) -> None:
#         cls.success_emoji = new
    
#     @classmethod
#     def set_error(cls, new: str) -> None:
#         cls.error_emoji = new
    
#     @classmethod
#     def set_skip(cls, new: str) -> None:
#         cls.skip_emoji = new
    
#     def __len__(self) -> int:
#         return len(self._tasks)
    
#     def __str__(self) -> str:
#         return self._tasks.strip()
    
#     __repr__ = __str__

class FileSync(set):
    def __init__(self, filename: Union[str, PathLike]) -> None:
        self.filename = filename
        
        items = load_file(filename)
        if not isinstance(items, list):
            return Display.exception("Invalid format type of file provided")
        
        self.update(items)
        
        self.add = self.__write_file(self.add)
        self.remove = self.__write_file(self.remove)
        self.clear = self.__write_file(self.clear)
    
    def __write_file(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            
            with open(self.filename, "w") as f:
                json.dump(list(self), f)
        
        return wrapper

class WithBool:
    def __init__(self) -> None:
        self.__bool = False
    
    def __enter__(self):
        self.__bool = True
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__bool = False
    
    def __bool__(self) -> bool:
        return self.__bool
    
    def __repr__(self) -> str:
        return str(self.__bool)
    
    @property
    def flag(self) -> bool:
        return self.__bool


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
            connector=aiohttp.TCPConnector(limit=None, ssl=False),
            trust_env=True,
            cookies={".ROBLOSECURITY": self.cookie}
        )

    async def close_session(self):
        await self.session.close()

    async def update_csrf_token(self, csrf_token: Union[str, None] = None) -> None:
        if csrf_token is None:
            self.session.headers.pop("x-csrf-token", None)
            
            async with self.session.post(
                "https://auth.roblox.com/v1/login",
                ssl=False
            ) as response:
                csrf_token = response.headers.get("x-csrf-token")
                
                if csrf_token is None:
                    Display.exception("Failed to get csrf token")

        self.session.headers.update({"x-csrf-token": csrf_token})
        # print(self.session.headers)

    async def update_auth_info(self) -> None:
        async with self.session.get(
            "https://users.roblox.com/v1/users/authenticated",
            ssl=False
        ) as response:
            
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

        if self.user_id is None:
            return None

        async with self.session.get(
                f"https://premiumfeatures.roblox.com/v1/users/{self.user_id}/validate-membership",
                ssl=False
        ) as response:
            
            self.has_premium = await response.json()
            return self.has_premium


class Collectible:
    def __init__(
            self,
            serial: int,
            on_sale: Optional[bool] = None,
            sale_price: Optional[int] = None,
            item_id: Optional[int] = None,
            instance_id: Optional[str] = None,
            product_id: Optional[str] = None,
            skip_on_sale: Optional[bool] = None,
            *,
            auth: Optional[Auth] = None
    ) -> None:

        self._serial = serial
        self._on_sale = on_sale
        self._sale_price = sale_price
        self._item_id = item_id
        self._instance_id = instance_id
        self._product_id = product_id
        
        self.skip_on_sale = skip_on_sale

        self.auth = auth

    @property
    def serial(self):
        return self._serial

    @property
    def on_sale(self):
        return self._on_sale
    
    @property
    def sale_price(self):
        return self._sale_price

    @on_sale.setter
    def on_sale(self, new):
        if self._on_sale is None:
            self._on_sale = new

    @property
    def sale_price(self):
        return self._sale_price

    @sale_price.setter
    def sale_price(self, new):
        if self._sale_price is None:
            self._sale_price = new

    @property
    def item_id(self):
        return self._item_id

    @item_id.setter
    def item_id(self, new):
        if self._item_id is None:
            self._item_id = new

    @property
    def instance_id(self):
        return self._instance_id

    @instance_id.setter
    def instance_id(self, new):
        if self._instance_id is None:
            self._instance_id = new

    @property
    def product_id(self):
        return self._product_id

    @product_id.setter
    def product_id(self, new):
        if self._product_id is None:
            self._product_id = new

    def set_values(
            self,
            on_sale: Optional[bool] = None,
            sale_price: Optional[int] = None,
            item_id: Optional[int] = None,
            instance_id: Optional[str] = None,
            product_id: Optional[str] = None,
            skip_on_sale: Optional[str] = None
    ) -> None:
        self.on_sale = on_sale
        self.sale_price = sale_price
        self.item_id = item_id
        self.product_id = product_id
        self.instance_id = instance_id
        
        self.skip_on_sale = skip_on_sale

    async def sell(self, price: int) -> Union[int, None]:
        if None in [self.auth, self.item_id, self.instance_id, self.product_id] or self.skip_on_sale:
            return None

        payload = {
            "collectibleProductId": self.product_id,
            "isOnSale": True,
            "price": price,
            "sellerId": self.auth.user_id,
            "sellerType": "User"
        }

        async with self.auth.session.patch(
                f"https://apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/instance/{self.instance_id}/resale",
                json=payload,
                ssl=False
        ) as response:
            if response.status == 200:
                self.on_sale = True
            
            return response.status

    async def take_off_sale(self) -> Union[int, None]:
        if None in [self.auth, self.item_id, self.instance_id, self.product_id]:
            return None

        payload = {
            "collectibleProductId": self.current["product_id"],
            "isOnSale": False,
            "sellerId": self.auth.user_id,
            "sellerType": "User"
        }

        async with self.auth.session.patch(
                f"https://apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/instance/{self.current['instance_id']}/resale",
                json=payload,
                ssl=False
        ) as response:
            if response.status == 200:
                self.on_sale = False
            
            return response.status


class Item:
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
            creator_type: Literal["Group", "User"],
            item_id: Optional[str] = None,
            *,
            auth: Optional[Auth] = None
    ) -> None:

        self._id = _id
        self.name = name
        self.__link = f"https://www.roblox.com/catalog/{self._id}"

        self.price = price
        self.thumbnail = thumbnail
        self.quantity = quantity
        self.item_id = item_id

        self._creator_id = creator_id
        self.creator_name = creator_name
        self._creator_type = creator_type
        self.__creator_link = f"https://www.roblox.com/groups/{self._creator_id}"

        self.price_to_sell = offered_price
        self.lowest_resale_price = lowest_resale_price

        self.recent_average_price = None
        self.has_resales = None
        
        self.latest_sale = None
        self.has_sales = None

        self._collectibles = {}
        self.resales = []
        self.sales = []

        self.auth = auth

    @property
    def id(self):
        return self._id
    
    @property
    def link(self):
        return self.__link

    @property
    def creator_id(self):
        return self._creator_id

    @creator_id.setter
    def creator_id(self, new: int):
        self._creator_id = new
        self.creator_type = self._creator_type

    @property
    def creator_type(self):
        return self._creator_type

    @creator_type.setter
    def creator_type(self, new: Literal["Group", "User"]):
        self._creator_type = new
        self.__creator_link = "https://www.roblox.com/" + (f"groups/{self._creator_id}" if self._creator_type == "Group" else f"users/{self._creator_id}/profile")

    @property
    def creator_link(self):
        return self.__creator_link
    
    @property
    def collectibles(self) -> List[Collectible]:
        return self._collectibles.values()
    
    def get_collectible(self, serial: int, default: Optional[Any] = None) -> Union[Collectible, None]:
        return self._collectibles.get(serial, default)
    
    def remove_collectible(self, serial: int) -> None:
        self._collectibles.pop(serial)

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

        if col is None and serial is not None:
            new = Collectible(
                serial=serial,
                on_sale=on_sale,
                sale_price=sale_price,
                item_id=(item_id or self.item_id),
                instance_id=instance_id,
                product_id=product_id,
                auth=self.auth
            )
            self._collectibles.update({serial: new})
        elif col is not None:
            col.set_values(
                on_sale=on_sale,
                sale_price=sale_price,
                item_id=(item_id or self.item_id),
                instance_id=instance_id,
                product_id=product_id
            )

    async def sell_collectibles(
            self,
            price: Optional[int] = None,
            skip_on_sale: Optional[bool] = False,
            skip_if_cheapest: Optional[bool] = False,
            log: Optional[bool] = True,
            retries: Optional[int] = 3
    ) -> Union[int, None]:
        
        if [col for col in self._collectibles.values() if (col.auth, col.item_id, col.instance_id, col.product_id)]:
            await self.fetch_collectibles()

        sold_amount = 0
        price_to_sell = (price or self.price_to_sell)

        for col in self._collectibles.values():
            tries = 0
            
            if col.sale_price == price_to_sell:
                if log: Display.skipping(f"This collectible is already on sale for the same price {GRAY_COLOR}(#{col.serial}){Color.white}")
                continue
            elif col.on_sale:
                if log and skip_on_sale and col.on_sale:
                    Display.skipping(f"This collectible is already on sale {GRAY_COLOR}(#{col.serial}){Color.white}")
                elif log and skip_if_cheapest and self.lowest_resale_price == col.sale_price:
                    Display.skipping(f"You are already selling this collectible for the cheapest price {GRAY_COLOR}(#{col.serial}){Color.white}")
                
                continue
            
            while True:
                status = await col.sell(price_to_sell)

                match status:
                    case 200:
                        if log: Display.success(f"Successfully sold for ${GRAY_COLOR}{price_to_sell} "
                                                f"(#{col.serial}){Color(255, 255, 255)}")

                        sold_amount += 1
                        break
                    case 429:
                        if log: Display.error("You got ratelimited! Trying again in 30 seconds...")

                        tries += 1
                        await asyncio.sleep(30)
                    case 403:
                        if log: Display.error("Your token got updated. Getting a new one...")
                        await self.auth.update_csrf_token()
                    case 412:
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

    async def fetch_sales(self,
                          save_sales: Optional[bool] = True,
                          save_rap: Optional[bool] = True,
                          save_latest_sale: Optional[bool] = True) -> None:

        if None in [self.auth, self.item_id] or (self.resales and None not in (self.recent_average_price, self.latest_sale)):
            return None

        async with self.auth.session.get(
                f"https://apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/resale-data",
                ssl=False
        ) as response:
            if response.status != 200:
                return None

            data = await response.json()

            if save_sales and not self.sales:
                for price, amount in zip(data["priceDataPoints"], data["volumeDataPoints"]):

                    data = {
                        "price": price["value"],
                        "amount": amount["value"],
                        "date": datetime.strptime(price["date"], "%Y-%m-%dT%H:%M:%SZ")
                    }
                    self.sales.append(data)

            if save_rap and self.recent_average_price is None:
                self.recent_average_price = round(data.get("recentAveragePrice", 0))

            if save_latest_sale and self.latest_sale is None:
                if data["priceDataPoints"] and data["priceDataPoints"][0]["value"] != 0:
                    self.latest_sale = data["priceDataPoints"][0]["value"]
                    self.has_sales = True
                else:
                    self.has_sales = False

    async def fetch_resales(self,
                            save_resales: Optional[bool] = True,
                            save_lrp: Optional[bool] = True,
                            *,
                            limit: Optional[int] = 99) -> None:

        if self.auth is None or (self.resales and self.lowest_resale_price is None):
            return None
        
        async with self.auth.session.get(
                f"https://apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/resellers?limit={limit}",
                ssl=False
        ) as response:
            try:
                data = (await response.json()).get("data")
            except:
                return None

            if data is None:
                return None
            
            if save_resales and not self.resales:
                for resale in data:
                    seller = resale["seller"]

                    data = {
                        "lowest_resale_price": resale["price"],
                        "serial": resale["serialNumber"],
                        "seller_id": seller["sellerId"],
                        "seller_name": seller["name"]
                    }
                    self.resales.append(data)

            if save_lrp and self.lowest_resale_price is not None:
                if data:
                    self.lowest_resale_price = data[0]["price"]
                    self.has_resales = True
                else:
                    self.has_resales = False

    async def fetch_collectibles(self) -> None:
        if self.auth is None:
            return None

        cursor = ""
        
        while True:
            async with self.auth.session.get(
                    f"https://apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/resellable-instances?"
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
