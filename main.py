import sys
import os

VERSION = "1.0.2"

try:
    import asyncio
    import json
    from tqdm import tqdm
    from datetime import datetime
    import aiohttp
    from collections import deque
    from rgbprint import Color
    from discord.errors import LoginFailure

    from os import PathLike
    from aiohttp import ClientResponse
    from typing import List, Iterable, Dict, Union, NoReturn, Any

    from core.utils import *
    from core.visuals import *
    from discord_bot import start as discord_bot_start

    os.system("cls" if os.name == "nt" else "clear")
except ModuleNotFoundError:
    install = input("Uninstalled modules found, do you want to install them? Y/n: ").lower() == "y"

    if install:
        print("Installing modules now...")
        os.system("pip install aiohttp tqdm rgbprint discord.py")
        print("Successfully installed required modules.")
    else:
        print("Aborting installing modules.")

    input("Press \"enter\" to exit...")
    sys.exit(1)


class AutoSeller:
    FAILED_IMAGE_URL = "https://t4.rbxcdn.com/7189017466763a9ed8874824aceba073"

    def __init__(self, config: dict, blacklist: list, seen: list) -> None:
        self.config = config

        self.blacklist = set(blacklist)
        self.seen = set(seen)

        self.discord_bot = config["Discord_Bot"]
        self.owners_list = self.discord_bot.get("Owner_IDs", [])

        webhooks = config["Webhook"]
        self.user_to_ping = f"<@{webhooks['User_To_Ping']}>" if webhooks.get("User_To_Ping", 0) else ""

        buy_webhook = webhooks["On_Buy"]
        self.buy_webhook_url = buy_webhook.get("Url", "").strip()
        self.buy_webhook_enabled = buy_webhook.get("Enabled", False)

        sale_webhook = webhooks["On_Sale"]
        self.sale_webhook_url = sale_webhook.get("Url", "").strip()
        self.sale_webhook_enabled = sale_webhook.get("Enabled", False)

        under_cut = config["Under_Cut"]
        self.under_cut_type = under_cut.get("type", "percent")
        self.under_cut_amount = under_cut.get("Value", 10)

        auto_sell = config["Auto_Sell"]
        self.auto_sell_enabled = not auto_sell.get("Ask_Before_Sell", False)
        self.keep_serials = auto_sell.get("Keep_Serials", 0)
        self.keep_copy = auto_sell.get("Keep_Copy", 0)

        hide_on_sale = auto_sell["Hide_OnSale"]
        self.hide_on_sale = hide_on_sale.get("Enabled", False)
        self.save_items = (hide_on_sale.get("Save_Items", False) and self.hide_on_sale)

        self.total_sold = 0

        self.assets = []
        self.current_index = 0
        self.done = False

        self.auth = Auth(config.get("Cookie", ""))

    async def start(self):
        display_info("Checking cookie to be valid")
        await self.auth.update_auth_info()

        if self.auth.user_id is None:
            return display_exception("Invalid cookie provided")
        elif self.buy_webhook_enabled and not self.buy_webhook_url.startswith("https://discord.com/api/webhooks/"):
            return display_exception("Invalid on buy webhook url provided")
        elif self.sale_webhook_enabled and not self.sale_webhook_url.startswith("https://discord.com/api/webhooks/"):
            return display_exception("Invalid on sale webhook url provided")
        elif self.under_cut_type not in ["robux", "percent"]:
            return display_exception("Invalid under cut type provided, must be \"robux\" or \"percent\"")
        elif self.under_cut_amount < 0:
            return display_exception("Under cut amount can not be less than 0")

        display_info("Getting current limiteds cap")
        items_cap = await self._get_current_cap()

        display_info("Loading your inventory")
        assets = sum(await asyncio.gather(*(self._get_user_collectibles(item_type) for item_type in ItemTypes.integers())),
                     [])

        if not assets:
            return display_exception("You dont have any items")

        asset_ids = [str(asset["assetId"]) for asset in assets]

        display_info("Loading assets thumbnails")
        thumbnails = sum(
            await asyncio.gather(*(self._get_assets_thumbnails(chunk) for chunk in slice_list(asset_ids, 100))), [])

        display_info(f"Found {len(assets)} items. Checking them...")
        assets_details = []

        for chunk in slice_list(asset_ids, 120):
            assets_details.extend(await self._get_assets_details(chunk))

        ignored_items = list(self.seen | self.blacklist)

        for asset, asset_detail, thumbnail in zip(assets, assets_details, thumbnails):
            asset_id = asset["assetId"]
            asset_serial = asset["serialNumber"]
            asset_lrp = asset_detail["lowestResalePrice"]

            if (asset_id in ignored_items or
               (self.keep_serials != 0 and self.keep_serials <= asset_serial) or
               asset_lrp == 0):

                continue

            if str(asset_id) not in self.assets:
                asset_cap = items_cap[ItemTypes.types[asset_detail["assetType"]]]["priceFloor"]
                sell_price = min_sale_price((asset_lrp - self.under_cut_amount) if self.under_cut_type == "robux" else round(asset_lrp - (asset_lrp / 100 * self.under_cut_amount))) if asset_lrp > asset_cap else asset_cap

                col = Collectible(
                    asset["assetId"],
                    asset["assetName"],
                    thumbnail,
                    asset_detail.get("totalQuantity"),
                    asset_detail.get("price"),
                    asset_lrp,
                    sell_price,
                    asset_detail.get("creatorTargetId"),
                    asset_detail.get("creatorName"),
                    asset.get("collectibleItemId"),
                    auth=self.auth
                )

                col.add(
                    asset_serial,
                    asset["collectibleItemInstanceId"]
                )

                self.assets.append(col)
            else:
                self.assets[self.assets.index(str(asset_id))].add(
                    asset_serial,
                    asset["collectibleItemInstanceId"]
                )

        clear_console()

        tasks = [
            asyncio.create_task(discord_bot_start(self)) if self.discord_bot.get("Enabled", False) else None,
            asyncio.create_task(self.start_buy_checking()) if self.buy_webhook_enabled else None,
            asyncio.create_task(self.start_selling())
        ]
        await asyncio.gather(*filter(None, tasks))

    def next_asset(self):
        if (self.current_index + 1) < len(self.assets):
            self.current_index += 1
        else:
            self.current_index = 0
            self.done = True

    @property
    def current_asset(self):
        return self.assets[self.current_index]

    async def start_selling(self):
        if self.auto_sell_enabled:
            while not self.done:
                display_selling(
                    f"Selling {GRAY_COLOR}{len(self.current_asset.collectibles)}x{Color.white} of {GRAY_COLOR}{self.current_asset.name}{Color.white} items...")

                await self.current_asset.fetch_collectibles()

                for _ in self.current_asset.collectibles:
                    while True:
                        status = await self.current_asset.sell()

                        if status == 200:
                            display_success(
                                f"Success sold for {GRAY_COLOR}{self.current_asset.price_to_sell} "
                                f"(#{self.current_asset.current['serial']}){Color(255, 255, 255)} for "
                                f"{GRAY_COLOR}${self.current_asset.price_to_sell}{Color.white}")

                            self.total_sold += 1
                            self.current_asset.next()
                            break
                        elif status == 429:
                            display_error("You got ratelimited! Trying again in 30 seconds...")
                            await asyncio.sleep(30)
                        elif status == 403:
                            display_error("Your token got updated. Getting a new one...")
                            await self.auth.update_csrf_token()
                        elif status == 412:
                            continue
                        else:
                            display_error(f"Failed to sell limited ({status})")
                            self.current_asset.next()
                            break

                if self.sale_webhook_enabled:
                    asyncio.create_task(self.send_sale_webhook(self.current_asset))

                if self.save_items:
                    self.seen.add(self.current_asset.id)
                    with open("items/seen.json", "w") as f: f.write(json.dumps(list(self.seen)))

                self.next_asset()

                await asyncio.sleep(0.5)
        else:
            while not self.done:
                choose = await self.update_console()
    
                if choose == "1":
                    display_selling(f"Selling {GRAY_COLOR}{len(self.current_asset.collectibles)}x{Color.white} items...")
    
                    await self.current_asset.fetch_collectibles()
    
                    for _ in self.current_asset.collectibles:
                        while True:
                            status = await self.current_asset.sell()
    
                            if status == 200:
                                display_success(f"Success sold for {GRAY_COLOR}{self.current_asset.price_to_sell} "
                                                f"(#{self.current_asset.current['serial']}){Color(255, 255, 255)}")
    
                                self.total_sold += 1
                                self.current_asset.next()
                                break
                            elif status == 429:
                                display_error("You got ratelimited! Trying again in 30 seconds...")
                                await asyncio.sleep(30)
                            elif status == 403:
                                display_error("Your token got updated. Getting a new one...")
                                await self.auth.update_csrf_token()
                            elif status == 412:
                                continue
                            else:
                                display_error(f"Failed to sell limited ({status})")
                                self.current_asset.next()
                                break
    
                    if self.sale_webhook_enabled:
                        asyncio.create_task(self.send_sale_webhook(self.current_asset))

                    if self.save_items:
                        self.seen.add(self.current_asset.id)
                        with open("items/seen.json", "w") as f: f.write(json.dumps(list(self.seen)))

                    self.next_asset()
    
                    await asyncio.sleep(0.5)
                elif choose == "2":
                    new_price = await display_input("Enter a new price to sell this limited: ")
                    self.current_asset.price_to_sell = new_price
                    display_success(f"Successfully set a new price to sell! ({GRAY_COLOR}${self.current_asset.price_to_sell}{Color.white})")
                    await asyncio.sleep(0.5)
                elif choose == "3":
                    self.blacklist.add(self.current_asset.id)
                    with open("items/blacklist.json", "w") as f: f.write(json.dumps(list(self.blacklist)))

                    self.next_asset()
    
                    display_success(f"Successfully added {GRAY_COLOR}{self.current_asset.name} ({self.current_asset.id}){Color.white} into a blacklist!")
                    await asyncio.sleep(0.5)
                elif choose == "4":
                    if self.save_items:
                        self.seen.add(self.current_asset.id)
                        with open("items/seen.json", "w") as f: f.write(json.dumps(list(self.seen)))

                    self.next_asset()

                    display_success(f"Skipped current item")
                    await asyncio.sleep(0.5)

        display_done(f"Sold {GRAY_COLOR}{self.total_sold}x{Color.white} items")

    async def start_buy_checking(self):
        async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=None),
                trust_env=True
        ) as session:

            while True:
                await asyncio.sleep(30)

                sales = await self._get_recent_sales()

                if sales is None:
                    continue

                users_thumbnails = await self._get_users_thumbnails([str(user["id"]) for user in sales["agent"]])

                for sale, user_thumbnail in zip(sales, users_thumbnails):
                    transaction_details = sale["details"]

                    if transaction_details["type"] != "Asset":
                        continue

                    asset_id = str(transaction_details["id"])

                    if asset_id in self.assets:
                        transaction_time = datetime.strptime(sale["created"], "%Y-%m-%dT%H:%M:%S.%fZ")
                        sold_amount = sales["currency"]["amount"]
                        user = sales["agent"]

                        asset = self.assets[self.assets.index(asset_id)]

                        embed = {
                            "content": self.user_to_ping,
                            "embeds": [{
                                "title": "Some Bought You Item",
                                "description": f"**Item name: **`{asset.name}`\n"
                                               f"**Sold for: **`{sold_amount} ({sold_amount // 2})`\n"
                                               f"**Sold at: **<t:{transaction_time}:f>",

                                "url": "https://www.roblox.com/catalog/16769497010/Crystal-Flamefire-Dominus",
                                "timestamp": transaction_time,
                                "color": 2469096,
                                "footer": {
                                    "text": "Was Bought at"
                                },
                                "thumbnail": {
                                    "url": asset.thumbnail
                                },
                                "author": {
                                    "url": f"https://www.roblox.com/users/{user['id']}/profile",
                                    "name": user["name"],
                                    "icon_url": user_thumbnail
                                }
                            }]
                        }


                        async with session.post(self.buy_webhook_url, json=embed):
                            self.assets.remove(transaction_asset["id"])

    async def update_console(self) -> str:
        clear_console()
        display_main()

        data = {
            "Info": {
                "Discord Bot": define_status(self.discord_bot),
                "OnBuy Webhook": define_status(self.buy_webhook_enabled),
                "OnSale Webhook": define_status(self.sale_webhook_enabled),
                "Under Cut": f"{self.under_cut_amount}{'%' if self.under_cut_type == 'percent' else ''}",
                "Total Blacklist": f"{len(self.blacklist)}"
            },
            "Current Item": {
                "Name": self.current_asset.name,
                "Creator": self.current_asset.creator_name,
                "Price": f"{self.current_asset.price:,}",
                "Quality": f"{self.current_asset.quantity:,}",
                "Lowest Price": f"{self.current_asset.lowest_resale_price:,}",
                "Price to Sell": f"{self.current_asset.price_to_sell:,}"
            }
        }

        display_sections(data)

        choose = await display_input("[1] - Sell | [2] - Set Price | [3] - Blacklist | [4] - Skip\n> ")
        return choose

    async def send_sale_webhook(self, col: Collectible) -> None:
        embed = {
            "content": self.user_to_ping,
            "embeds": [{
                "title": "A New Item Went on Sale",
                "color": 2469096,
                "fields": [
                    {
                      "name": "Sold Amount",
                      "value": f"`{len(list(filter(lambda x: x['on_sale'], col.collectibles)))}`",
                      "inline": True
                    },
                    {
                      "name": "Selling Price",
                      "value": f"`{col.price_to_sell}`",
                      "inline": True
                    },
                    {
                      "name": "Name",
                      "value": f"`{col.name}`",
                      "inline": True
                    }
                ],
                "thumbnail": {
                    "url": col.thumbnail
                },
                "timestamp": str(datetime.now()),
                "url": col.link,
                "footer": {
                    "text": "Was sold at"
                }
            }]
        }

        while True:
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.post(self.sale_webhook_url, json=embed) as response:
                    if response.status == 429:
                        await asyncio.sleep(30)
                        continue

                    break

    async def _get_recent_sales(self) -> List[dict]:
        async with self.auth.session.get(
            f"https://economy.roblox.com/v2/users/{self.auth.user_id}/transactions?"
            "cursor=&limit=10&transactionType=Sale&itemPricingType=PaidAndLimited",
            ssl=False
        ) as response:
            if response.status != 200:
                return None

            return (await response.json()).get("data")

    async def _get_users_thumbnails(self, user_ids: Iterable[str]) -> Union[List[str], None]:
        thumbnails = []

        for chunk in slice_list(user_ids, 100):
            async with self.auth.session.get(
                    "https://thumbnails.roblox.com/v1/users/avatar-headshot?"
                    f"userIds={','.join(chunk)}&size=50x50&format=Png&isCircular=false",
                    ssl=False
            ) as response:
                data = await response.json()

                if data.get("data") is None:
                    return thumbnails

                thumbnails.extend([img["imageUrl"] if img["state"] == "Completed" else self.FAILED_IMAGE_URL
                                   for img in data["data"]])

        return thumbnails

    async def _get_assets_thumbnails(self, asset_ids: Iterable[str]) -> Union[List[str], None]:
        thumbnails = []

        for chunk in slice_list(asset_ids, 100):
            async with self.auth.session.get(
                    "https://thumbnails.roblox.com/v1/assets?"
                    f"assetIds={','.join(chunk)}&returnPolicy=PlaceHolder&size=50x50&format=Png&isCircular=false",
                    ssl=False
            ) as response:
                data = await response.json()

                if data.get("data") is None:
                    return thumbnails

                thumbnails.extend([img["imageUrl"] if img["state"] == "Completed" else self.FAILED_IMAGE_URL
                                   for img in data["data"]])

        return thumbnails

    async def _get_assets_details(self, asset_ids: List[Union[int, str]]) -> List[dict]:
        assets = []

        for chunk in slice_list(asset_ids, 120):
            payload = {"items": [{"itemType": 1, "id": str(_id)} for _id in chunk]}

            async with self.auth.session.post(
                    "https://catalog.roblox.com/v1/catalog/items/details",
                    json=payload
            ) as response:
                data = (await response.json()).get("data")

                if not data:
                    return assets

                assets.extend(data)

        return assets

    async def _get_user_collectibles(self, item_type: int) -> List[dict]:
        assets = []
        cursor = ""

        while True:
            async with self.auth.session.get(
                    f"https://inventory.roblox.com/v2/users/{self.auth.user_id}/inventory/{item_type}?"
                    f"limit=100&cursor={cursor}&sortOrder=Desc",
                    ssl=False
            ) as response:

                if response.status != 200:
                    return assets

                data = await response.json()

                cursor = data.get("nextPageCursor")
                assets.extend(
                    [asset for asset in data.get("data") if asset.get("collectibleItemId") is not None])

                if not cursor:
                    return assets

    async def _get_current_cap(self) -> Union[dict, None]:
        async with self.auth.session.get(
                "https://itemconfiguration.roblox.com/v1/collectibles/metadata",
                ssl=False
        ) as response:
            if response.status != 200:
                return None

            return (await response.json())["limitedItemPriceFloors"]

    def __len__(self):
        return len(self.assets)


async def main():
    display_info("Setting up everything...")

    display_info("Loading config")
    config = load_file("config.json")

    display_info("Loading data assets")
    blacklist = load_file("items/blacklist.json")
    seen = load_file("items/seen.json")

    auto_seller = AutoSeller(config, blacklist, seen)

    try:
        await auto_seller.start()
    except LoginFailure:
        return display_exception("Invalid discord token provided")
    except Exception as err:
        return display_exception(f"Unknown error occurred: {err}")
    finally:
        if (auth := getattr(auto_seller, "auth")) is not None:
            asyncio.run(auth.close_session())


if __name__ == "__main__":
    asyncio.run(main())