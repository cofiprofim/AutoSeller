from discord.ext import commands
import discord

from .buttons import ControlPanel
from .embeds import exception_embed, custom_embed


async def start(self):
    bot = commands.Bot(command_prefix=self.discord_bot["Prefix"], intents=discord.Intents.all())

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

            return await ControlPanel(self, ctx).start()
        except:
            return await ctx.reply(embeds=exception_embed(traceback.format_exc()))

    @bot.event
    async def on_command_error(ctx: discord.Message, exception: Exception) -> None:
        if type(exception) in (commands.BadArgument, commands.CommandNotFound, commands.MissingRequiredArgument):
            return None

        await ctx.reply(embed=exception_embed(exception))

    return await bot.start(self.discord_bot["Token"])
