import sys
import types
import discord
import secrets
import importlib
import traceback

from .utils import *
from .core import (
    command as _cmd,
    InteractionContext,
    SubCommandGroup,
    messagecommand as _mcmd,
    usercommand as _ucmd,
    BaseCommand,
    MessageCommand,
    SlashCommand,
    UserCommand
)

from discord import http, ui
from discord.ext import commands
from discord.enums import InteractionType
from typing import List, Optional, Tuple, Union, Dict, Mapping, Callable, Any, Awaitable


__all__ = (
    "AutoShardedBot",
    "Bot"
)

class ApplicationMixin:
    """The mixin for appcommands module"""
    def __init__(self, *args, **kwargs) -> None:
        oldkwargs = kwargs.copy()

        if not kwargs.get('command_prefix'):
            kwargs["command_prefix"] = " ".join(secrets.token_urlsafe(5000).split('_'))

        def _do_nothing(*args, **kwargs) -> None:
            pass

        def None_wrap(*args, **kwargs) -> Callable[[Callable[[Any, Any], Any]], Callable]:
            def wrap(func: Callable[[Any, Any], Any]) -> Callable[[Any, Any], Any]:
                return func
            return wrap

        super().__init__(*args, **kwargs)

        if not oldkwargs.get('command_prefix'):
            self.remove_command('help')
            self.__command = self.command
            self.command = None_wrap
            self.add_command = _do_nothing
            self.remove_command = _do_nothing

        self.__connected: bool = False

        self.to_register: List[BaseCommand]                                   = []
        self.__appcommands: Dict[int, BaseCommand]                            = {}
        self.__usercommands: Dict[int, UserCommand]                           = {}
        self.__messagecommands: Dict[int, MessageCommand]                     = {}
        self.__subcommands: Dict[int, Dict[str, SlashCommand]]                = {}
        self.__slashcommands: Dict[int, Union[SlashCommand, SubCommandGroup]] = {}

        self.add_listener(self.__connectlistener, "on_connect")
        self.add_listener(self.interaction_handler, "on_interaction")

    def add_app_command(self, command: BaseCommand, *, on_discord: bool = False) -> Union[None, Awaitable]:
        """Adds a app command,
        usually used when subclassed

        .. versionadded:: 2.0

        Parameters
        ------------
        command: :class:`~appcommands.core.BaseCommand`
            The command which is to be added
        on_discord: :class:`~bool`
            Whether to register all pending commands on discord
            needs to be awaited when passed ``True`` (default: ``False``)"""
        self.to_register.append(command)
        if on_discord:
            return self.register_commands()

    def remove_app_command(self, command: BaseCommand) -> None:
        """Remove an application command from the internal list
        of appcommands.

        .. versionadded:: 2.0

        Parameters
        -----------
        command: :class:`appcommands.BaseCommand`
            The command to remove.
        """
        if command.id in self.__appcommands:
            self.__appcommands.pop(command.id)
        if command.id in self.__subcommands:
            self.__subcommands.pop(command.id)
        if command.id in self.__usercommands:
            self.__usercommands.pop(command.id)
        if command.id in self.__slashcommands:
            self.__slashcommands.pop(command.id)
        if command.id in self.__messagecommands:
            self.__messagecommands.pop(command.id)

    def slashcommand(self, cls=MISSING, **kwargs) -> Callable[[Callable], SlashCommand]:
        r"""A decorator which adds a slash command to bot
        same as :meth:`appcommands.slashcommand`

        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`~str`
            name of the command, defaults to function name, (required)
        description: Optional[:class:`~str`]
            description of the command, required
        guild_ids: Optional[List[:class:`~int`]]
            list of ids of the guilds for which command is to be added, (optional)
        options: Optional[List[:class:`~appcommands.Option`]]
            the options for command, can be empty
        cls: :class:`~appcommands.SlashCommand`
            The custom command class, must be a subclass of :class:`appcommands.SlashCommand`, (optional)

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
        Callable[..., :class:`~appcommands.SlashCommand`]
            The command."""
        def decorator(func) -> SlashCommand:
            wrapped = _cmd(cls=cls, **kwargs)
            cmd = wrapped(func)
            self.add_app_command(cmd)
            return cmd

        return decorator

    def messagecommand(self, cls=MISSING, **kwargs) -> Callable[[Callable], MessageCommand]:
        r"""A shortcut decorator that adds a Context-Menu message commands to bot
        same as :meth:`appcommands.messagecommand`

        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`~str`
            name of the command, defaults to function name, (required)
        guild_ids: Optional[List[:class:`~int`]]
            list of ids of the guilds for which command is to be added, (optional)
        cls: :class:`~appcommands.MessageCommand`
            The custom command class, must be a subclass of :class:`appcommands.MessageCommand`, (optional)

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
        Callable[..., :class:`~appcommands.MessageCommand`]
            The command."""
        def decorator(func) -> MessageCommand:
            wrapped = _mcmd(cls=cls, **kwargs)
            cmd = wrapped(func)
            self.add_app_command(cmd)
            return cmd

        return decorator

    def usercommand(self, cls=MISSING, **kwargs) -> Callable[[Callable], UserCommand]:
        r"""A decorator which adds a message command to bot
        same as :meth:`appcommands.usercommand`

        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`~str`
            name of the command, defaults to function name, (required)
        guild_ids: Optional[List[:class:`~int`]]
            list of ids of the guilds for which command is to be added, (optional)
        cls: :class:`~appcommands.UserCommand`
            The custom command class, must be a subclass of :class:`appcommands.UserCommand`, (optional)

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
        Callable[..., :class:`~appcommands.UserCommand`]
            The command."""
        def decorator(func) -> UserCommand:
            wrapped = _ucmd(cls=cls, **kwargs)
            cmd = wrapped(func)
            self.add_app_command(cmd)
            return cmd

        return decorator

    def slashgroup(self, name: str, description: Optional[str] = "No description.") -> SubCommandGroup:
        """The group by which subcommands are to be derived for slash commands

        .. versionadded:: 2.0

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
        :class:`appcommands.SubCommandGroup`
            The group by which commands will be made"""
        sub_command_group = SubCommandGroup(name, description)
        self.add_app_command(sub_command_group)
        return sub_command_group

    async def register_commands(self) -> None:
        r"""|coro|

        This function registers app commands

        .. versionadded:: 2.0
        """
        commands = []
        perms = {}
        registered_commands = await self.http.get_global_commands(self.user.id)
        self.to_register.extend([c for c in list(self.appcommands.values()) if ((isinstance(c,(SubCommandGroup,SlashCommand))) and (not bool(c.parent))) or (not isinstance(c,(SubCommandGroup,SlashCommand)))])

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
            perms[guild.id] = []

        for command in [cmd for cmd in self.to_register if cmd.guild_ids]:
            json = command.to_dict()
            if (command.guild_ids is ALL_GUILDS) or (getattr(command,"all_guilds",False)):
                command.guild_ids = []
                command.all_guilds = True
                for guild_id in guild_commands:
                    guild_commands[guild_id] = guild_commands[guild_id]+[json]
                    command.guild_ids.append(guild_id)
            else:
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
                    if cmd.__permissions__:
                        perms[guild_id].append({"id": str(cmd.id), "permissions": cmd.__permissions__})

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

        for guild_id, data in perms.items():
            if not data:
                continue

            await self.http.bulk_edit_guild_application_command_permissions(
                self.user.id,
                guild_id,
                data
            )

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

    async def __connectlistener(self):
        if not self.__connected:
            await self.register_commands()
            self.__connected = True
            self.remove_listener(self.__connectlistener, 'on_connect')

    @property
    def appcommands(self) -> Mapping[int, BaseCommand]:
        """The all application command the bot has

        .. versionadded:: 2.0

        Returns
        --------
        Mapping[:class:`~int`, :class:`appcommands.BaseCommand`]
        """
        return types.MappingProxyType(self.__appcommands)

    @property
    def subcommands(self) -> Mapping[int, Union[SlashCommand, SubCommandGroup]]:
        """The slashcommands' subcommands

        .. versionadded:: 2.0

        Returns
        --------
        Mapping[:class:`~int`, Union[:class:`~appcommands.SlashCommand`, :class:`~appcommands.SubCommandGroup`]]
        """
        return types.MappingProxyType(self.__subcommands)

    @property
    def slashcommands(self) -> Mapping[str, Union[SlashCommand, SubCommandGroup]]:
        """All slashcommands with id

        .. versionadded:: 2.0

        Returns
        ---------
        Mapping[:class:`~int`, Union[:class:`~appcommands.SlashCommand`, :class:`~appcommands.SubCommandGroup`]]
        """
        return types.MappingProxyType(self.__slashcommands)

    @property
    def usercommands(self) -> Mapping[str, UserCommand]:
        """All usercommands with id

        .. versionadded:: 2.0

        Returns
        ---------
        Mapping[:class:`~int`, :class:`~appcommands.UserCommand`]
        """
        return types.MappingProxyType(self.__usercommands)

    @property
    def messagecommands(self) -> Mapping[str, MessageCommand]:
        """All messagecommands with id

        .. versionadded:: 2.0

        Returns
        ---------
        Mapping[:class:`~int`, :class:`~appcommands.MessageCommand`]
        """
        return types.MappingProxyType(self.__messagecommands)

    def get_slash_commands(self) -> Mapping[str, Union[SlashCommand, SubCommandGroup]]:
        """Gets every slash commands registered in the current running instance

        .. versionadded:: 2.0

        Returns
        ---------
        Mapping[:class:`~str`, Union[:class:`~appcommands.SlashCommand`, :class:`~appcommands.models.SubCommandGroup`]]
        """
        ret = {}
        for cmd in self.__slashcommands.values():
            if not isinstance(cmd, SubCommandGroup): ret[cmd.full_name] = cmd
        for cmd in self.__subcommands.values():
            if not isinstance(cmd, dict): ret[cmd.full_name] = cmd
            else:
                for _cmd in cmd.values():
                    ret[_cmd.full_name] = _cmd

        return types.MappingProxyType(ret)

    def get_slash_command(self, name: str) -> Union[SlashCommand, SubCommandGroup]:
        """Gives a slash command registered in this module
        
        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`~str`
            the name from which the slash command is to be found

        Returns
        ---------
        Union[:class:`~appcommands.SlashCommand`, :class:`~appcommands.SubCommandGroup`, :class:`None`]
            The found thing"""
        return (self.get_slash_commands()).get(name)

    def get_user_commands(self) -> Mapping[str, UserCommand]:
        """Gets every user commands registered in the current running instance

        .. versionadded:: 2.0

        Returns
        ---------
        Mapping[:class:`~str`, :class:`~appcommands.UserCommand`]
        """
        ret = {}

        for id, cmd in self.usercommands.items():
            ret[self.__usercommands[id].name] = cmd

        return types.MappingProxyType(ret)

    def get_user_command(self, name: str) -> UserCommand:
        """Gives a user command registered in this module
        
        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`~str`
            the name from which the user command is to be found

        Returns
        ---------
        :class:`~appcommands.UserCommand`
            The found thing"""
        return (self.get_user_commands()).get(name)

    def get_message_commands(self) -> Mapping[str, MessageCommand]:
        """Gets every message commands registered in the current running instance

        .. versionadded:: 2.0

        Returns
        ---------
        Mapping[:class:`~str`, :class:`~appcommands.MessageCommand`]
        """
        ret = {}

        for id, cmd in self.messagecommands.items():
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
        :class:`~appcommands.MessageCommand`
            The found thing"""
        return (self.get_message_commands()).get(name)

    def get_app_commands(self) -> Mapping[str, BaseCommand]:
        """Gets every app commands registered in the current running instance

        .. versionadded:: 2.0

        Returns
        ---------
        Mapping[:class:`~str`, :class:`appcommands.core.BaseCommand`]
        """
        ret = {}

        for id, cmd in self.appcommands.items():
            ret[self.__appcommands[id].name] = cmd

        return types.MappingProxyType(ret)

    def get_app_command(self, name: str) -> BaseCommand:
        """Gives a app command registered in this module
        
        Parameters
        -----------
        name: :class:`~str`
            the name from which the message command is to be found

        Returns
        ---------
        :class:`appcommands.core.BaseCommand`
            The found thing"""
        return (self.get_app_commands()).get(name)

    def get_interaction_context(self, interaction: discord.Interaction) -> InteractionContext:
        """The method usually implemented to use custom contexts

        .. versionadded:: 2.0

        Parameters
        -----------
        interaction: :class:`~discord.Intetaction`

        Returns
        ---------
        :class:`~appcommands.InteractionContext`
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
    """The Bot class.
    This is a subclass of :class:`discord.ext.commands.Bot`

    Example
    ---------

    .. code-block:: python3

        import appcommands

        bot = appcommands.Bot(command_prefix="$")

    """
    pass


class AutoShardedBot(ApplicationMixin, commands.AutoShardedBot):
    """The AutoShardedBot class.
    This is a subclass of :class:`discord.ext.commands.AutoShardedBot`
    and is same as :class:`appcommands.Bot`

    Example
    ---------

    .. code-block:: python3

        import appcommands

        bot = appcommands.AutoShardedBot(command_prefix="$")

    """
    pass
