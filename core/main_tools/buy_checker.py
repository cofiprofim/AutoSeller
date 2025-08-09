from __future__ import annotations

from collections import deque
from datetime import datetime
import discord
import asyncio
import collections

from typing import Optional, List, AsyncGenerator, TYPE_CHECKING

from core.instances import Collectible

if TYPE_CHECKING:
    from main import AutoSeller

from ..detection import get_users_thumbnails, get_recent_sales
from ..instances import Item, Collectible
from ..clients import Auth

__all__ = ("BuyChecker",)


class Transaction:
    def __init__(self, transaction: dict) -> None:
        details = transaction["details"]
        self.item_type = details["type"]
        self.item_id = details["id"]

        self.created_at = datetime.strptime(transaction["created"],
                                            "%Y-%m-%dT%H:%M:%S.%fZ")
        self.sold_for = transaction["currency"]["amount"]

        buyer = transaction["agent"]
        self.buyer_id = buyer["id"]
        self.buyer_name = buyer["name"]

    async def make_embed(self, collectible: Collectible, auth: Auth, user_to_ping: Optional[int] = None) -> dict:
        item = collectible.item

        embed = discord.Embed(
            title="Someone Bought Your Item",
            description=f"**Item name: **`{item.name}`\n"
                        f"**Item Serial: **`{collectible.serial}`"
                        f"**Sold for: **`${self.sold_for * 2} (you got ${self.sold_for})`\n"
                        f"**Sold at: **<t:{self.created_at:.0f}:f>",
            url=item.link,
            timestamp=datetime.now(),
            color=2469096,
        )
        embed.set_footer(text="Was sold at")
        embed.set_thumbnail(url=item.thumbnail)

        buyer_thumbnail = get_users_thumbnails((self.buyer_id,), auth)
        embed.set_author(name=self.buyer_name,
                         url=f"https://www.roblox.com/users/{self.buyer_id}/profile",
                         icon_url=buyer_thumbnail)

        data = {
            "content": user_to_ping,
            "embeds": [embed.to_dict()]
        }

        return data


class BuyChecker:
    def __init__(self, seller: AutoSeller, *, interval: Optional[int] = 10) -> None:
        self._seller = seller
        self.interval = interval
        self.sold_items = collections.deque(maxlen=10)

    async def start(self):
        while True:
            await asyncio.sleep(self.interval)
            new_sales = self._fetch_new_sales()

            async for sale, col in new_sales:
                await self.send_webhook(col, sale)

    async def _fetch_existing_sales(self) -> AsyncGenerator[Transaction]:
        sales = [Transaction(sale) for sale in await get_recent_sales(self._seller.auth)]

        for sale in sales:
            if (
                sale.item_type != "Asset"
                or sale.created_at < self._seller.loaded_time
            ):
                continue

            item = self._seller.get_item(sale.item_id)
            if item is None:
                continue

            yield sale

    async def _fetch_new_sales(self) -> AsyncGenerator[tuple[Transaction, Collectible]]:
        async for sale in self._fetch_existing_sales():
            item = self._seller.get_item(sale.item_id)

            old_collectibles = item.collectibles.copy()
            await item.fetch_collectibles()

            for col in old_collectibles:
                current = item.get_collectible(col.serial)

                if (
                    current is None
                    or any(col.item.id == item.id and col.serial == current.serial
                           for col in self.sold_items)
                ):
                    continue

                yield sale, current

    async def send_webhook(self, collectible: Collectible, transaction: Transaction) -> None:
        embed = transaction.make_embed(collectible, self._seller.auth, user_to_ping=self._seller.user_to_ping)

        async with self._seller.auth.post(self._seller.buy_webhook_url, json=embed) as response:
            if response.status == 204:
                self.sold_items.append(collectible)

            elif response.status == 429:
                await asyncio.sleep(30)
                await self.send_webhook(collectible, transaction)
