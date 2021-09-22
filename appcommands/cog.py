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

        from appcommands import cog, slashcommand, slashgroup

        class MyCog(cog.SlashCog):
            def __init__(self, bot):
                self.bot = bot

            g=slashgroup(name="dev")

            @g.subcommand(name="test1")
            async def test1(self, ctx):
                await ctx.send("tested", ephemeral=True)

            @slashcommand(name="test")
            async def test(self, ctx):
                await ctx.send("tested!")

        def setup(bot):
            bot.add_cog(MyCog(bot))

    """
    __app_commands__: tuple
    __user_commands__: tuple
    __slash_commands__: tuple
    __message_commands__: tuple
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        slashcmds = {}
        appcmds = {}
        usercmds = {}
        msgcmds = {}
        for base in reversed(self.__class__.__mro__):
            for elem, value in base.__dict__.items():
                if elem in appcmds:
                    del appcmds[elem]
                    slashcmds.pop(elem)
                    usercmds.pop(elem)
                    msgcmds.pop(elem)
    
                if isinstance(value, SlashCommand):
                    slashcmds[elem] = value
                    appcmds[elem] = value
                elif isinstance(value, SubCommandGroup):
                    slashcmds[elem] = value
                    appcmds[elem] = value
                elif isinstance(value, MessageCommand):
                    msgcmds[elem] = value
                    appcmds[elem] = value
                elif isinstance(value, UserCommand):
                    usercmds[elem] = value
                    appcmds[elem] = value

        self.__slash_commands__ = tuple(cmd for cmd in slashcmds.values())
        self.__user_commands__ = tuple(cmd for cmd in usercmds.values())
        self.__message_commands__ = tuple(cmd for cmd in msgcmds.values())
        self.__app_commands__ = tuple(cmd for cmd in appcmds.values())

        return self

    def _inject(self, bot):
        new_list = [i for i in self.__app_commands__]
        to_remove, updated_list, appcmds, msgcmds, slashcmds, usercmds = [], [], [], [], [], []
        for index, cmd in enumerate(new_list):
            cmd.cog = self
            if isinstance(cmd, (SlashCommand, UserCommand, MessageCommand)):
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

        for cmd in updated_list:
            if isinstance(cmd, SlashCommand):
                slashcmds.append(cmd)
                appcmds.append(cmd)
            elif isinstance(cmd, SubCommandGroup):
                slashcmds.append(cmd)
                appcmds.append(cmd)
            elif isinstance(cmd, MessageCommand):
                msgcmds.append(cmd)
                appcmds.append(cmd)
            elif isinstance(cmd, UserCommand):
                usercmds.append(cmd)
                appcmds.append(cmd)

        self.__app_commands__ = (i for i in appcmds)
        self.__user_commands__ = (i for i in usercmds)
        self.__message_commands__ = (i for i in msgcmds)
        self.__slash_commands__ = (i for i in slashcmds)
        return super()._inject(bot)
        
    def _eject(self, bot):
        for cmd in self.__slash_commands__:
            bot.remove_app_command(cmd)

        super()._eject(bot)
