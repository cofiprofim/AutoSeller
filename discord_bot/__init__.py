from __future__ import annotations

import traceback

from discord.ext.commands import Bot, BadArgument, CommandNotFound, MissingRequiredArgument
from discord import app_commands, Intents

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import AutoSeller


from discord_bot.visuals.view import *
from discord_bot.visuals.embeds import *
from discord_bot.utils.decorators import *


async def start(self: AutoSeller) -> None:
    bot = Bot(command_prefix=self.bot_prefix, intents=Intents.all())

    @bot.event
    async def on_ready():
        await bot.tree.sync()
    
    @bot.event
    async def on_message_delete(message: discord.Message) -> None:
        if message == self.control_panel:
            self.control_panel = None

    @bot.hybrid_command(name="start", description="Starts selling limiteds")
    @app_commands.describe(channel="The channel to send a control panel to")
    @users_blacklist(self.owners_list, message="You don't have permission to use this command!")
    @base_command
    async def start_command(ctx: discord.Message, channel: discord.TextChannel = None):
        channel = (channel or ctx.channel)

        if self.auto_sell:
            return await ctx.reply(content=f"You can not run this command when you have auto sell enabled")
        elif self.control_panel is not None:
            return await ctx.reply(content=f"You already have one control panel running! "
                                           f"({self.control_panel.message.jump_url})")

        await ControlPanel(self, channel, ctx).start()
        return await ctx.reply(f"Successfully created a control panel {self.control_panel.service_message.jump_url}")

    @bot.event
    async def on_command_error(ctx: discord.Message, exception: Exception):
        if type(exception) in (BadArgument, CommandNotFound, MissingRequiredArgument):
            return None

        await ctx.reply(embed=exception_embed(traceback.format_exc()))

    await bot.start(self.bot_token)
