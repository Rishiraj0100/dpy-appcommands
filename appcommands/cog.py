import discord
import asyncio

from .utils import *
from .models import (
    SlashCommand,
    SubCommandGroup,
    UserCommand,
    MessageCommand
)

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
        new_list = [i for i in self.__slash_commands__]
        to_remove, updated_list = [], []
        for index, cmd in enumerate(new_list):
            cmd.cog = self
            if isinstance(cmd, SlashCommand):
                setattr(self.__class__, cmd.callback.__name__, cmd.__func__)

            if isinstance(cmd, SubCommandGroup):
                for subcmd in cmd.subcommands:
                    if isinstance(subcmd, SubCommandGroup):
                        for _subcmd in subcmd.subcommands:
                            _subcmd.cog = self
                    else:
                        subcmd.cog = self
  
            if (
                isinstance(cmd, SlashCommand)
                and not cmd.is_subcommand
            ):
                bot.to_register.append(cmd)
            elif  (
                isinstance(cmd, SubCommandGroup)
                and not cmd.parent
            ):
                bot.to_register.append(cmd)
            elif isinstance(cmd, (MessageCommand, UserCommand)):
                bot.to_register.append(cmd)
            else:
                to_remove.append(new_list[index])

        for cmd in new_list:
            if not cmd in to_remove:
                updated_list.append(cmd)

        self.__slash_commands__ = (i for i in updated_list)
        return super()._inject(bot)
        
    def _eject(self, bot):
        for cmd in self.__slash_commands__:
            bot.remove_app_command(cmd)

        super()._eject(bot)
