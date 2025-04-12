from traceback import format_exc
import functools
import discord

from typing import List, Callable, Optional

from discord_bot.visuals.embeds import exception_embed

__all__ = ("users_blacklist", "base_command")


def users_blacklist(user_ids: List[int],
                    ignore_empty: Optional[bool] = True,
                    message: Optional[str] = None) -> Callable:

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(ctx: discord.Message, *args, **kwargs):
            if ignore_empty and user_ids or ctx.author.id in user_ids:
                return (not message) or (await ctx.reply(message))

            await func(ctx, *args, **kwargs)

        return wrapper
    return decorator


def base_command(func: Callable):
    @functools.wraps(func)
    async def wrapper(ctx: discord.Message, *args, **kwargs):
        await ctx.defer()
        try:
            await func(ctx, *args, **kwargs)
        except:
            await ctx.reply(embed=exception_embed(format_exc()))

    return wrapper
