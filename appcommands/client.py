import sys
import types
import discord
import importlib

from .utils import *
from .models import (
    command as _cmd,
    InteractionContext,
    SubCommandGroup,
    messagecommand as _mcmd,
    usercommand as _ucmd
)

from discord import http, ui
from discord.ext import commands
from discord.enums import InteractionType
from typing import List, Optional, Tuple, Union, Dict, Mapping, Callable, Any, TYPE_CHECKING


if TYPE_CHECKING:
    from .models import (
        BaseCommand,
        MessageCommand,
        SlashCommand,
        UserCommand
    )

__all__ = ("Bot", "AutoShardedBot")

class ApplicationMixin:
    """The mixin for appcommands module"""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.to_register = []
        self.__appcommands = {}
        self.__subcommands = {}
        self.__usercommands = {}
        self.__slashcommands = {}
        self.__messagecommans = {}
        self.add_listener(self.interaction_handler, "on_interaction")

    def add_app_command(self, command: BaseCommand) -> None:
        """Adds a app command,
        usually used when subclassed

        Parameters
        ------------
        command: :class:`~appcommands.models.BaseCommand`
            The command which is to be added"""
        self.to_register.append(command)

    def remove_app_command(self, command: BaseCommand) -> None:
        """Remove a :class:`~appcommands.models.BaseCommand` from the internal list
        of commands.

        Parameters
        -----------
        command: :class:`~appcommands.models.BaseCommand`
            The command to remove.
        """
        self.__appcommands.pop(command.id)
        self.__subcommands.pop(command.id)
        self.__usercommands.pop(command.id)
        self.__slashcommands.pop(command.id)
        self.__messagecommands.pop(command.id)

    def slashcommand(self, cls=MISSING, **kwargs) -> Callable[[Callable], SlashCommand]:
        r"""Adds a slash command to bot
        same as :meth:`~appcommands.models.slashcommand`

        Parameters
        -----------
        name: :class:`~str`
            name of the command, defaults to function name, (required)
        description: Optional[:class:`~str`]
            description of the command, required
        guild_ids: Optional[List[:class:`~int`]]
            list of ids of the guilds for which command is to be added, (optional)
        options: Optional[List[:class:`~appcommands.models.Option`]]
            the options for command, can be empty
        cls: :class:`~appcommands.models.SlashCommand`
            The custom command class, must be a subclass of :class:`~appcommands.models.SlashCommand`, (optional)

        Example
        ---------

        .. code-block:: python3

            @bot.slashcommand(name="Hi", description="Hello!")
            async def some_func(ctx):
                await ctx.send("Hello!")

        Raises
        --------
        TypeError
           The passed callback is not coroutine or it is already an AppCommand

        Returns
        --------
        Callable[[Callable], :class:`~appcommands.models.SlashCommand`]
            The slash command."""
        def decorator(func) -> SlashCommand:
            wrapped = _cmd(cls=cls, **kwargs)
            cmd = wrapped(func)
            self.add_app_command(cmd)
            return cmd

        return decorator

    def messagecommand(self, cls=MISSING, **kwargs) -> Callable[[Callable], MessageCommand]:
        r"""Adds a message command to bot
        same as :meth:`~appcommands.models.messagecommand`

        Parameters
        -----------
        name: :class:`~str`
            name of the command, defaults to function name, (required)
        guild_ids: Optional[List[:class:`~int`]]
            list of ids of the guilds for which command is to be added, (optional)
        cls: :class:`~appcommands.models.MessageCommand`
            The custom command class, must be a subclass of :class:`~appcommands.models.MessageCommand`, (optional)

        Example
        ---------

        .. code-block:: python3

            @bot.messagecommand(name="ID")
            async def some_func(ctx, message: discord.Message):
                await ctx.send(f"Id of that message is {message.id}")

        Raises
        --------
        TypeError
           The passed callback is not coroutine or it is already an AppCommand

        Returns
        --------
        Callable[[Callable], :class:`~appcommands.models.MessageCommand`]
            The slash command."""
        def decorator(func) -> MessageCommand:
            wrapped = _mcmd(cls=cls, **kwargs)
            cmd = wrapped(func)
            self.add_app_command(cmd)
            return cmd

        return decorator

    def usercommand(self, cls=MISSING, **kwargs) -> Callable[[Callable], UserCommand]:
        r"""Adds a message command to bot
        same as :meth:`~appcommands.models.usetcommand`

        Parameters
        -----------
        name: :class:`~str`
            name of the command, defaults to function name, (required)
        guild_ids: Optional[List[:class:`~int`]]
            list of ids of the guilds for which command is to be added, (optional)
        cls: :class:`~appcommands.models.UserCommand`
            The custom command class, must be a subclass of :class:`~appcommands.models.UserCommand`, (optional)

        Example
        ---------

        .. code-block:: python3

            @bot.usercommand(name="ID")
            async def some_func(ctx, user: discord.Member):
                await ctx.send(f"Id of that user is {user.id}")

        Raises
        --------
        TypeError
           The passed callback is not coroutine or it is already an AppCommand

        Returns
        --------
        Callable[[Callable], :class:`~appcommands.models.UserCommand`]
            The slash command."""
        def decorator(func) -> UserCommand:
            wrapped = _ucmd(cls=cls, **kwargs)
            cmd = wrapped(func)
            self.add_app_command(cmd)
            return cmd

        return decorator

    def slashgroup(self, name: str, description: Optional[str] = "No description.") -> SubCommandGroup:
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

            mygrp = bot.slashgroup(name='test', description='test group')

            @mygrp.command(description="test cmd of test grp")
            async def test1(ctx):
                await ctx.send("tested")

        Returns
        ---------
        :class:`~appcommands.models.SubCommandGroup`
            The group by which commands will be made"""
        sub_command_group = SubCommandGroup(name, description)
        self.add_slash_command(sub_command_group)
        return sub_command_group

    async def register_commands(self) -> None:
        r"""|coro|

        The coro which registers slash commands"""
        commands = []
        registered_commands = await self.http.get_global_commands(self.user.id)
        for command in [cmd for cmd in self.to_register if not cmd.guild_ids]:
            json = command.to_dict()
            if len(registered_commands) > 0:
                matches = [
                    x
                    for x in registered_commands
                    if x["name"] == command.name and x["type"] == command.type
                ]
                if matches:
                    json["id"] = matches[0]["id"]
            commands.append(json)

        guild_commands = {}
        async for guild in self.fetch_guilds(limit=None):
            guild_commands[guild.id] = []

        for command in [cmd for cmd in self.to_register if cmd.guild_ids]:
            json = command.to_dict()
            for guild_id in command.guild_ids:
                to_update = guild_commands[guild_id]
                guild_commands[guild_id] = to_update + [json]

        for guild_id in guild_commands:
            if not guild_commands[guild_id]:
                continue

            try:
                cmds = await self.http.bulk_upsert_guild_commands(self.user.id, guild_id, guild_commands[guild_id])
            except Exception as e:
                print(f"Failed to add guild commands for guild {guild_id}")
                traceback.print_exc()
                self.dispatch("on_guild_command_register_fail", guild_id, guild_commands[guild_id])
            else:
                for i in cmds:
                    cmd = discord.utils.get(self.to_register, name=i["name"], description=i["description"], type=i['type'])
                    setattr(cmd, "id", int(i['id']))
                    if cmd.type == 1:
                        self.__slashcommands[int(i.get('id'))] = cmd
                    self.__appcommands[int(i["id"])] = cmd

        cmds = await self.http.bulk_upsert_global_commands(self.user.id, commands)
        for i in cmds:
            cmd = discord.utils.get(
                self.to_register,
                name=i["name"],
                description=i["description"],
                type=i["type"],
            )
            setattr(cmd, "id", int(i['id']))
            if cmd.type == 1:
                self.__slashcommands[int(i.get('id'))] = cmd
            elif cmd.type == 2:
                self.__usercommands[int(i.get('id'))] = cmd
            else:
                self.__messagecommands[int(i.get('id'))] = cmd

            if isinstance(cmd, SubCommandGroup):
                self.__subcommands[int(i['id'])] = {}
                for subcommand in cmd.subcommands:
                    if isinstance(subcommand, SubCommandGroup):
                        for _subcmd in subcommand.subcommands:
                            self.__subcommands[int(i['id'])][_subcmd.name] = _subcmd
                    else:
                        self.__subcommands[int(i['id'])][subcommand.name] = subcommand

            self.__appcommands[int(i["id"])] = cmd
        self.to_register = []

    async def on_connect(self):
        await self.register_commands()

    @property
    def appcommands(self) -> Mapping[int, Union[SlashCommand, SubCommandGroup]]:
        """The all application command the bot has

        Returns
        --------
        Mapping[:class:`~int`, Union[:class:`~appcommands.models.SlashCommand`, :class:`~appcommands.models.SubCommandGroup`]]
        """
        return types.MappingProxyType(self.__appcommands)

    @property
    def subcommands(self) -> Mapping[int, Union[SlashCommand, SubCommandGroup]]:
        """The slashcommands' subcommands

        Returns
        --------
        Mapping[:class:`~int`, Union[:class:`~appcommands.models.SlashCommand`, :class:`~appcommands.models.SubCommandGroup`]]
        """
        return types.MappingProxyType(self.__subcommands)

    @property
    def slashcommands(self) -> Mapping[str, Union[SlashCommand, SubCommandGroup]]:
        """All slashcommands with id

        Returns
        ---------
        Mapping[:class:`~int`, Union[:class:`~appcommands.models.SlashCommand`, :class:`~appcommands.models.SubCommandGroup`]]
        """
        return types.MappingProxyType(self.__slashcommands)

    @property
    def usercommands(self) -> Mapping[str, UserCommand]:
        """All usercommands with id

        Returns
        ---------
        Mapping[:class:`~int`, :class:`~appcommands.models.UserCommand`]
        """
        return types.MappingProxyType(self.__usercommands)

    @property
    def messagecommands(self) -> Mapping[str, MessageCommand]:
        """All messagecommands with id

        Returns
        ---------
        Mapping[:class:`~int`, :class:`~appcommands.models.MessageCommand`]
        """
        return types.MappingProxyType(self.__messagecommands)

    def get_slash_commands(self) -> Mapping[str, Union[SlashCommand, SubCommandGroup]]:
        """Gets every slash commands registered in the current running instance

        Returns
        ---------
        Mapping[:class:`~str`, Union[:class:`~appcommands.models.SlashCommand`, :class:`~appcommands.models.SubCommandGroup`]]
        """
        ret = {}

        for id, cmd in self.__slashcommands:
            ret[self.__slashcommands[id]] = cmd

        return types.MappingProxyType(ret)

    def get_slash_command(self, name: str) -> Union[SlashCommand, SubCommandGroup]:
        """Gives a slash command registered in this module
        
        Parameters
        -----------
        name: :class:`~str`
            the name from which the slash command is to be found

        Returns
        ---------
        Union[:class:`~appcommands.models.SlashCommand`, :class:`~appcommands.models.SubCommandGroup`]
            The found thing"""
        return (self.get_slash_commands()).get(name)

    def get_user_commands(self) -> Mapping[str, UserCommand]:
        """Gets every user commands registered in the current running instance

        Returns
        ---------
        Mapping[:class:`~str`, :class:`~appcommands.models.UserCommand`]
        """
        ret = {}

        for id, cmd in self.usercommands:
            ret[self.__usercommands[id].name] = cmd

        return types.MappingProxyType(ret)

    def get_user_command(self, name: str) -> UserCommand:
        """Gives a user command registered in this module
        
        Parameters
        -----------
        name: :class:`~str`
            the name from which the user command is to be found

        Returns
        ---------
        :class:`~appcommands.models.UserCommand`
            The found thing"""
        return (self.get_user_commands()).get(name)

    def get_message_commands(self) -> Mapping[str, MessageCommand]:
        """Gets every user commands registered in the current running instance

        Returns
        ---------
        Mapping[:class:`~str`, :class:`~appcommands.models.MessageCommand`]
        """
        ret = {}

        for id, cmd in self.messagecommands:
            ret[self.__messagecommands[id].name] = cmd

        return types.MappingProxyType(ret)

    def get_message_command(self, name: str) -> MessageCommand:
        """Gives a message command registered in this module
        
        Parameters
        -----------
        name: :class:`~str`
            the name from which the message command is to be found

        Returns
        ---------
        :class:`~appcommands.models.MessageCommand`
            The found thing"""
        return (self.get_message_commands()).get(name)

    def get_interaction_context(self, interaction: discord.Interaction) -> InteractionContext:
        """The method usually implemented to use custom contexts

        Parameters
        -----------
        interaction: :class:`~discord.Intetaction`

        Returns
        ---------
        :class:`~appcommands.models.InteractionContext`
            The context that will be used for handling interactions"""
        return InteractionContext(self, interaction)

    async def interaction_handler(self, interaction):
        if interaction.type != InteractionType.application_command:
            return

        id = int(interaction.data['id'])
        _data = interaction.data.copy()
        context = self.get_interaction_context(interaction)
        if id in self.__subcommands:
            _data = _data['options'][0]
            while 'options' in _data and _data['type'] == 2:
                if _data.get('options'):
                    _data = _data.get('options')[0]
                else:
                    break

            if (_data['name'] in self.__subcommands[id]):
                return await context.invoke(self.__subcommands[id][_data['name']])

        if int(interaction.data['id']) in self.__appcommands:
            context = self.get_interaction_context(interaction)
            await context.invoke(self.__appcommands[id])

class Bot(ApplicationMixin, commands.Bot):
    """The Bot
    This is fully same as :class:`~discord.ext.commands.Bot`

    Example
    ---------

    .. code-block:: python3

        import appcommands

        bot = appcommands.Bot(command_prefix="$")

    """
    pass

class AutoShardedBot(ApplicationMixin, commands.AutoShardedBot):
    """The AutoShardedBot class
    This is fully same as :class:`~discord.ext.commands.AutoShardedBot`

    Example
    ---------

    .. code-block:: python3

        import appcommands

        bot = appcommands.AutoShardedBot(command_prefix="$")

    """
    pass
