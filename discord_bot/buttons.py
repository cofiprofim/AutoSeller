from discord.ui import View, button, Button, Modal
from datetime import datetime
import traceback
import discord
import asyncio
import json

from .embeds import custom_embed, loading_embed
# from core.utils import TasksManager

from typing import Optional


class ControlPanel(View):
    class _SetPricePopup(Modal, title="New Price Set"):
        def __init__(self, button_object):
            super().__init__(timeout=None)

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

                await self.button.update_service_message(self.button.make_embed())
            except:
                traceback.print_exc()

    def __init__(self, seller, ctx: discord.Message) -> None:
        super().__init__(timeout=None)

        self.seller = seller

        self.client_message = ctx
        self.service_message = None

    async def start(self):
        self.service_message = await self.client_message.reply(embed=self.make_embed(),
                                                               view=self)
        self.seller.control_panel = self.service_message

    async def update_service_message(self, embed: discord.Embed):
        await self.service_message.edit(embed=embed, view=self)

    def switch_buttons_disabling(self, disabled: Optional[bool] = None):
        for children in self.children:
            if isinstance(children, Button):
                children.disabled = disabled if disabled is not None else not children.disabled
    
    def make_embed(self) -> discord.Embed:
        item = self.seller.current_asset
        
        embed = discord.Embed(title=item.name,
                              url=item.link,
                              timestamp=datetime.now(),
                              color=2469096,
                              description=f"Sell this item for `{item.price_to_sell:,}` robux")

        embed.add_field(name=f"Lowest Resale Price", value=f"`{item.lowest_resale_price:,}`" if item.has_resales is True else "`No Resales`", inline=True)
        embed.add_field(name=f"Latest Sale", value=f"`{item.latest_sale:,}`" if item.latest_sale is not None else "`N/A`", inline=True)
        embed.add_field(name=f"RAP", value=f"`{item.recent_average_price:,}`" if item.recent_average_price is not None else "`N/A`", inline=True)
        embed.add_field(name=f"Price", value=f"`{item.price:,}`", inline=True)
        embed.add_field(name=f"Quantity", value=f"`{item.quantity:,}`", inline=True)

        embed.set_author(name=item.creator_name, url=item.creator_link)
        embed.set_thumbnail(url=item.thumbnail)

        embed.set_footer(text=f"Viewing {self.seller.current_index + 1}/{len(self.seller.items) + 1}")

        return embed

    @button(label="sell", style=discord.ButtonStyle.green, emoji="💲", row=2)
    async def sell(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send(embed=custom_embed("No Permission", "You are not allowed to interact with buttons!"),
                                                   ephemeral=True)

        self.switch_buttons_disabling(True)
        await self.update_service_message(embed=loading_embed(f"Selling {len(self.seller.current_asset. collectibles):,} Items"))
        
        # Too complicated, maybe will add this next time
        
        # sold_amount = 0
        # resable = True
        
        # tasks = TasksManager()
        # try:
        #     await self.seller.current_asset.fetch_collectibles()
            
        #     for col in self.seller.current_asset.collectibles.values():
        #         if resable == False:
        #             break
                
        #         tries = 0
                
        #         if col.sale_price == self.seller.current_asset.price_to_sell:
        #             tasks.add_skip(f"This collectible is already on sale for the same price `(#{col.serial})`")
        #             asyncio.create_task(self.update_service_message(loading_embed(f"Selling {len(self.seller.current_asset.collectibles):,} Items", tasks.tasks)))
        #             continue
        #         elif col.on_sale and self.seller.hide_on_sale:
        #             tasks.add_skip(f"This collectible is already on sale `(#{col.serial})`")
        #             asyncio.create_task(self.update_service_message(loading_embed(f"Selling {len(self.seller.current_asset.collectibles):,} Items", tasks.tasks)))
        #             continue
                
        #         while True:
        #             status = await col.sell(self.seller.current_asset.price_to_sell)

        #             match status:
        #                 case 200:
        #                     tasks.add_success(f"Successfully sold for `${self.seller.current_asset.price_to_sell:,}` `(#{col.serial})`")
        #                     asyncio.create_task(self.update_service_message(loading_embed(f"Selling {len(self.seller.current_asset.collectibles):,} Items", tasks.tasks)))

        #                     sold_amount += 1
        #                     break
        #                 case 429:
        #                     tasks.add_error("You got ratelimited! Trying again in 30 seconds...`")
        #                     asyncio.create_task(self.update_service_message(loading_embed(f"Selling {len(self.seller.current_asset.collectibles):,} Items", tasks.tasks)))

        #                     tries += 1
        #                     await asyncio.sleep(30)
        #                 case 403:
        #                     tasks.add_error("Your token got updated. Getting a new one...")
        #                     asyncio.create_task(self.update_service_message(loading_embed(f"Selling {len(self.seller.current_asset.collectibles):,} Items", tasks.tasks)))
                            
        #                     await self.auth.update_csrf_token()
        #                 case 412:
        #                     tasks.add_skip("Item is not resable. Skipping it")
        #                     asyncio.create_task(self.update_service_message(loading_embed(f"Selling {len(self.seller.current_asset.collectibles):,} Items", tasks.tasks)))
                            
        #                     resable = False
        #                     sold_amount = False
                            
        #                     break
        #                 case _:
        #                     tasks.add_error(f"Failed to sell limited ({status})")
        #                     asyncio.create_task(self.update_service_message(loading_embed(f"Selling {len(self.seller.current_asset.collectibles):,} Items", tasks.tasks)))

        #                     tries += 1
        #                     await asyncio.sleep(3)

        #             if tries > 3:
        #                 break
            
        #     sold_amount = await self.seller.current_asset.sell_collectibles(skip_on_sale=self.hide_on_sale, log=False)
        #     if sold_amount is None:
        #         self.seller.current_asset.resable = False
        #     else:
        #         self.seller.current_asset.resable = True
        #         self.seller.total_sold += sold_amount

        #     if self.seller.sale_webhook_enabled:
        #         asyncio.create_task(self.seller.send_sale_webhook(self.seller.current_asset))
        #     if self.seller.save_items:
        #         self.seller.seen.add(self.seller.current_asset.id)
        #         with open("items/seen.json", "w") as f: f.write(json.dumps(list(self.seller.seen)))

        #     self.seller.next_asset()

        #     try:
        #         asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_resales(save_resales=False))
        #         asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_sales(save_sales=False))
        #     except IndexError:
        #         pass
            
        # except Exception as err:
        #     tasks.add_error(f"`Unknown error occurred: {err}`")
        #     asyncio.create_task(self.update_service_message(loading_embed(f"Selling {len(self.seller.current_asset.collectibles):,} Items", tasks.tasks)))
        
        try:
            sold_amount = await self.seller.current_asset.sell_collectibles(skip_on_sale=self.seller.hide_on_sale)
            if sold_amount is None:
                self.seller.not_resable.add(self.seller.current_asset.id)
                with open("items/not_resable.json", "w") as f:
                    f.write(json.dumps(list(self.seller.not_resable)))
            else:
                self.seller.total_sold += sold_amount

                if self.seller.sale_webhook_enabled:
                    asyncio.create_task(self.seller.send_sale_webhook(self.seller.current_asset))
            
            if self.seller.save_items:
                self.seller.seen.add(self.seller.current_asset.id)
                with open("items/seen.json", "w") as f: f.write(json.dumps(list(self.seller.seen)))
        except:
            pass
        
        self.seller.next_asset()
        
        try:
            asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_resales(save_resales=False))
            asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_sales(save_sales=False))
        except IndexError:
            pass
        
        self.switch_buttons_disabling(False)
        await self.update_service_message(self.make_embed())

    @button(label="set price", style=discord.ButtonStyle.gray, emoji="✏️", row=1)
    async def set_price(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send(
                embed=custom_embed("No Permission", "You are not allowed to interact with buttons!"),
                ephemeral=True)

        await interaction.response.send_modal(self._SetPricePopup(self))

    @button(label="blacklist", style=discord.ButtonStyle.gray, emoji="📃", row=1)
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send(
                embed=custom_embed("No Permission", "You are not allowed to interact with buttons!"),
                ephemeral=True)

        self.seller.blacklist.add(self.seller.current_asset.id)
        with open("items/blacklist.json", "w") as f: f.write(json.dumps(list(self.seller.blacklist)))

        self.seller.next_asset()
        
        try:
            asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_resales(save_resales=False))
            asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_sales(save_sales=False))
        except IndexError:
            pass
        
        await self.update_service_message(self.make_embed())
    
    @button(label="stop", style=discord.ButtonStyle.danger, emoji="⛔", row=2)
    async def stop(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send("You are not allowed to interact with buttons!",
                                                ephemeral=True)

        await self.service_message.delete()
        self.seller.control_panel = None

    @button(label="skip", style=discord.ButtonStyle.blurple, emoji="➡️", row=2)
    async def skip(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send("You are not allowed to interact with buttons!",
                                                   ephemeral=True)

        self.seller.next_asset()
        
        try:
            asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_resales(save_resales=False))
            asyncio.create_task(self.seller.items[self.seller.current_index + 1].fetch_sales(save_sales=False))
        except IndexError:
            pass

        await self.update_service_message(self.make_embed())
