import sys
import os

VERSION = "1.2.2"

try:
    import asyncio
    from datetime import datetime
    import traceback
    import aiohttp
    from collections import deque
    from rgbprint import Color
    from aioconsole import ainput
    from discord.errors import LoginFailure

    from typing import List, Optional, Any, Union

    from core.utils import (Item, Auth, WithBool, ItemTypes, FileSync,
                            load_file, is_webhook_exists, slice_list, define_status)
    from core.visuals import Display, Tools, GRAY_COLOR
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

__all__ = ("AutoSeller")


class AutoSeller:
    under_cut_types = ("robux", "percent")
    sort_items_types = ("name", "creator", "price")
    
    def __init__(
        self,
        config: dict,
        blacklist: FileSync,
        seen: FileSync,
        not_resable: FileSync
    ) -> None:
        
        self.config = config

        self.blacklist = blacklist
        self.seen = seen
        self.not_resable = not_resable

        discord_bot = config["Discord_Bot"]
        self.discord_bot = discord_bot.get("Enabled", False)
        self.bot_token = discord_bot.get("Token", "")
        self.bot_prefix = discord_bot.get("Prefix", "")
        self.owners_list = discord_bot.get("Owner_IDs", [])
        
        webhooks = config["Webhook"]
        self.user_to_ping = f"<@{webhooks['User_To_Ping']}>" if webhooks.get("User_To_Ping", 0) else ""

        buy_webhook = webhooks["OnBuy"]
        self.buy_webhook_url = buy_webhook.get("Url", "").strip()
        self.buy_webhook = buy_webhook.get("Enabled", False)

        sale_webhook = webhooks["OnSale"]
        self.sale_webhook_url = sale_webhook.get("Url", "").strip()
        self.sale_webhook = sale_webhook.get("Enabled", False)

        auto_sell = config["Auto_Sell"]
        self.auto_sell = not auto_sell.get("Ask_Before_Sell", False)
        self.skip_on_sale = auto_sell.get("Hide_OnSale", False)
        self.skip_if_cheapest = auto_sell.get("Skip_If_Cheapest", False)
        self.sort_items_by = auto_sell.get("Sort_Items_By", "name")
        self.keep_serials = auto_sell.get("Keep_Serials", 0)
        self.keep_copy = auto_sell.get("Keep_Copy", 0)
        self.creators_blacklist = auto_sell.get("Creators_Blacklist", [])
        
        under_cut = auto_sell["Under_Cut"]
        self.under_cut_type = under_cut.get("Type", "percent")
        self.under_cut_amount = under_cut.get("Value", 10)
        
        save_progress = auto_sell["Save_Progress"]
        self.save_progress = save_progress.get("Enabled", False)
        self.clear_after_done = save_progress.get("Clear_After_Done", False)

        self._items = {}
        self.total_sold = 0
        self.current_index = 0
        self.done = False
        self.selling = WithBool()
        self.sold_items = deque(maxlen=10)
        self.loaded_time = None

        self.auth = Auth(config.get("Cookie", "").strip())
        
        self.control_panel = None
    
    @property
    def items(self) -> List[Item]:
        return list(self._items.values())

    async def start(self):
        await self.auth.update_csrf_token()
        
        if self.discord_bot:
            if not self.bot_token:
                return Display.exception("Invalid discord bot token provided")
            
            elif not self.bot_prefix:
                return Display.exception("Discord bot prefix can not be empty")
        
        elif self.buy_webhook and not await is_webhook_exists(self.buy_webhook_url):
            return Display.exception("Invalid on buy webhook url provided")

        elif self.sale_webhook and not await is_webhook_exists(self.sale_webhook_url):
            return Display.exception("Invalid on sale webhook url provided")

        elif self.under_cut_type not in self.under_cut_types:
            return Display.exception(f"Invalid under cut type provided, must be: {self.under_cut_types}")
        
        elif self.sort_items_by not in self.sort_items_types:
            return Display.exception(f"Invalid sort items type provided, must be: {self.sort_items_types}")

        elif self.under_cut_amount < 0:
            return Display.exception("Under cut amount can not be less than 0")


        Display.info("Checking cookie to be valid")
        await self.auth.update_auth_info()
        if self.auth.user_id is None:
            return Display.exception("Invalid cookie provided")

        # Display.info("Checking premium owning")
        # if not await self.auth.get_premium_owning():
        #     return Display.exception("You dont have premium to sell limiteds")

        Display.info("Getting current limiteds cap")
        items_cap = await get_current_cap(self.auth)

        Display.info("Loading your inventory")
        tasks = [asyncio.create_task(get_user_inventory(item_type, self.auth)) for item_type in ItemTypes.integers()]
        user_items = sum(await asyncio.gather(*tasks), [])

        if not user_items:
            return Display.exception("You dont have any limited UGC items")

        item_ids = [str(asset["assetId"]) for asset in user_items]

        Display.info("Loading items thumbnails")
        tasks = [asyncio.create_task(get_assets_thumbnails(chunk, self.auth)) for chunk in slice_list(item_ids, 100)]
        item_thumbnails = sum(await asyncio.gather(*tasks), [])

        Display.info(f"Found {len(user_items)} items. Checking them...")
        tasks = [asyncio.create_task(get_items_details(chunk, self.auth)) for chunk in slice_list(item_ids, 120)]
        items_details = sum(await asyncio.gather(*tasks), [])

        ignored_items = list(self.seen | self.blacklist | self.not_resable)
        
        for item, item_details, thumbnail in zip(user_items, items_details, item_thumbnails):
            item_id = item["assetId"]
            item_serial = item["serialNumber"]
            item_lrp = item_details["lowestResalePrice"]
            creator_id = item_details.get("creatorTargetId")

            if item_id in ignored_items or (self.creators_blacklist and creator_id in self.creators_blacklist):
                continue
            
            item_obj = self.get_item(item_id)

            if item_obj is None:
                asset_cap = items_cap[ItemTypes.types[item_details["assetType"]]]["priceFloor"]
                sell_price = item_lrp - self.under_cut_amount if self.under_cut_type == "robux" else round(item_lrp - (item_lrp / 100 * self.under_cut_amount)) if item_lrp > asset_cap else asset_cap

                new = Item(
                    _id=item["assetId"],
                    name=item["assetName"],
                    thumbnail=thumbnail,
                    quantity=item_details.get("totalQuantity"),
                    price=item_details.get("price"),
                    lowest_resale_price=item_lrp,
                    offered_price=sell_price,
                    creator_id=creator_id,
                    creator_name=item_details.get("creatorName"),
                    creator_type=item_details.get("creatorType"),
                    item_id=item["collectibleItemId"],
                    auth=self.auth
                )

                new.add_collectible(
                    serial=item_serial,
                    item_id=item["collectibleItemId"],
                    instance_id=item["collectibleItemInstanceId"]
                )

                self.add_item(new)
            else:
                item_obj.add_collectible(
                    serial=item_serial,
                    item_id=item["collectibleItemId"],
                    instance_id=item["collectibleItemInstanceId"]
                )
        
        if not self._items:
            Display.error(f"You dont have any limiteds that are not in {GRAY_COLOR}blacklist/{Color.white} directory")
            clear_items = await Display.ainput(f"Do you want to reset your selling progress? (Y/n): ")
            
            if clear_items.lower() == "y":
                self.seen.clear()
                Display.success("Cleared your limiteds selling progress")
                Tools.exit_program() 

        if self.keep_serials != 0 or self.keep_copy != 0:
            for item in self.items:
                if len(item.collectibles) <= self.keep_copy:
                    self.remove_item(item.id)
                    continue
                
                for col in item.collectibles:
                    if col.serial > self.keep_serials:
                        col.skip_on_sale = True
        
        if not self._items:
            not_met = []
            
            if self.keep_copy != 0:
                not_met.append(f"{self.keep_copy} copies or higher")
            if self.keep_serials != 0:
                not_met.append(f"{self.keep_serials} serial or higher")
            
            list_requirements = ", ".join(not_met)
            return Display.exception(f"You dont have any limiteds with {list_requirements}")
        
        self.loaded_time = datetime.now()

        # if self.discord_bot_enabled:
        #     TasksManager.set_success("https://cdn.discordapp.com/emojis/1244723120292499467.webp?size=40&quality=lossless")
        #     TasksManager.set_error(":octagonal_sign:")
        #     TasksManager.set_skip("https://cdn.discordapp.com/emojis/1244723114827448381.webp?size=40&quality=lossless")
        
        self._items = dict(sorted(self._items.items(), key=lambda x: x[1].name))

        try:
            async with self:
                tasks = [
                    asyncio.create_task(discord_bot_start(self)) if self.discord_bot else None,
                    asyncio.create_task(self.start_buy_checking()) if self.buy_webhook else None,
                    asyncio.create_task(self.start_selling())
                ]
                await asyncio.gather(*filter(None, tasks))
            
        except LoginFailure:
            return Display.exception("Invalid discord token provided")
        except Exception:
            return Display.exception(f"Unknown error occurred:\n\n{traceback.format_exc()}")
    
    def get_item(self, _id: int, default: Optional[Any] = None) -> Union[Item, Any]:
        return self._items.get(_id, default)
    
    def add_item(self, item: Item) -> None:
        self._items.update({item.id: item})

    def remove_item(self, _id: int) -> None:
        self._items.pop(_id)

    def next_item(self, *,
                  fetch_sales: Optional[bool] = True,
                  fetch_resales: Optional[bool] = True,
                  step_index: Optional[int] = 1):
        
        if (self.current_index + 1) < len(self.items):
            self.current_index += 1
        else:
            self.current_index = 0
            self.done = True
        
        try:
            if fetch_sales:
                asyncio.create_task(self.items[self.current_index + step_index].fetch_sales(save_sales=False))
            if fetch_resales:
                asyncio.create_task(self.items[self.current_index + step_index].fetch_resales(save_resales=False))
        except IndexError:
            pass

    @property
    def current_item(self):
        return self.items[self.current_index]

    async def start_selling(self):
        for i in range(2):
            try:
                await asyncio.gather(
                    self.items[i].fetch_resales(save_resales=False),
                    self.items[i].fetch_sales(save_sales=False)
                )
            except IndexError:
                break

        if self.auto_sell:
            while not self.done:
                await Display.custom(
                    f"Selling {GRAY_COLOR}{len(self.current_item.collectibles)}x{Color.white} "
                    f"of {GRAY_COLOR}{self.current_item.name}{Color.white} items...",
                    "selling", Color(255, 153, 0))

                sold_amount = await self.current_item.sell_collectibles(
                    skip_on_sale=self.skip_on_sale,
                    skip_if_cheapest=self.skip_if_cheapest,
                    log=True
                )
                if sold_amount is None:
                    self.not_resable.add(self.current_item.id)
                else:
                    self.total_sold += sold_amount

                    if self.sale_webhook and sold_amount > 0:
                        asyncio.create_task(self.send_sale_webhook(self.current_item, sold_amount))
                    if self.save_progress:
                        self.seen.add(self.current_item.id)

                self.next_item()
                await asyncio.sleep(0.5)
        else:
            while not self.done:
                await self.update_console()
                choose = await ainput()
    
                if choose == "1":
                    if self.selling:
                        Display.error("This item is already being sold")
                        await asyncio.sleep(0.7)
                        continue
                    
                    with self.selling:
                        await Display.custom(
                            f"Selling {GRAY_COLOR}{len(self.current_item.collectibles)}x{Color.white} items...",
                            "selling", Color(255, 153, 0))

                        sold_amount = await self.current_item.sell_collectibles(
                            skip_on_sale=self.skip_on_sale,
                            skip_if_cheapest=self.skip_if_cheapest,
                            log=True
                        )
                        if sold_amount is None:
                            self.not_resable.add(self.current_item.id)
                        else:
                            self.total_sold += sold_amount

                            if self.sale_webhook and sold_amount > 0:
                                asyncio.create_task(self.send_sale_webhook(self.current_item, sold_amount))

                        if self.save_progress:
                            self.seen.add(self.current_item.id)

                        self.next_item()
                        
                        if self.control_panel is not None:
                            asyncio.create_task(self.control_panel.update_service_message(self.control_panel.make_embed()))
                        
                elif choose == "2":
                    new_price = await Display.ainput(f"Enter the new price you want to sell: ")
                    
                    if not new_price.isdigit():
                        Display.error("Invalid price amount was provided")
                        await asyncio.sleep(0.7)
                        continue
                    
                    self.current_item.price_to_sell = int(new_price)

                    Display.success(f"Successfully set a new price to sell!"
                                    f"({GRAY_COLOR}${self.current_item.price_to_sell}{Color.white})")
                elif choose == "3":
                    self.blacklist.add(self.current_item.id)
                    self.next_item()
    
                    Display.success(f"Successfully added {GRAY_COLOR}{self.current_item.name} "
                                    f"({self.current_item.id}){Color.white} into a blacklist!")
                elif choose == "4":
                    if self.save_progress:
                        self.seen.add(self.current_item.id)
                    
                    self.next_item()
                    Display.skipping(f"Skipped {GRAY_COLOR}{len(self.current_item.collectibles)}x{Color.white} collectibles")

                await asyncio.sleep(0.7)
        
        Tools.clear_console()
        
        await Display.custom(
            f"Sold {GRAY_COLOR}{self.total_sold}x{Color.white} items",
            "done", Color(207, 222, 0))
        
        if not self.clear_after_done:
            clear_items = await Display.ainput(f"Do you want to reset your selling progress? (Y/n): ")
        
        if self.clear_after_done or (clear_items.lower() == "y"):
            self.seen.clear()
            Display.success("Cleared your limiteds selling progress")
            Tools.exit_program()
    
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
                
                user_ids = [str(sale["agent"]["id"]) for sale in sales]
                users_thumbnails = await get_users_thumbnails(user_ids, self.auth)

                for sale, user_thumbnail in zip(sales, users_thumbnails):
                    transaction_details = sale["details"]
                    transaction_time = datetime.strptime(sale["created"], "%Y-%m-%dT%H:%M:%S.%fZ")

                    if transaction_details["type"] != "Asset" or transaction_time < self.loaded_time:
                        continue
                    
                    item = self.get_item(transaction_details["id"])
                    
                    if item is None:
                        continue
                    
                    old_collectibles = item.collectibles
                    await item.fetch_collectibles()
                    
                    for col in old_collectibles:
                        current = item.get_collectible(col.serial)
                        
                        was_sold = [c for c in self.sold_items if c[0] == item.id and c[1] == current.serial]
                        if current is not None or was_sold:
                            continue
                        
                        sold_amount = sale["currency"]["amount"]
                        user = sale["agent"]

                        embed = {
                            "content": self.user_to_ping,
                            "embeds":[{
                                "title": "Some Bought You Item",
                                "description": f"**Item name: **`{item.name}`\n"
                                               f"**Item Serial: **`{current.serial}`"
                                               f"**Sold for: **`${sold_amount * 2} (you got ${sold_amount})`\n"
                                               f"**Sold at: **<t:{transaction_time:.0f}:f>",
                                "url": item.link,
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
                            if response.status == 204:
                                self.sold_items.append((item.id, current.serial))
                            
    async def update_console(self) -> str:
        Tools.clear_console()
        Display.main()
        
        item = self.current_item

        data = {
            "Info": {
                "Discord Bot": define_status(self.discord_bot),
                "Save Items": define_status(self.save_progress),
                "Under Cut": f"-{self.under_cut_amount}{'%' if self.under_cut_type == 'percent' else ''}",
                "Total Blacklist": f"{len(self.blacklist)}"
            },
            "Current Item": {
                "Name": item.name,
                "Creator": item.creator_name,
                "Price": f"{item.price:,}",
                "Quality": f"{item.quantity:,}",
                "Lowest Price": item.define_lowest_resale_price(),
                "Price to Sell": f"{item.price_to_sell:,}",
                "RAP": item.define_recent_average_price(),
                "Latest Sale": item.define_latest_sale()
            }
        }

        Display.sections(data)
        await Display.custom("[1] - Sell | [2] - Set Price | [3] - Blacklist | [4] - Skip\n> ",
                             "input", Display.ainput_color, end="")

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
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        tasks = [
            asyncio.create_task(self.auth.close_session()),
            asyncio.create_task(self.control_panel.service_message.delete()) if self.control_panel is not None else None
        ]
        
        await asyncio.gather(*filter(None, tasks))
    
    def __len__(self):
        return len(self.items)


async def check_for_update(raw_code_url: str) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.get(raw_code_url) as response:
            try:
                version = (await response.text()).strip().split("VERSION = \"")[1].split("\"")[0]
            except IndexError:
                return False

            if version != VERSION:
                return True
            else:
                return False


async def main():
    Display.info("Setting up everything...")
    
    Display.info("Checking for updates")
    code_url = "https://raw.githubusercontent.com/cofiprofim/AutoSeller/refs/heads/main/main.py"
    if await check_for_update(code_url):
        await Display.custom(
            "Your code is outdated. Please update it from github",
            "new", Color(163, 133, 0), exit_after=True)

    Display.info("Loading config")
    config = load_file("config.json")

    Display.info("Loading data assets")
    blacklist = FileSync("blacklist/blacklist.json")
    seen = FileSync("blacklist/seen.json")
    not_resable = FileSync("blacklist/not_resable.json")

    auto_seller = AutoSeller(config, blacklist, seen, not_resable)

    try:
        await auto_seller.start()
    except Exception:
        return Display.exception(f"Unknown error occurred:\n\n{traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())
