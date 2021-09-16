import copy
import typing
import discord
import asyncio
import inspect
import functools

from .utils import *
from .types import AppClient
from .enums import OptionType

from discord import ui, http
from aiohttp.client import ClientSession
from discord.utils import cached_property
from typing import Dict, List, Union, Optional, Coroutine, Callable


__all__ = (
    "Choice",
    "command",
    "InteractionContext",
    "InteractionData",
    "Option",
    "SlashCommand"
)

async def get_ctx_kw(ctx, params) -> dict:
    bot, cmd, kwargs = ctx.bot, ctx.command, {}
    if cmd is not None and len(ctx.data.options) > 0:
        for k, _ in params.items():
            for opt in ctx.data.options:    
                if k == opt.name:
                    if opt.type == OptionType.USER:
                        if ctx.guild:
                            value = ctx.guild.get_member(opt.value) or await ctx.guild.fetch_member(opt.value)
                        else:
                            value = bot.get_user(opt.value) or await bot.fetch_user(opt.value)
                    elif opt.type == OptionType.CHANNEL:
                        if ctx.guild:
                            value = ctx.guild.get_channel(opt.value) or await ctx.guild.fetch_channel(opt.value)
                        else:
                            value = bot.get_channel(opt.value) or await bot.fetch_channel(opt.value)
                    elif opt.type == OptionType.ROLE:
                        value = ctx.guild.get_role(opt.value)
                    elif opt.type == OptionType.MENTIONABLE:
                        value = discord.Object(opt.value)
                    else:
                        value = opt.value
                    kwargs[k] = value
    return kwargs

def unwrap_function(function):
    partial = functools.partial
    while True:
        if hasattr(function, '__wrapped__'):
            function = function.__wrapped__
        elif isinstance(function, partial):
            function = function.func
        else:
            return function


def get_signature_parameters(function, globalns) -> dict:
    signature = inspect.signature(function)
    params = {}
    cache = {}
    eval_annotation = discord.utils.evaluate_annotation
    for name, parameter in signature.parameters.items():
        annotation = parameter.annotation
        if annotation is parameter.empty:
            params[name] = parameter
            continue
        if annotation is None:
            params[name] = parameter.replace(annotation=type(None))
            continue

        annotation = eval_annotation(annotation, globalns, globalns, cache)

        params[name] = parameter.replace(annotation=annotation)

    return params


def generate_options(function, description: str = "No description.") -> List['Option']:
    options = []
    params = iter(inspect.signature(function).parameters.values())
    if next(params).name in ("self", "cls"):
        # Skip 1. (+ 2.) parameter, self/cls and ctx
        next(params)

    for param in params:
        required = True
        if isinstance(param.annotation, str):
            # if from __future__ import annotations, then annotations are strings and should be converted back to types
            param = param.replace(
                annotation=eval(param.annotation, function.__globals__))

        if param.default is not inspect._empty:
            required = False
        elif getattr(param.annotation, "__origin__", None) is typing.Union:
            # Make a command argument optional with typing.Optional[type] or typing.Union[type, None]
            args = getattr(param.annotation, "__args__", None)
            if args:
                param = param.replace(annotation=args[0])
                required = not isinstance(args[-1], type(None))

        if isinstance(param.annotation, Option):
            kw=param.annotation.to_dict()
            kw["name"] = param.name
            options.append(Option.from_dict(kw))
        else:
            option_type = (OptionType.from_type(param.annotation)
                           or OptionType.STRING)
            name = param.name
            options.append(
                Option(name, description or "No description", option_type,
                       required))

    return options

class InteractionContext:
    """The ctx param given in CMD callbacks
    
    **Attributes**

    Attributes
    ------------
    bot: Union[:class:`~discord.ext.commands.Bot`, :class:`~discord.ext.commands.AutoShardedBot`]
        The discord bot
    client: :class:`~appcommands.client.AppClient`
        The appclient on which this context is used 
    type: :class:`~int`
        Interaction type 
    guild: Union[:class:`~discord.Guild`, None]
        The guild in which command is fired, None if it is in DMs 
    channel: Union[:class:`~discord.TextChannel`, :class:`~discord.DMChannel`]
        The channel in which command is triggered
    id: :class:`~int`
        id of this interaction
    user: Union[:class:`~discord.User`, :class:`~discord.Member`]
        The user who fired this cmd 
    token: :class:`~str`
        token of this interaction, (valid for 15 mins)"""
    def __init__(self, bot, interaction) -> None:
        self.bot: commands.Bot = bot
        self._state = bot._connection
        self._session: ClientSession = self.bot.http._HTTPClient__session
        self.version: int = interaction.version
        self.type: int = interaction.type
        self.token: str = interaction.token
        self.id: int = interaction.id
        self.application_id: int = interaction.application_id
        self.kwargs: dict = {}
        self.interaction = interaction
        self.data: dict = InteractionData.from_dict(self.interaction.data)
        self.__invoked = False

    async def invoke(self):
        if self.__invoked:
            raise TypeError("This context has already been invoked, you can't invoke it again")

        cmd = self.bot.appcommands.get(self.data.id, None)['command']
        self.command = cmd
        params = copy.deepcopy(cmd.params)
        if cmd.cog and str(list(params.keys())[0]) in ("cls", "self"): # cls/self only
            params.pop(list(params.keys())[0])
        self.kwargs[str(list(params.keys())[0])] = self
        params.pop(str(list(params.keys())[0]))
        self.kwargs = {**self.kwargs, **(await get_ctx_kw(self, params))}
        self.__invoked = True
        if cmd.cog:
            cog = self.bot.cogs.get(cmd.cog.qualified_name)
            if cog:
                return await (getattr(cog, cmd.callback.__name__))(**self.kwargs)

            await cmd.callback(**self.kwargs)

    @cached_property
    def channel(self):
        return self.interaction.channel

    @cached_property
    def channel_id(self):
        return self.interaction.channel_id

    @cached_property
    def guild(self):
        return self.interaction.guild

    @cached_property
    def guild_id(self):
        return self.interaction.guild_id

    @cached_property
    def message(self):
        return self.interaction.message

    @cached_property
    def user(self):
        return self.interaction.user

    @cached_property
    def response(self):
        return self.interaction.response

    author = user

    @property
    def respond(self):
        return self.interaction.response.send_message

    @property
    def send(self):
        if not self.response.is_done():
            return self.respond

        return self.channel.send

    @property
    def defer(self):
        return self.interaction.response.defer

    @property
    def followup(self):
        return self.interaction.followup


class InteractionData:
    """The data given in `ctx.data`

    **Attributes**

    Attributes
    ------------
    type: :class:`~int`
        Type of the command
    name: :class:`~str`
        Name of the command
    id: :class:`~int`
        Id of the command
    options: List[:class:`~appcommands.models.Option`]
        Options passed in command
    """
    def __init__(self, type: int, name: str, _id: int, options: Optional[List['Option']] = None) -> None:
        self.type = type
        self.name = name
        self.id = int(_id)
        self.options = options

    def __repr__(self):
        return f"<InteractionData type={self.type} id={self.id} name={self.name} options={self.options}>"

    def __str__(self):
        return self.__repr__()

    @classmethod
    def from_dict(cls, d: dict) -> 'InteractionData':
        options = []
        if d.get('options'):
            for i in d.get('options'):
                options.append(Option.from_dict(i))

        return cls(d['type'], d['name'], d['id'], options)

class Choice:
    """Choice for the option value 
    
    Parameters 
    ------------
    name: :class:`~str`
        name of the choice, (required)
    value: Optional[:class:`~str`]
        value of the choice used for backends, (optional)"""
    def __init__(self, name: str, value: Optional[str] = None):
        self.name = name
        self.value = value or self.name

    def to_dict(self):
        return {"name": self.name, "value": self.value}

    def __repr__(self):
        return "<Choice name={0} value={1.value}>".format(self.name, self)


class Option:
    """Options for slashcommands 
    
    Parameters 
    ------------
    name: :class:`~str`
        name of the Option, (required)
    description: Optional[:class:`~str`]
        description of option, (optional)
    type: Optional[:class:`~int`]
        the type of option, (optional)
    required: Optional[:class:`~bool`]
        whether the option is required
    choices: Optional[List[:class:`~appcommands.models.Choice`]]
        The choices for this option
    """
    def __init__(self,
                 name: str,
                 description: Optional[str] = "No description.",
                 type: Optional[int] = 3,
                 required: Optional[bool] = True,
                 value: str = None,
                 choices: Optional[List[Choice]] = []):
        self.name = name
        self.description = description
        self.type = type
        self.choices = choices
        self.value = value
        self.required = required

    def to_dict(self) -> dict:
        ret = {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "choices": list(c.to_dict() for c in self.choices),
            "required": self.required,
            "value": self.value
        }
        return ret

    @classmethod
    def from_dict(cls, data):
        required = True if data.get("required") else False
        name = data.get("name")
        description = data.get("description")
        value = data.get("value")
        type = data.get("type")
        choices = []
        if data.get("choices"):
            for choice in data.get('choices'):
                choices.append(Choice(**choice))
        return cls(name, description, type, required, value, choices)

    def __repr__(self):
        return f"<Option name={self.name} description={self.description} type={self.type} required={self.required} value={self.value} choices={self.choices}>"

class SlashCommand:
    """SlashCmd base class 
    
    Parameters
    ------------
    client: :class:`~appcommands.client.AppClient`
       Your AppClient instance, (required)
    name: :class:`~str`
       Name of the cmd, (required)
    description: Optional[:class:`~str`]
       description of the cmd, (optional)
    guild: Optional[:class:`~str`]
       id of the guild for which command is to be added, (optional)
    options: Optional[List[:class:`~appcommands.models.Option`]]
       options for your command, (optional)
    callback: Optional[Coroutine]
       the callback which is to be called when a command fires, (optional)
       
    Raises 
    --------
    TypeError 
        Callback is not coroutine 
    ValueError 
        Name not given when coroutine not given
    """
    def __init__(self,
                 name: str = None,
                 description: Optional[str] = "No description.",
                 guild_ids: Optional[List[int]] = None,
                 options: Optional[List[Option]] = [],
                 callback: Optional[Coroutine] = None) -> None:
        self.options = options
        self.description = description
        self.guilds = guild_ids
        self.cog = None
        self.is_subcommand = False
        if callback:
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError('Callback must be a coroutine.')
            self.name = name or callback.__name__
            unwrap = unwrap_function(callback)
            try:
                globalns = unwrap.__globals__
            except:
                globalns = {}

            self.params = get_signature_parameters(callback, globalns)
            if not options or options == []:
                self.options = generate_options(callback, description)
            self.callback = callback
        elif (hasattr(self, 'callback') and self.callback is not MISSING):
            if not callback:
                callback = self.callback
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError('Callback must be a coroutine.')
            self.name = name or self.__class__.__name__
            unwrap = unwrap_function(callback)
            try:
                globalns = unwrap.__globals__
            except:
                globalns = {}

            self.params = get_signature_parameters(callback, globalns)
            if not options:
                self.options = generate_options(self.callback, description)
        else:
            if not name:
                raise ValueError("You must specify name when callback is None")
            self.name  = name

    def __repr__(self):
        return f"<SlashCommmand name='{self.name}' description='{self.description}'>"

    def __str__(self):
        return self.__repr__()

    def to_dict(self) -> dict:
        ret = {
            "name": self.name,
            "description": self.description,
            "options": list(d.to_dict() for d in self.options)
        }
        return ret

    @missing
    async def callback(self, ctx: InteractionContext):
        raise NotImplementedError

class SubCommandGroup(Option):
    def __init__(self,
                 name: str = None,
                 description: str = "No description.",
                 guild_ids: Optional[List[int]] = [],
                 parent = None):
        super().__init__(name=name, description=description, type = OptionType.SUB_COMMAND_GROUP)
        self.parent = parent
        self.name = name
        self.description = description
        self.guilds = self.guild_ids
        self.subcommands: List[Union[SubCommandGroup, SlashCommand]] = []

    def command(self, **kwargs) -> Callable[[Callable], SlashCommand]:
        def wrap(func) -> SlashCommand:
            command = 
            command.is_subcommand = True
            self.subcommands.append(command)
            return command

        return wrap

    def command_group(self, name, description) -> SubCommandGroup:
        if self.parent is not None:
            raise TypeError("Subcommand groups can't have more groups")

        sub_command_group = SubCommandGroup(name, description, parent=self)
        self.subcommands.append(sub_command_group)
        return sub_command_group

    def to_dict(self):
        ret = {
            "name": self.name,
            "description": self.description,
            "options": [o.to_dict() for o in self.subcommands]
        }
        if self.parent is not None:
            ret["type"] = OptionType.SUB_COMMAND_GROUP
        return ret



def command(bot, *args, cls: SlashCommand = MISSING, **kwargs) -> Callable[[Callable], SlashCommand]:
    """The slash commands wrapper 
    
    Parameters
    ------------
    # client: :class:`~appcommands.client.AppClient`
    #     Your appclient instance, (required)
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
    
        from appcommands.models import command
        
        @command(bot.appclient, name="hi", description="Hello!")
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

    def wrapper(func) -> SlashCommand:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError('Callback must be a coroutine.')
        if hasattr(func, "__slash__") and isinstance(func.__slash__, SlashCommand):
            raise TypeError('Callback is already a slashcommand.')

        result = cls(*args, callback=func, **kwargs)
        func.__slash__ = result
        #result.client.bot.loop.create_task(result.client.add_command(result))
        bot.to_register.append(result)
        return func

    return wrapper
