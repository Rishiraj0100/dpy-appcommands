import discord
import asyncio

from .utils import *
from .models import SlashCommand, Option, command as _cmd, SubCommandGroup

from discord.ext.commands import Cog
from typing import Optional, Union, List

__all__ = ("command", "SlashCog")


def slash(*args, cls=MISSING, **kwargs):
    """Same as :func:`~appcommands.models.command` but doesn't
    requires bot and is to be used in cogs only

    Parameters
    ------------
    name: :class:`~str`
        Name of the command, (required)
    description: Optional[:class:`~str`]
        Description of the command, (optional)
    guild: Optional[:class:`~str`]
        Id of the guild for which command is to be added, (optional)
    options: Optional[List[:class:`~appcommands.models.Option`]]
        Options for the command, detects automatically if None given, (optional)
    cls: :class:`~appcommands.models.SlashCommand`
        The custom command class, must be a subclass of :class:`~appcommands.models.SlashCommand`, (optional)

    Example
    ----------
    
    .. code-block:: python3
    
        from slash import cog
        
        class MyCog(cog.SlashCog):
            @cog.slash(name="hi", description="Hello!")
            async def hi(ctx, user: discord.Member = None):
                user = user or ctx.user
                await ctx.reply(f"Hi {user.mention}")

    Raises
    --------
    TypeError
        The passed callback is not coroutine or it is already a SlashCommand
    """
    if cls is MISSING:
        cls = SlashCommand

    def wrapper(func):
        if not asyncio.iscoroutinefunction(func):
            raise TypeError('Callback must be a coroutine.')
        if hasattr(func, "__slash__") and isinstance(func.__slash__, SlashCommand):
            raise TypeError('Callback is already a slashcommand.')

        result = cls(*args, callback=func, **kwargs)
        func.__slash__ = result
        return func

    return wrapper


def slashgroup(name: str, description: Optional[str] = "No description.") -> SubCommandGroup:
    """The group by which subcommands are to be derived for slash commands

    Parameters
    -------------
    name: :class:`~str`
        Name of the group, (required)
    description: Optional[:class:`~str`]
        Description of the group, (optional)

    Example
    ---------

    .. code-block:: python3

        from appcommands import cog

        mygrp = cog.slashgroup(name='test', description='test group')

        class MyCog(cog.SlashCog):
            @mygrp.command(description="test cmd of test grp")
            async def test1(self, ctx):
                await ctx.send("tested")

    Returns
    ---------
    :class:`~appcommands.models.SubCommandGroup`
        The group by which commands will be made"""
    sub_command_group = SubCommandGroup(name, description)
    return sub_command_group

class SlashCog(Cog):
    """The cog for extensions

    Example
    ----------

    .. code-block:: python3

        from slash import cog

        class MyCog(cog.SlashCog):
            def __init__(self, bot):
                self.bot = bot

            @cog.slash(name="test")
            async def test(self, ctx):
                await ctx.reply("tested!")

        def setup(bot):
            bot.add_cog(MyCog(bot))

    """
    __slash_commands__: tuple
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        slashcmds = {}
        for base in reversed(self.__class__.__mro__):
            for elem, value in base.__dict__.items():
                if elem in slashcmds:
                    del slashcmds[elem]
    
                if (
                    hasattr(value, "__slash__")
                    and isinstance(value.__slash__, SlashCommand)
                    and not value.__slash__.is_subcommand
                ):
                    slashcmds[elem] = value.__slash__
                elif (
                    hasattr(value, "__slash__")
                    and isinstance(value.__slash__, SubCommandGroup)
                    and value.__slash__.parent is None
                ):
                    slashcmds[elem] = value.__slash__
                    
        self.__slash_commands__ = tuple(cmd for cmd in slashcmds.values())
        return self

    def _inject(self, bot):
        for cmd in self.__slash_commands__:
            bot.to_register.append(cmd)

        return super()._inject(bot)
        
    def _eject(self, bot):
        loop, http = bot.loop, bot.http
        for cmd in self.__slash_commands__:
            loop.create_task(http.delete_global_command(bot.user.id, bot.get_slash_command(cmd.name)['id']))
            
        super()._eject(bot)
