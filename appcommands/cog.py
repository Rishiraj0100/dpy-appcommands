import asyncio
import discord
import inspect

from .utils import *
from .core import (
    BaseCommand,
    MessageCommand,
    SlashCommand,
    SubCommandGroup,
    UserCommand
)

from discord.ext import commands
from typing import Optional, Union, List, Type, Tuple

class CogMeta(commands.CogMeta):
    """A metaclass for defining a cog.

    This is a subclass of :class:`discord.ext.commands.CogMeta`

    .. versionadded:: 2.0

    Note that you should probably not use this directly. It is exposed
    purely for documentation purposes along with making custom metaclasses to intermix
    with other metaclasses such as the :class:`abc.ABCMeta` metaclass.

    For example, to create an abstract cog mixin class, the following would be done.

    .. code-block:: python3

        import abc

        class CogABCMeta(appcommands.CogMeta, abc.ABCMeta):
            pass

        class SomeMixin(metaclass=abc.ABCMeta):
            pass

        class SomeCogMixin(SomeMixin, appcommands.Cog, metaclass=CogABCMeta):
            pass

    .. note::

        When passing an attribute of a metaclass that is documented below, note
        that you must pass it as a keyword-only argument to the class creation
        like the following example:

        .. code-block:: python3

            class MyCog(appcommands.Cog, name='My Cog'):
                pass

    Attributes
    -----------
    name: :class:`str`
        The cog name. By default, it is the name of the class with no modification.
    description: :class:`str`
        The cog description. By default, it is the cleaned docstring of the class.
    """
    __app_commands__: Tuple[BaseCommand]
    __user_commands__: Tuple[UserCommand]
    __slash_commands__: Tuple[Union[SlashCommand, SubCommandGroup]]
    __message_commands__: Tuple[MessageCommand]
    def __new__(cls: Type[commands.CogMeta], *args, **kwargs):
        name, bases, attrs = args
        attrs['__cog_name__'] = kwargs.pop('name', name)

        description = kwargs.pop('description', None)
        if description is None:
            description = inspect.cleandoc(attrs.get('__doc__', ''))
        attrs['__cog_description__'] = description

        slashcmds = {}
        appcmds = {}
        usercmds = {}
        msgcmds = {}
        no_bot_cog = 'Commands or listeners must not start with cog_ or bot_ (in method {0.__name__}.{1})'

        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
        for base in reversed(new_cls.__mro__):
            for elem, value in base.__dict__.items():
                if elem in appcmds:
                    del appcmds[elem]
                    slashcmds.pop(elem)
                    usercmds.pop(elem)
                    msgcmds.pop(elem)

                is_static_method = isinstance(value, staticmethod)
                if is_static_method:
                    value = value.__func__
                if isinstance(value, BaseCommand):
                    if is_static_method:
                        raise TypeError(f'Command in method {base}.{elem!r} must not be staticmethod.')
                    if elem.startswith(('cog_', 'bot_')):
                        raise TypeError(no_bot_cog.format(base, elem))
                    appcmds[elem] = value

                if isinstance(value, SlashCommand):
                    slashcmds[elem] = value
                elif isinstance(value, SubCommandGroup):
                    slashcmds[elem] = value
                elif isinstance(value, MessageCommand):
                    msgcmds[elem] = value
                elif isinstance(value, UserCommand):
                    usercmds[elem] = value

        new_cls.__slash_commands__ = tuple(cmd for cmd in slashcmds.values())
        new_cls.__user_commands__ = tuple(cmd for cmd in usercmds.values())
        new_cls.__message_commands__ = tuple(cmd for cmd in msgcmds.values())
        new_cls.__app_commands__ = tuple(cmd for cmd in appcmds.values())

        return new_cls

class Cog(commands.Cog, metaclass=CogMeta):
    """The cog for extension commands

    Example
    ----------

    .. code-block:: python3

        from appcommands import Cog, slashcommand, slashgroup

        class MyCog(Cog):
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

        self.__app_commands__ = tuple(i for i in appcmds)
        self.__user_commands__ = tuple(i for i in usercmds)
        self.__message_commands__ = tuple(i for i in msgcmds)
        self.__slash_commands__ = tuple(i for i in slashcmds)
        return super()._inject(bot)
        
    def _eject(self, bot):
        for cmd in self.__app_commands__:
            bot.remove_app_command(cmd)

        super()._eject(bot)
