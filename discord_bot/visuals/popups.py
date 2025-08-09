from __future__ import annotations

from discord.ui import Modal, TextInput
import discord

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .view import ControlPanel


class SetPricePopup(Modal, title="New Price Set"):
    def __init__(self, view: ControlPanel):
        super().__init__(timeout=None)

        self.view = view

    new_price = TextInput(
        style=discord.TextStyle.short,
        label="Price Set",
        required=True,
        max_length=1000,
        placeholder="Paste here a price to sell this item"
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if self.new_price.value.isdigit() and int(self.new_price.value) > 0:
            self.view.seller.current.price_to_sell = int(self.new_price.value)

        await self.view.update_message(self.view.make_embed())
