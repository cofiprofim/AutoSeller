from __future__ import annotations

from discord.ui import View, button, Button
from datetime import datetime
import discord
import asyncio

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from main import AutoSeller

from discord_bot.visuals.embeds import custom_embed, loading_embed
from discord_bot.visuals.popups import SetPricePopup


class BaseView(View):
    def __init__(self, seller: AutoSeller, channel: discord.TextChannel, ctx: discord.Message):
        super().__init__(timeout=None)

        self.seller = seller
        self.channel = channel

        self.client_message = ctx
        self.service_message = None

    def switch_buttons_disabling(self, disabled: Optional[bool] = None):
        for children in self.children:
            if isinstance(children, Button):
                children.disabled = (not children.disabled) if disabled is None else disabled

    async def update_service_message(self, embed: discord.Embed):
        await self.service_message.edit(embed=embed, view=self, content=self.client_message.author.mention)


class ControlPanel(BaseView):
    async def start(self):
        self.service_message = await self.channel.send(embed=self.make_embed(),
                                                       view=self,
                                                       content=self.client_message.author.mention)

        self.seller.control_panel = self

    def make_embed(self) -> discord.Embed:
        item = self.seller.current
        
        embed = discord.Embed(title=item.name,
                              url=item.link,
                              timestamp=datetime.now(),
                              color=2469096,
                              description=f"Sell this item for `{item.price_to_sell:,}` robux")

        embed.add_field(name=f"Lowest Resale Price",
                        value=f"`{item.define_lowest_resale_price()}`",
                        inline=True)
        embed.add_field(name=f"Latest Sale",
                        value=f"`{item.define_latest_sale()}`",
                        inline=True)
        embed.add_field(name=f"RAP",
                        value=f"`{item.define_recent_average_price()}`",
                        inline=True)
        
        embed.add_field(name=f"Price", value=f"`{item.price:,}`", inline=True)
        embed.add_field(name=f"Quantity", value=f"`{item.quantity:,}`", inline=True)

        embed.set_author(name=item.creator_name, url=item.creator_link)
        embed.set_thumbnail(url=item.thumbnail)

        embed.set_footer(text=f"Viewing {self.seller.current_index + 1}/{len(self.seller.items) + 1}")

        return embed

    @button(label="sell", style=discord.ButtonStyle.green, emoji="💲", row=2)
    async def sell_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id == self.client_message.author.id:
            return await interaction.followup.send(embed=custom_embed("No Permission",
                                                                      "You are not allowed to interact with buttons!"),
                                                   ephemeral=True)

        self.switch_buttons_disabling(True)
        await self.update_service_message(embed=loading_embed(f"Selling {len(self.seller.current.collectibles):,} Items"))
        await interaction.response.defer(ephemeral=True)
        
        if not self.seller.selling:
            with self.seller.selling:
                sold_amount = await self.seller.current.sell_collectibles(
                    skip_on_sale=self.seller.skip_on_sale,
                    skip_if_cheapest=self.seller.skip_if_cheapest,
                    log=False
                )

                if sold_amount is None:
                    self.seller.not_resable.add(self.seller.current.id)
                else:
                    self.seller.total_sold += sold_amount

                    if self.seller.sale_webhook and sold_amount > 0:
                        asyncio.create_task(self.seller.send_sale_webhook(self.seller.current, sold_amount))

                if self.seller.save_progress:
                    self.seller.seen.add(self.seller.current.id)
                
                self.seller.next_item()
                await self.seller.update_console()
                
                if self.seller.done:
                    self.switch_buttons_disabling(False)
                    return await self.update_service_message(
                        embed=custom_embed("Done", f"Successfully sold {self.seller.total_sold} limiteds"))
        
        self.switch_buttons_disabling(False)
        return await self.update_service_message(self.make_embed())

    @button(label="set price", style=discord.ButtonStyle.gray, emoji="✏️", row=1)
    async def set_price_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send(
                embed=custom_embed("No Permission", "You are not allowed to interact with buttons!"),
                ephemeral=True)

        await interaction.response.send_modal(SetPricePopup(self))

    @button(label="blacklist", style=discord.ButtonStyle.gray, emoji="📃", row=1)
    async def next_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send(
                embed=custom_embed("No Permission", "You are not allowed to interact with buttons!"),
                ephemeral=True)

        self.seller.blacklist.add(self.seller.current.id)
        self.seller.next_item()
        
        await self.update_service_message(self.make_embed())
        await interaction.response.defer(ephemeral=True)
    
    @button(label="stop", style=discord.ButtonStyle.danger, emoji="⛔", row=2)
    async def stop_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send("You are not allowed to interact with buttons!",
                                                   ephemeral=True)

        await self.service_message.delete()
        self.seller.control_panel = None

    @button(label="skip", style=discord.ButtonStyle.blurple, emoji="➡️", row=2)
    async def skip_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.client_message.author.id:
            return await interaction.followup.send("You are not allowed to interact with buttons!",
                                                   ephemeral=True)

        self.seller.seen.add(self.seller.current.id)
        self.seller.next_item()

        await self.update_service_message(self.make_embed())
        await interaction.response.defer(ephemeral=True)
