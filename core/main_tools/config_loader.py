from typing import Optional, NoReturn

from ..visuals import Display
from ..utils import is_webhook_exists

__all__ = ("ConfigLoader",)


class ConfigLoader:
    under_cut_types = ("robux", "percent")
    sort_items_types = ("name", "creator", "price")

    def __init__(self, config: dict):
        discord_bot = config["Discord_Bot"]
        self.discord_bot = discord_bot.get("Enabled", False)
        self.bot_token = discord_bot.get("Token", "").strip()
        self.bot_prefix = discord_bot.get("Prefix", "").strip()
        self.owners_list = discord_bot.get("Owner_IDs", [])

        webhooks = config["Webhook"]
        self.user_to_ping = f"<@{webhooks['User_To_Ping']}>" if webhooks.get("User_To_Ping") else ""

        buy_webhook = webhooks["OnBuy"]
        self.buy_webhook_url = buy_webhook.get("Url", "").strip()
        self.buy_webhook = buy_webhook.get("Enabled", False)

        sale_webhook = webhooks["OnSale"]
        self.sale_webhook_url = sale_webhook.get("Url", "").strip()
        self.sale_webhook = sale_webhook.get("Enabled", False)

        auto_sell = config["Auto_Sell"]
        self.auto_sell = not auto_sell.get("Ask_Before_Sell", False)
        self.save_progress = auto_sell.get("Save_Progress", True)
        self.skip_on_sale = auto_sell.get("Hide_OnSale", False)
        self.skip_if_cheapest = auto_sell.get("Skip_If_Cheapest", False)
        self.sort_items_by = auto_sell.get("Sort_Items_By", "name")
        self.keep_serials = auto_sell.get("Keep_Serials", 0)
        self.keep_copy = auto_sell.get("Keep_Copy", 0)
        self.creators_blacklist = auto_sell.get("Creators_Blacklist", [])

        under_cut = auto_sell["Under_Cut"]
        self.under_cut_type = under_cut.get("Type", "percent").strip()
        self.under_cut_amount = under_cut.get("Value", 10)

    async def handle_exceptions(self) -> Optional[NoReturn]:
        if self.discord_bot:
            if not self.bot_token:
                return Display.exception("Invalid discord bot token provided")

            elif not self.bot_prefix:
                return Display.exception("Discord bot prefix can not be empty")

        elif (self.buy_webhook and
              not await is_webhook_exists(self.buy_webhook_url)):
            return Display.exception("Invalid on buy webhook url provided")

        elif (self.sale_webhook and
              not await is_webhook_exists(self.sale_webhook_url)):
            return Display.exception("Invalid on sale webhook url provided")

        elif self.under_cut_type not in self.under_cut_types:
            return Display.exception(f"Invalid under cut type provided, must be: {self.under_cut_types}")

        elif self.sort_items_by not in self.sort_items_types:
            return Display.exception(f"Invalid sort items type provided, must be: {self.sort_items_types}")

        elif self.under_cut_amount < 0:
            return Display.exception("Under cut amount can not be less than 0")
