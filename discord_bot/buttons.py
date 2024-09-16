from discord.ui import View, button, Button, Modal
import traceback
import discord
import asyncio
import json

from .embeds import custom_embed, loading_embed

from typing import Optional


class ControlPanel(View):
    class _SetPricePopup(Modal, title="New Price Set"):
        def __init__(self, button_object):
            super().__init__()

            self.button = button_object

        new_price = discord.ui.TextInput(
            style=discord.TextStyle.short,
            label="Price Set",
            required=True,
            max_length=1000,
            placeholder="Paste here a price to sell this item"
        )

        async def on_submit(self, interaction: discord.Interaction):
            try:
                await interaction.response.defer(ephemeral=True)

                if self.new_price.value.isdigit() and int(self.new_price.value) > 0:
                    self.button.seller.current_asset.price_to_sell = int(self.new_price.value)

                await self.button.update_service_message(self.button.seller.current_asset.make_embed())
            except:
                traceback.print_exc()

    def __init__(self, seller, ctx: discord.Message) -> None:
        super().__init__(timeout=None)

        self.seller = seller

        self.client_message = ctx
        self.service_message = None

    async def start(self):
        self.service_message = await self.client_message.reply(embed=self.seller.current_asset.make_embed(),
                                                               view=self)

    async def update_service_message(self, embed: discord.Embed):
        await self.service_message.edit(embed=embed, view=self)

    def switch_buttons_disabling(self, disabled: Optional[bool] = None):
        for children in self.children:
            if isinstance(children, Button):
                children.disabled = disabled if disabled is not None else not children.disbled

    @button(label="sell", style=discord.ButtonStyle.green, emoji="💲")
    async def sell(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send(embed=custom_embed("No Permission", "You are not allowed to interact with buttons!"),
                                                   ephemeral=True)

        # message = await interaction.followup.send(embed=custom_embed("Selling", f"Selling `{len(self.seller.current_asset.collectibles):,}` items..."),
        #                                           ephemeral=True)

        # sold_amount = 0

        self.switch_buttons_disabling(True)
        await self.update_service_message(embed=loading_embed("Selling Items", f"Selling `{len(self.seller.current_asset.collectibles):,}` items..."))

        try:
            for _ in self.seller.current_asset.collectibles:
                while True:
                    status = await self.seller.current_asset.sell()

                    if status == 200:
                        self.seller.current_asset.next()
                        # sold_amount += 1
                        break
                    elif status == 429:
                        await asyncio.sleep(30)
                    elif status == 403:
                        await self.seller.auth.update_csrf_token()
                    elif status == 412:
                        continue
                    else:
                        self.seller.next_asset.next()
                        break
        except:
            traceback.print_exc()

        if self.seller.sale_webhook_enabled:
            asyncio.create_task(self.seller.send_sale_webhook(self.seller.current_asset))

        if self.seller.save_items:
            self.seller.seen.add(self.seller.current_asset.id)
            with open("items/seen.json", "w") as f: f.write(json.dumps(list(self.seller.seen)))

        self.seller.next_asset()

        self.switch_buttons_disabling(False)
        await self.update_service_message(self.seller.current_asset.make_embed())

        # await asyncio.gather(
        #     message.edit(embed=custom_embed("Done",
        #                                     f"Sold `{sold_amount:,}/{len(self.seller.current_asset.collectibles):,}` items")),
        #     self.update_service_message(self.seller.current_asset.make_embed())
        # )

    @button(label="set price", style=discord.ButtonStyle.gray, emoji="✏️")
    async def set_price(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send(
                embed=custom_embed("No Permission", "You are not allowed to interact with buttons!"),
                ephemeral=True)

        await interaction.response.send_modal(self._SetPricePopup(self))

    @button(label="blacklist", style=discord.ButtonStyle.gray, emoji="📃")
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send(
                embed=custom_embed("No Permission", "You are not allowed to interact with buttons!"),
                ephemeral=True)

        self.seller.blacklist.add(self.seller.current_asset.id)
        with open("items/blacklist.json", "w") as f: f.write(json.dumps(list(self.seller.blacklist)))

        self.seller.next_asset()
        await self.update_service_message(self.seller.current_asset.make_embed())

    @button(label="skip", style=discord.ButtonStyle.primary, emoji="➡️")
    async def skip(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send("You are not allowed to interact with buttons!",
                                                   ephemeral=True)


        if self.seller.save_items:
            self.seller.seen.add(self.seller.current_asset.id)
            with open("items/seen.json", "w") as f: f.write(json.dumps(list(self.seller.seen)))

        self.seller.next_asset()

        await self.update_service_message(self.seller.current_asset.make_embed())
