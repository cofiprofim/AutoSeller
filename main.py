import sys
import os

__import__("warnings").filterwarnings("ignore")

try:
    import discord
    import aioconsole
    import asyncio
    import collections
    from rgbprint import Color
    from datetime import datetime
    from traceback import format_exc

    from typing import List, Optional, Any, Union, AsyncGenerator, Iterable
    from discord.errors import LoginFailure
    from asyncio import Task

    from core.instances import *
    from core.main_tools import *
    from core.clients import *
    from core.visuals import *
    from core.detection import *
    from core.utils import *
    from core.constants import VERSION, RAW_CODE_URL, ITEM_TYPES
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

__all__ = ("AutoSeller",)


class AutoSeller(ConfigLoader):
    __slots__ = ("config", "_items", "auth", "buy_checker", "blacklist",
                 "seen", "not_resable", "current_index", "done",
                 "total_sold", "selling", "loaded_time", "control_panel")

    def __init__(self,
                 config: dict,
                 blacklist: FileSync,
                 seen: FileSync,
                 not_resable: FileSync) -> None:
        super().__init__(config)
        
        self.config = config

        self._items = dict()
        self.auth = Auth(config.get("Cookie", "").strip())
        self.buy_checker = BuyChecker(self)

        self.blacklist = blacklist
        self.seen = seen
        self.not_resable = not_resable

        self.current_index = 0
        self.done = False
        self.total_sold = 0
        self.selling = WithBool()
        self.loaded_time = None
        self.control_panel = None

    @property
    def items(self) -> List[Item]:
        return list(self._items.values())

    @property
    def current(self) -> Item:
        return self.items[self.current_index]

    def get_item(self, _id: int, default: Optional[Any] = None) -> Union[Item, Any]:
        return self._items.get(item, default)

    def add_item(self, item: Item) -> Item:
        self._items.update({item.id: item})
        return item

    def remove_item(self, _id: int) -> Item:
        return self._items.pop(item)

    def next_item(self, *, step_index: int = 1) -> None:
        self.current_index = (self.current_index + 1) % len(self.items)

        if not self.current_index:
            self.done = True

        self.fetch_item_info(step_index=step_index)

    def fetch_item_info(self, *,
                        fetch_sales: bool = True,
                        fetch_resales: bool = True,
                        step_index: int = 1) -> Optional[Iterable[Task]]:
        try:
            item = self.items[self.current_index + step_index]
        except IndexError:
            return None

        tasks = (
            asyncio.create_task(item.fetch_sales(save_sales=False)) if fetch_sales else None,
            asyncio.create_task(item.fetch_resales(save_resales=False)) if fetch_resales else None
        )

        return filter(None, tasks)

    def sort_items(self, _type: str) -> None:
        self._items = dict(sorted(self._items.items(), key=lambda x: getattr(x[1], _type)))

    async def start(self):
        await asyncio.gather(self.auth.fetch_csrf_token(),
                             self.handle_exceptions())

        Display.info("Checking cookie to be valid")
        if await self.auth.fetch_user_info() is None:
            return Display.exception("Invalid cookie provided")

        Display.info("Checking premium owning")
        if not await self.auth.fetch_premium():
            return Display.exception("You dont have premium to sell limiteds")

        await self._load_items()
        self.sort_items("name")

        try:
            async with self:
                tasks = (
                    discord_bot_start(self) if self.discord_bot else None,
                    self.buy_checker.start() if self.buy_webhook else None,
                    self.auth.csrf_token_updater(),
                    self.start_selling()
                )
                await asyncio.gather(*filter(None, tasks))
        except LoginFailure:
            return Display.exception("Invalid discord token provided")
        except Exception:
            return Display.exception(f"Unknown error occurred:\n\n{format_exc()}")

    async def start_selling(self):
        for i in range(2):
            for task in self.fetch_item_info(step_index=i):
                await task

        if self.auto_sell: await self._auto_sell_items()
        else: await self._manual_selling()

        Tools.clear_console()
        await Display.custom(
            f"Sold [g{self.total_sold}x] items",
            "done", Color(207, 222, 0))

        clear_items = await Display.input(f"Do you want to reset your selling progress? (Y/n): ")

        if clear_items.lower() == "y":
            self.seen.clear()
            Display.success("Cleared your limiteds selling progress")
            Tools.exit_program()

    async def sell_item(self):
        await Display.custom(
            f"Selling [g{len(self.current.collectibles)}x] of [g{self.current.name}] items...",
            "selling", Color(255, 153, 0))

        sold_amount = await self.current.sell_collectibles(
            skip_on_sale=self.skip_on_sale,
            skip_if_cheapest=self.skip_if_cheapest,
            log=True
        )
        if sold_amount is None:
            self.not_resable.add(self.current.id)
        else:
            self.total_sold += sold_amount

            if self.sale_webhook and sold_amount > 0:
                asyncio.create_task(self.send_sale_webhook(self.current, sold_amount))

        if self.save_progress:
            self.seen.add(self.current.id)

        self.next_item()

    async def _auto_sell_items(self):
        while not self.done:
            await self.sell_item()
            await asyncio.sleep(0.5)

    async def _manual_selling(self):
        while not self.done:
            await self.update_console()
            choose = (await aioconsole.ainput()).strip()

            match choose:
                case "1":
                    if self.selling:
                        Display.error("This item is already being sold")
                        await asyncio.sleep(0.7)
                        continue

                    with self.selling:
                        await self.sell_item()

                        if self.control_panel is not None:
                            asyncio.create_task(self.control_panel.update_service_message(self.control_panel.make_embed()))
                case "2":
                    new_price = await Display.input(f"Enter the new price you want to sell: ")

                    if not new_price.isdigit():
                        Display.error("Invalid price amount was provided")
                        await asyncio.sleep(0.7)
                        continue
                    elif int(new_price) < 0:
                        Display.error("Price can not be lower than 0")
                        await asyncio.sleep(0.7)
                        continue

                    self.current.price_to_sell = int(new_price)

                    Display.success(f"Successfully set a new price to sell! ([g${self.current.price_to_sell}])")
                case "3":
                    self.blacklist.add(self.current.id)
                    self.next_item()

                    Display.success(f"Successfully added [g{self.current.name} ({self.current.id})] into a blacklist!")
                case "4":
                    if self.save_progress:
                        self.seen.add(self.current.id)

                    self.next_item()
                    Display.skipping(
                        f"Skipped [g{len(self.current.collectibles)}x] collectibles")
                case _:
                    continue

            await asyncio.sleep(0.7)

    async def __fetch_items(self) -> AsyncGenerator:
        Display.info("Loading your inventory")
        user_items = await AssetsLoader(get_user_inventory, ITEM_TYPES.keys()).load(self.auth)
        if not user_items:
            Display.exception("You dont have any limited UGC items")

        item_ids = [str(asset["assetId"]) for asset in user_items]

        Display.info("Loading items thumbnails")
        items_thumbnails = await AssetsLoader(get_assets_thumbnails, item_ids, 100).load(self.auth)

        Display.info(f"Found {len(user_items)} items. Checking them...")
        items_details = await AssetsLoader(get_items_details, item_ids, 120).load(self.auth)

        for item_info in zip(user_items, items_details, items_thumbnails):
            yield item_info

    async def _load_items(self) -> None:
        if self.loaded_time is not None:
            return Display.exception("You have already loaded items")

        Display.info("Getting current limiteds cap")
        items_cap = await get_current_cap(self.auth)

        ignored_items = list(self.seen | self.blacklist | self.not_resable)

        async for item, item_details, thumbnail in self.__fetch_items():
            item_id = item["assetId"]

            if (
                item_id in ignored_items
                or item_details["creatorTargetId"] in self.creators_blacklist
            ):
                continue

            item_obj = self.get_item(item_id)

            if item_obj is None:
                asset_cap = items_cap[ITEM_TYPES[item_details["assetType"]]]["priceFloor"]
                sell_price = define_sale_price(self.under_cut_amount, self.under_cut_type,
                                               asset_cap, item_details["lowestResalePrice"])

                item_obj = Item(
                    item, item_details,
                    price_to_sell=sell_price,
                    thumbnail=thumbnail,
                    auth=self.auth
                )
                self.add_item(item_obj)

            item_obj.add_collectible(
                serial=item["serialNumber"],
                item_id=item["collectibleItemId"],
                instance_id=item["collectibleItemInstanceId"]
            )

        if not self.items:
            Display.error(f"You dont have any limiteds that are not in[g blacklist/] directory")
            clear_items = await Display.input(f"Do you want to reset your selling progress? (Y/n): ")

            if clear_items.lower() == "y":
                self.seen.clear()
                Display.success("Cleared your limiteds selling progress")
                Tools.exit_program()

        if self.keep_serials or self.keep_copy:
            for item in self.items:
                if len(item.collectibles) <= self.keep_copy:
                    self.remove_item(item.id)
                    continue

                for col in item.collectibles:
                    if col.serial > self.keep_serials:
                        col.skip_on_sale = True

        if not self.items:
            not_met = []

            if self.keep_copy: not_met.append(f"{self.keep_copy} copies or higher")
            if self.keep_serials: not_met.append(f"{self.keep_serials} serial or higher")

            list_requirements = ", ".join(not_met)
            return Display.exception(f"You dont have any limiteds with {list_requirements}")

        self.loaded_time = datetime.now()

    async def update_console(self) -> None:
        Tools.clear_console()
        Display.main()

        item = self.current

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
                             "input", BaseColors.gray, end="")
    
    async def send_sale_webhook(self, item: Item, sold_amount: int) -> None:
        embed = discord.Embed(
            color=2469096,
            timestamp=datetime.now(),
            description=f"**Item name: **`{item.name}`\n"
                        f"**Sold amount: **`{sold_amount}`\n"
                        f"**Sold for: **`{item.price_to_sell}`",
            title="A New Item Went on Sale",
            url=item.link
        )
        embed.set_footer(text="Were sold at")
        
        data = {
            "content": self.user_to_ping,
            "embeds": [embed.to_dict()]
        }

        async with ClientSession() as session:
            async with session.post(self.sale_webhook_url, json=data) as response:
                if response.status == 429:
                    await asyncio.sleep(30)
                    await self.send_sale_webhook(item, sold_amount)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        tasks = (
            self.auth.close_session(),
            self.control_panel.service_message.delete() if self.control_panel else None
        )

        await asyncio.gather(*filter(None, tasks))


async def main():
    Display.info("Setting up everything...")

    Display.info("Checking for updates")
    if await check_for_update(RAW_CODE_URL, VERSION):
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
    except:
        return Display.exception(f"Unknown error occurred:\n\n{format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())


    ___     __      ___       _  _       _  _          _    _         _         ___          _  _       ____       ___        ____   
   F _ ",   FJ     F __".    FJ  L]     F L L]        F L  J J       /.\       F __".       FJ  L]     F ___J     F _ ",     F ___J  
  J `-' |  J  L   J (___|   J |  | L   J   \| L      J J .. L L     //_\\     J (___|      J |__| L   J |___:    J `-'(|    J |___:  
  |  __/F  |  |   J\___ \   | |  | |   | |\   |      | |/  \| |    / ___ \    J\___ \      |  __  |   | _____|   |  _  L    | _____| 
  F |__/   F  J  .--___) \  F L__J J   F L\\  J      F   /\   J   / L___J \  .--___) \     F L__J J   F L____:   F |_\  L   F L____: 
 J__|     J____L J\______J J\______/F J__L \\__L    J___//\\___L J__L   J__L J\______J    J__L  J__L J________L J__| \\__L J________L
 |__L     |____|  J______F  J______F  |__L  J__|    |___/  \___| |__L   J__|  J______F    |__L  J__| |________| |__|  J__| |________|
                                                                                                                                     

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%#**##***%%%%%%%%%%%%%%%%%%%%%%%%%@@@@@@@@@@@@@@@@@@@@@@@@@@@
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%##*+=-:::::::::-----=+*##%%%%%%%%%%%%%%%%@@@@@@@@@@@@@@@@@@@@@@@
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%##+=--:::::::::::::::::::::::::-+*##%%%%%%%%%%%%%@@@@@@@@@@@@@@@@@@@@
%%%%%%%%%%%%%%%%%%%%%%%%%%#**+=-:::::::::::::::::::::::::::::::::::-=**#%%%%%%%%%%%%%%@@@@@@@@@@@@@%
######%%%%%%%%%%%%%%%%%##+=-:::::::::::::::::::::::::::::::::::::::::::=*#%%%%%%%%%%%%%%%%%%%%%%%%%%
##########%%%%%%%%###*+=-::::::::::::::::::::::::::::::::::::::::::::::::-*#%%%%%%%%%%%%%%%%%%%%%%%%
##############%%###+=----::::::::::::::::::::::::::::::::::::::::::::::::::-*#%%%%%%%%%%%%%%%%%%%%%%
#################*=------------:----:::::::::::::::::::::::::::::::::::::::::-*#%%%%%%%%%%%%%%%%%%%%
################*+=------------------------------:::::::::::::::::::::::::::::-*#%%%%%%%%%%%%%%%%%%%
##############+=====------------------------------:::::::::::::::::::::::::::::=##%%%%%%%%%%%%%%%%%%
############*=----===--------------=======------------:::::::::::::::::::::::::-*###%%%%%%%%%%%%%%%%
##########*+------====-------===================---------::----:::::---::::::::-+######%%%%%%%%%%%%%
#########*=--------====-===========+++++++****++===------------------=---:::::::=*#########%%%%%%%%%
########+--------============+++++++++*###%@@@%#*+=====--------=++======---:::::=*###########%%%%%%%
#######+=--------=============+++++++++%%%@@@@@@@#**++===-----=*#==+++===---:::-+*##############%%%%
######+=---------=====------===========+*#%@@@@@@@@%%#**+++++*%@%#*##*++====---=+**##############%%%
#####*==---------====------------=========+*#%%%%%%%%%#*******#%@@%%#**++++====--=+*################
####*+==--------=====--------------=============+=++++*****#######%%#####***++===-=+***#############
###*+===--------=====----------------================++*#%###%%###*******###**++===--+***###########
##*====--------=====-------------------================+##**#######%%%%#####***++==--=+****#########
##*======------====----==-=======------=================+**######%%%%%%%%%%%%%%#*#*=::-=+***########
##+=======---======--------------==------=======------====++****###%%%%%##%%%@@%#+=-:::-+****#######
#*+===============----------------==--------------=----====++***###%%%%%%%%#+--:::::::::-+****######
#*+=========+=====------=====-------------------==--------===+****#**++----::::::::::::::-+*****####
*+====================------------------------==----------===+++++++==----::::::::::::::::-+*****###
+=========++++=========--=-----=--------------===----------=+++=======---:::::::::::::::::-=******##
+==+++===+*++==--===============-----------------==---------++==+====-----:::::::::::::::::-+******#
++++++++++*+++=====================----======---==----------====+==-----::::::::::::::::::::=+*****#
+++=====++++++=+==================================--==---------====----:::::::::::::::::::::-+******
++++====++**+++++++======++====++===============----==----------===----:::::::::::::::::::::-=+*****
+++++++++****+==++++=====+++==++++===============-====-----------------:::::::::::::::::::::-=+*****
**++++++****++++++++=======+++=+++========++===========----------------::::::::::::::::::::::=+*****
**+*********++=++++++=======++++++=======================---------------::::::::::::::::::::-=++****
**++++*+*****++*++*++++==========+================----=====-------------::::::::::::::::::::-=+*****
**++++++*##***+++++=+++++=================---=======----===--------------::::::::::--::::::::=+*****
********###***++==+++=++++======+=========-=---===---------=--------------:::::::::--:::::::-=+*****
***+*****###**+++++=+==++++========++=+++====--===--===----==-------------::::::::--::::::::-++*****
*********#####*+++*+++++++++==========++++=========-------------------------::-::--::::::::-=+******
*********######++*+++++=++=+=========================------------------------------:::::::--+++*****
*********######*****++++++++++++======================-----------------------------:::::::-=++++****
*******#########******+*+=+++++++++=++=++====================---------------------:::::::-=++++++***
*****############*+******+++++++++++++==+====================-------------------------:::-=+++++++**
******############***#***++===+==+==+==========================-----------------------:--=+++++++++*
******#############**##****+==+++++++====+++++===-==============------------------------=+++++++++++
*******##########%%#****##****++++++++=+=+++=+==============---===---------------------=++++++++++++
********###%%%%###%%%##*********++++++++++++==+====================---==--------------=+++++++++++++
**********#%%%%%%#%%%%%##***+****+++++++==+++===----======+++++========-------------=+++++++++++++++
***********##%%%%%%#%%%%%%####*****++++*++=+++++=======+++++++=====----======-----==++++++++++++++++
************##%%%%%%%#%%%%%%%%######******++**++******+++++++=====----====-----===++++++++++++++*+++
**************#%%%%%%%%%%%%%%%%%%%%%%%#########*#**#**+++++=+===================+++++++++++++++*****
*********####**##%%%%%%%%%%%%%%%%%%%%%%%%%%%###***++++++==++==++==============+++++++++*************
###################%%%@@@%%%%%%%##########*******++++++=++++++++++=========+++**********************
%%%%%%%%%%%#%%%#%%%%%%%%@@@@@@@@%%##%##*##*****##**++++++++***++++++++++++**************************
%%%%%%%%%%%%%%%%%%%%%%%%%%@@@@@@@@@@%%%%%@%########***************++++****************************##
%%%%%%%%%%%%%%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%%%%%%%%%%##########********************************###
