from traceback import format_exc
from discord.ext import commands
from discord import app_commands
import discord

from .buttons import ControlPanel
from .embeds import exception_embed, custom_embed


async def start(self):
    bot = commands.Bot(command_prefix=self.bot_prefix, intents=discord.Intents.all())

    @bot.event
    async def on_ready():
        await bot.tree.sync()
    
    @bot.event
    async def on_message_delete(message: discord.Message) -> None:
        if message == self.control_panel:
            self.control_panel = None
    
    @bot.hybrid_command(name="start", description="Starts selling limiteds")
    @app_commands.describe(channel="The channel to send a control panel to")
    async def start_command(ctx: discord.Message, channel: discord.TextChannel = None) -> None:
        try:
            await ctx.defer()
            
            channel = (channel or ctx.channel)
            
            if self.owners_list and ctx.author.id not in self.owners_list:
                return await ctx.reply(content="You don't have permission to use this command!")
            elif self.auto_sell:
                return await ctx.reply(content=f"You can not run this command when you have auto sell enabled")
            elif self.control_panel is not None:
                return await ctx.reply(content=f"You already have one control panel running! {self.control_panel.service_message.jump_url}")
            
            await ControlPanel(self, channel, ctx).start()
            return await ctx.reply(f"Successfully created a control panel {self.control_panel.service_message.jump_url}")
        except:
            return await ctx.reply(embed=exception_embed(format_exc()))

    @bot.event
    async def on_command_error(ctx: discord.Message, exception: Exception) -> None:
        if type(exception) in (commands.BadArgument, commands.CommandNotFound, commands.MissingRequiredArgument):
            return None

        await ctx.reply(embed=exception_embed(exception))

    return await bot.start(self.bot_token)
