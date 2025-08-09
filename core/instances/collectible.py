from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from .item import Item

from ..clients import Auth

__all__ = ("Collectible",)


class Collectible:
    __slots__ = ("_serial", "on_sale", "sale_price",
                 "item_id", "instance_id", "product_id",
                 "skip_on_sale", "item")

    def __init__(
            self,
            serial: int,
            on_sale: Optional[bool] = None,
            sale_price: Optional[int] = None,
            item_id: Optional[int] = None,
            instance_id: Optional[str] = None,
            product_id: Optional[str] = None,
            item: Optional[Item] = None,
            skip_on_sale: Optional[bool] = None
    ) -> None:

        self._serial = serial
        self.on_sale = on_sale
        self.sale_price = sale_price
        self.item_id = item_id
        self.product_id = product_id
        self.instance_id = instance_id

        self.item = item
        self.skip_on_sale = skip_on_sale

    @property
    def serial(self):
        return self._serial

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

    async def sell(self, price: int, auth: Auth) -> Optional[aiohttp.ClientResponse]:
        if None in (self.item_id, self.instance_id, self.product_id) or self.skip_on_sale:
            return None

        payload = {
            "collectibleProductId": self.product_id,
            "isOnSale": True,
            "price": price,
            "sellerId": auth.user_id,
            "sellerType": "User"
        }

        async with auth.patch(
            f"apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/instance/{self.instance_id}/resale",
            json=payload
        ) as response:
            if response.status == 200:
                self.on_sale = True

            return response

    async def take_off_sale(self, auth: Auth) -> Optional[int]:
        if None in (self.item_id, self.instance_id, self.product_id):
            return None

        payload = {
            "collectibleProductId": self.product_id,
            "isOnSale": False,
            "sellerId": auth.user_id,
            "sellerType": "User"
        }

        async with auth.patch(
            f"apis.roblox.com/marketplace-sales/v1/item/{self.item_id}/instance/{self.instance_id}/resale",
            json=payload
        ) as response:
            if response.status == 200:
                self.on_sale = False

            return response.status
