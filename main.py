import sys
import os

VERSION = "1.1.1"

try:
    import asyncio
    import json
    # from tqdm import tqdm
    from datetime import datetime
    import traceback
    import aiohttp
    from collections import deque
    from rgbprint import Color
    import time
    from discord.errors import LoginFailure

    from typing import List

    from core.utils import *
    from core.visuals import *
    from core.detection import *
    from discord_bot import start as discord_bot_start

    os.system("cls" if os.name == "nt" else "clear")
except ModuleNotFoundError:
    install = input("Uninstalled modules found, do you want to install them? Y/n: ").lower() == "y"

    if install:
        print("Installing modules now...")
        os.system("pip install aiohttp rgbprint discord.py aioconsole")
        print("Successfully installed required modules.")
    else:
        print("Aborting installing modules.")

    input("Press \"enter\" to exit...")
    sys.exit(1)


class AutoSeller:
    def __init__(self, config: dict, blacklist: List[int], seen: List[int], not_resable: List[int]) -> None:
        self.config = config

        self.blacklist = set(blacklist)
        self.seen = set(seen)
        self.not_resable = set(not_resable)

        self.discord_bot = config["Discord_Bot"]
        self.owners_list = self.discord_bot.get("Owner_IDs", [])
        self.discord_bot_enabled = self.discord_bot.get("Enabled", False)

        webhooks = config["Webhook"]
        self.user_to_ping = f"<@{webhooks['User_To_Ping']}>" if webhooks.get("User_To_Ping", 0) else ""

        buy_webhook = webhooks["OnBuy"]
        self.buy_webhook_url = buy_webhook.get("Url", "").strip()
        self.buy_webhook_enabled = buy_webhook.get("Enabled", False)

        sale_webhook = webhooks["OnSale"]
        self.sale_webhook_url = sale_webhook.get("Url", "").strip()
        self.sale_webhook_enabled = sale_webhook.get("Enabled", False)

        under_cut = config["Under_Cut"]
        self.under_cut_type = under_cut.get("Type", "percent")
        self.under_cut_amount = under_cut.get("Value", 10)

        auto_sell = config["Auto_Sell"]
        self.auto_sell_enabled = not auto_sell.get("Ask_Before_Sell", False)
        self.keep_serials = auto_sell.get("Keep_Serials", 0)
        self.keep_copy = auto_sell.get("Keep_Copy", 0)
        self.hide_on_sale = auto_sell.get("Hide_OnSale", False)
        self.save_items = auto_sell.get("Save_Seen_Items", False)

        self.total_sold = 0

        self.items = []
        self.current_index = 0
        self.done = False

        self.auth = Auth(config.get("Cookie", ""))
        self.control_panel = None

    async def start(self):
        if self.buy_webhook_enabled and (not self.buy_webhook_url.startswith("https://discord.com/api/webhooks/") or not await is_webhook_exists(self.buy_webhook_url)):
            return display_exception("Invalid on buy webhook url provided")

        elif self.sale_webhook_enabled and (not self.sale_webhook_url.startswith("https://discord.com/api/webhooks/") or not await is_webhook_exists(self.sale_webhook_url)):
            return display_exception("Invalid on sale webhook url provided")

        elif self.under_cut_type not in ["robux", "percent"]:
            return display_exception("Invalid under cut type provided, must be \"robux\" or \"percent\"")

        elif self.under_cut_amount < 0:
            return display_exception("Under cut amount can not be less than 0")

        display_info("Checking cookie to be valid")
        await self.auth.update_auth_info()
        if self.auth.user_id is None:
            return display_exception("Invalid cookie provided")

        display_info("Checking premium owning")
        if not await self.auth.get_premium_owning():
            return display_exception("You dont have premium to sell limiteds")

        display_info("Getting current limiteds cap")
        items_cap = await get_current_cap(self.auth)

        display_info("Loading your inventory")
        tasks = [asyncio.create_task(get_user_inventory(item_type, self.auth)) for item_type in ItemTypes.integers()]
        user_items = sum(await asyncio.gather(*tasks), [])

        if not user_items:
            return display_exception("You dont have any limited UGC items")

        item_ids = [str(asset["assetId"]) for asset in user_items]

        display_info("Loading items thumbnails")
        tasks = [asyncio.create_task(get_assets_thumbnails(chunk, self.auth)) for chunk in slice_list(item_ids, 100)]
        item_thumbnails = sum(await asyncio.gather(*tasks), [])

        display_info(f"Found {len(user_items)} items. Checking them...")
        tasks = [asyncio.create_task(get_items_details(chunk, self.auth)) for chunk in slice_list(item_ids, 120)]
        items_details = sum(await asyncio.gather(*tasks), [])

        ignored_items = list(self.seen | self.blacklist | self.not_resable)

        for item, item_details, thumbnail in zip(user_items, items_details, item_thumbnails):
            item_id = item["assetId"]
            item_serial = item["serialNumber"]
            item_lrp = item_details["lowestResalePrice"]

            if item_id in ignored_items or (self.keep_serials != 0 and self.keep_serials <= item_serial):
                continue

            item_obj = [item for item in self.items if item.id == item_id]

            if not item_obj:
                asset_cap = items_cap[ItemTypes.types[item_details["assetType"]]]["priceFloor"]
                sell_price = item_lrp - self.under_cut_amount if self.under_cut_type == "robux" else round(item_lrp - (item_lrp / 100 * self.under_cut_amount)) if item_lrp > asset_cap else asset_cap

                col = Item(
                    _id=item["assetId"],
                    name=item["assetName"],
                    thumbnail=thumbnail,
                    quantity=item_details.get("totalQuantity"),
                    price=item_details.get("price"),
                    lowest_resale_price=item_lrp,
                    offered_price=sell_price,
                    creator_id=item_details.get("creatorTargetId"),
                    creator_name=item_details.get("creatorName"),
                    creator_type=item_details.get("creatorType"),
                    item_id=item["collectibleItemId"],
                    auth=self.auth
                )

                col.add_collectible(
                    serial=item_serial,
                    item_id=item["collectibleItemId"],
                    instance_id=item["collectibleItemInstanceId"]
                )

                self.items.append(col)
            else:
                item_obj[0].add_collectible(
                    serial=item_serial,
                    item_id=item["collectibleItemId"],
                    instance_id=item["collectibleItemInstanceId"]
                )
        
        if self.keep_copy != 0:
            for i, col in enumerate(self.items):
                if len(col.collectibles) < self.keep_copy:
                    self.items.pop(i)
        
        if not self.items:
            return display_exception(f"You dont have any limited with {self.keep_copy + 1} collectibles or higher")
        
        # if self.discord_bot_enabled:
        #     TasksManager.set_success("https://cdn.discordapp.com/emojis/1244723120292499467.webp?size=40&quality=lossless")
        #     TasksManager.set_error(":octagonal_sign:")
        #     TasksManager.set_skip("https://cdn.discordapp.com/emojis/1244723114827448381.webp?size=40&quality=lossless")
            
        self.items.sort(key=str)

        clear_console()

        try:
            tasks = [
                asyncio.create_task(discord_bot_start(self)) if self.discord_bot.get("Enabled", False) else None,
                asyncio.create_task(self.start_buy_checking()) if self.buy_webhook_enabled else None,
                asyncio.create_task(self.start_selling())
            ]
            await asyncio.gather(*filter(None, tasks))
        except LoginFailure:
            return display_exception("Invalid discord token provided")
        except Exception:
            return display_exception(f"Unknown error occurred:\n\n{traceback.format_exc()}")
        finally:
            await self.auth.close_session()

    def next_asset(self):
        if (self.current_index + 1) < len(self.items):
            self.current_index += 1
        else:
            self.current_index = 0
            self.done = True

    @property
    def current_asset(self):
        return self.items[self.current_index]

    async def start_selling(self):
        for i in range(2):
            await asyncio.gather(
                self.items[i].fetch_resales(save_resales=False),
                self.items[i].fetch_sales(save_sales=False)
            )

        if self.auto_sell_enabled:
            while not self.done:
                display_selling(f"Selling {GRAY_COLOR}{len(self.current_asset.collectibles)}x{Color.white} "
                                f"of {GRAY_COLOR}{self.current_asset.name}{Color.white} items...")

                sold_amount = await self.current_asset.sell_collectibles(skip_on_sale=self.hide_on_sale)
                if sold_amount is None:
                    self.not_resable.add(self.current_asset.id)
                    with open("items/not_resable.json", "w") as f:
                        f.write(json.dumps(list(self.not_resable)))
                else:
                    self.total_sold += sold_amount

                    if self.sale_webhook_enabled and sold_amount > 0:
                        asyncio.create_task(self.send_sale_webhook(self.current_asset, sold_amount))
                    if self.save_items:
                        self.seen.add(self.current_asset.id)
                        with open("items/seen.json", "w") as f:
                            f.write(json.dumps(list(self.seen)))

                self.next_asset()
                await asyncio.sleep(0.5)
        else:
            while not self.done:
                choose = await self.update_console()
    
                if choose == "1":
                    display_selling(
                        f"Selling {GRAY_COLOR}{len(self.current_asset.collectibles)}x{Color.white} items...")

                    sold_amount = await self.current_asset.sell_collectibles(skip_on_sale=self.hide_on_sale)
                    if sold_amount is None:
                        self.not_resable.add(self.current_asset.id)
                        with open("items/not_resable.json", "w") as f:
                            f.write(json.dumps(list(self.not_resable)))
                    else:
                        self.total_sold += sold_amount

                        if self.sale_webhook_enabled and sold_amount > 0:
                            asyncio.create_task(self.send_sale_webhook(self.current_asset, sold_amount))

                    if self.save_items:
                        self.seen.add(self.current_asset.id)
                        with open("items/seen.json", "w") as f:
                            f.write(json.dumps(list(self.seen)))

                    self.next_asset()

                    try:
                        asyncio.create_task(self.items[self.current_index + 1].fetch_resales(save_resales=False))
                        asyncio.create_task(self.items[self.current_index + 1].fetch_sales(save_sales=False))
                    except IndexError:
                        pass

                    await asyncio.sleep(0.7)
                elif choose == "2":
                    new_price = await display_input("Enter a new price to sell this limited: ")
                    self.current_asset.price_to_sell = int(new_price)

                    display_success(f"Successfully set a new price to sell! "
                                    f"({GRAY_COLOR}${self.current_asset.price_to_sell}{Color.white})")
                    await asyncio.sleep(0.7)
                elif choose == "3":
                    self.blacklist.add(self.current_asset.id)
                    with open("items/blacklist.json", "w") as f:
                        f.write(json.dumps(list(self.blacklist)))

                    self.next_asset()
                    
                    try:
                        asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_resales(save_resales=False))
                        asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_sales(save_sales=False))
                    except IndexError:
                        pass
    
                    display_success(f"Successfully added {GRAY_COLOR}{self.current_asset.name} "
                                    f"({self.current_asset.id}){Color.white} into a blacklist!")
                    await asyncio.sleep(0.7)
                elif choose == "4":
                    self.next_asset()
                    
                    try:
                        asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_resales(save_resales=False))
                        asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_sales(save_sales=False))
                    except IndexError:
                        pass

                    display_success(f"Skipped current item")
                    await asyncio.sleep(0.7)

        clear_console()
        await display_done(f"Sold {GRAY_COLOR}{self.total_sold}x{Color.white} items")

    async def start_buy_checking(self):
        async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=None),
                trust_env=True
        ) as session:

            while True:
                await asyncio.sleep(10)

                sales = await get_recent_sales(self.auth)

                if sales is None:
                    continue

                users_thumbnails = await get_users_thumbnails([str(sale["agent"]["id"]) for sale in sales], self.auth)

                for sale, user_thumbnail in zip(sales, users_thumbnails):
                    transaction_details = sale["details"]

                    if transaction_details["type"] != "Asset":
                        continue
                    
                    item_id = transaction_details["id"]
                    try:
                        index, item = [(index, item) for index, item in enumerate(self.items) if item.id == item_id][0]
                    except IndexError:
                        item = None

                    if item is not None and len(item.collectibles) <= 1:
                        transaction_time = time.mktime(datetime.strptime(sale["created"], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())
                        sold_amount = sale["currency"]["amount"]
                        user = sale["agent"]

                        embed = {
                            "content": self.user_to_ping,
                            "embeds":[{
                                "title": "Some Bought You Item",
                                "description": f"**Item name: **`{item.name}`\n"
                                               f"**Sold for: **`${sold_amount} (you got ${sold_amount // 2})`\n"
                                               f"**Sold at: **<t:{transaction_time:.0f}:f>",

                                "url": "https://www.roblox.com/catalog/16769497010/Crystal-Flamefire-Dominus",
                                "timestamp": sale["created"],
                                "color": 2469096,
                                "footer": {
                                    "text": "Was Sold at"
                                },
                                "thumbnail": {
                                    "url": item.thumbnail
                                },
                                "author": {
                                    "url": f"https://www.roblox.com/users/{user['id']}/profile",
                                    "name": user["name"],
                                    "icon_url": user_thumbnail
                                }
                            }]
                        }

                        async with session.post(self.buy_webhook_url, json=embed) as response:
                            if response.status == 200:
                                self.items.pop(index)
                            

    async def update_console(self) -> str:
        clear_console()
        display_main()

        data = {
            "Info": {
                "Discord Bot": define_status(self.discord_bot_enabled),
                "Under Cut": f"-{self.under_cut_amount}{'%' if self.under_cut_type == 'percent' else ''}",
                "Save Items": define_status(self.save_items),
                "Total Blacklist": f"{len(self.blacklist)}"
            },
            "Current Item": {
                "Name": self.current_asset.name,
                "Creator": self.current_asset.creator_name,
                "Price": f"{self.current_asset.price:,}",
                "Quality": f"{self.current_asset.quantity:,}",
                "Lowest Price": "No Resales" if self.current_asset.has_resales is False else f"{self.current_asset.lowest_resale_price:,}",
                "Price to Sell": f"{self.current_asset.price_to_sell:,}",
                "RAP": f"{self.current_asset.recent_average_price:,}",
                "Latest Sale": f"{self.current_asset.latest_sale:,}"
            }
        }

        display_sections(data)

        choose = await display_input("[1] - Sell | [2] - Set Price | [3] - Blacklist | [4] - Skip\n> ")
        return choose

    async def send_sale_webhook(self, item: Item, sold_amount: int) -> None:
        embed = {
            "content": self.user_to_ping,
            "embeds": [{
                "title": "A New Item Went on Sale",
                "color": 2469096,
                "description": f"**Item name: **`{item.name}`\n"
                               f"**Sold amount: **`{sold_amount}`\n"
                               f"**Sold for: **`{item.price_to_sell}`",
                "thumbnail": {
                    "url": item.thumbnail
                },
                "timestamp": str(datetime.now()),
                "url": item.link,
                "footer": {
                    "text": "Were sold at"
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

    def __len__(self):
        return len(self.items)


async def check_for_update() -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://raw.githubusercontent.com/cofiprofim/AutoSeller/refs/heads/main/main.py") as response:
            try:
                version = (await response.text()).strip().split("VERSION = \"")[1].split("\"")[0]
            except IndexError:
                return False

            if version != VERSION:
                return True
            else:
                return False


async def main():
    display_info("Setting up everything...")
    
    display_info("Checking for updates")
    if (await check_for_update()):
        return display_new("Your code is outdated. Please update it from github")

    display_info("Loading config")
    config = load_file("config.json")

    display_info("Loading data assets")
    blacklist = load_file("items/blacklist.json")
    seen = load_file("items/seen.json")
    not_resable = load_file("items/not_resable.json")

    auto_seller = AutoSeller(config, blacklist, seen, not_resable)

    try:
        await auto_seller.start()
    except Exception:
        return display_exception(f"Unknown error occurred:\n\n{traceback.format_exc()}")
    finally:
        if (auth := getattr(auto_seller, "auth")) is not None:
            await auth.close_session()


if __name__ == "__main__":
    asyncio.run(main())

