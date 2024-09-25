from discord.ext import commands
import discord
from traceback import format_exc

from .buttons import ControlPanel
from .embeds import exception_embed, custom_embed


async def start(self):
    bot = commands.Bot(command_prefix=self.discord_bot_enabled, intents=discord.Intents.all())

    @bot.event
    async def on_ready():
        await bot.tree.sync()

    @bot.hybrid_command(name="start", description="Starts selling limiteds")
    async def start_command(ctx) -> None:
        try:
            await ctx.defer()
            
            if ctx.author.id not in self.owners_list:
                return await ctx.reply(
                    content="You don't have permission to use this command!")
            elif self.control_panel is not None:
                return await ctx.reply(content=f"You already have one control panel running! {self.control_panel.jump_url}")

            return await ControlPanel(self, ctx).start()
        except:
            return await ctx.reply(embed=exception_embed(format_exc()))

    @bot.event
    async def on_command_error(ctx: discord.Message, exception: Exception) -> None:
        if type(exception) in (commands.BadArgument, commands.CommandNotFound, commands.MissingRequiredArgument):
            return None

        await ctx.reply(embed=exception_embed(exception))

    return await bot.start(self.discord_bot["Token"])
