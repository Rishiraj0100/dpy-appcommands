import discord
import asyncio

from .utils import *
from .models import SlashCommand, SubCommandGroup

from discord.ext.commands import Cog
from typing import Optional, Union, List


class SlashCog(Cog):
    """The cog for extensions

    Example
    ----------

    .. code-block:: python3

        from appcommands import cog, command

        class MyCog(cog.SlashCog):
            def __init__(self, bot):
                self.bot = bot

            @command(name="test")
            async def test(self, ctx):
                await ctx.send("tested!")

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
    
                if isinstance(value, SlashCommand):
                    slashcmds[elem] = value
                elif isinstance(value, SubCommandGroup):
                    slashcmds[elem] = value
                    
        self.__slash_commands__ = tuple(cmd for cmd in slashcmds.values())
        return self

    def _inject(self, bot):
        for cmd in self.__slash_commands__:
            bot.to_register.append(cmd)

        return super()._inject(bot)
        
    def _eject(self, bot):
        for cmd in self.__slash_commands__:
            bot.remove_app_command(cmd)

        super()._eject(bot)
