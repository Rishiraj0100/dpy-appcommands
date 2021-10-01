import copy
import typing
import discord
import asyncio
import inspect
import functools

from .utils import *
from .enums import OptionType

from discord import ui, http
from aiohttp.client import ClientSession
from discord.utils import cached_property
from typing import (
    Any,
    Dict,
    List,
    Union,
    Optional,
    Callable,
    Coroutine,
    TYPE_CHECKING
)

if TYPE_CHECKING:
    from .client import Bot, AutoShardedBot

__all__ = (
    "BaseCommand",
    "Choice",
    "command",
    "InteractionContext",
    "InteractionData",
    "MessageCommand",
    "messagecommand",
    "Option",
    "SlashCommand",
    "slashcommand",
    "SubCommandGroup",
    "UserCommand",
    "usercommand"
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

class BaseCommand:
    __permissions__: tuple = ()
    def __repr__(self) -> str:
        return "<appcommands.models.{0.__class__.__name__} name={0.name} description={1}>".format(self, self.description)

    def __eq__(self, other: Any) -> bool:
        return self.name == other.name and self.description == other.description

    def _update_perms(self, data: Union[list, dict, tuple]) -> None:
        perms = list(perm for perm in self.__permissions__)
        if isinstance(data, dict):
            perms.append(data)
        elif isinstance(data, list):
            perms.extend(data)
        elif isinstance(data, tuple):
            perms.extend(list(i for i in data))

        self.__permissions__ = tuple(perm for perm in perms)

    def create_permission(self, id: int, type: int, value: bool) -> None:
        self._update_perms({"id": id, "type": type, "value": value})

class InteractionContext:
    """The ctx param given in CMD callbacks
    
    Attributes
    ------------
    bot: Union[:class:`~appcommands.client.Bot`, :class:`~appcommands.client.AutoShardedBot`]
        The appcommands bot instance
    type: :class:`~int`
        Interaction type 
    guild: Union[:class:`~discord.Guild`, None]
        The guild in which command is fired, None if it is in DMs 
    channel: Union[:class:`~discord.abc.GuildChannel`, :class:`~discord.DMChannel`]
        The channel in which command is triggered
    id: :class:`~int`
        id of this interaction
    user: Union[:class:`~discord.User`, :class:`~discord.Member`]
        The user who fired this cmd 
    token: :class:`~str`
        token of this interaction, (valid for 15 mins)"""
    def __init__(self, bot: Union['Bot', 'AutoShardedBot'], interaction) -> None:
        self.bot: Union[Bot, AutoShardedBot] = bot
        self._state = bot._connection
        self._session: ClientSession = self.bot.http._HTTPClient__session
        self.version: int = interaction.version
        self.type: int = interaction.type
        self.token: str = interaction.token
        self.id: int = interaction.id
        self.application_id: int = interaction.application_id
        self.kwargs: dict = {}
        self.interaction = interaction
        self.__invoked = False

    async def invoke(self, cmd) -> None:
        """|coro|

        The Coroutine that invokes commands

        .. versionadded:: 2.0

        Parameters
        -----------
        cmd: :class:`~appcommands.models.BaseCommand`
            The command which will be invoked
        """
        if self.__invoked:
            raise TypeError("This context has already been invoked, you can't invoke it again")

        self.command = cmd
        self.__invoked = True
        if cmd.type == 1:
            data = self.interaction.data
            data['bot'] = self.bot
            self.data: dict = InteractionData.from_dict(data)
            params = copy.deepcopy(cmd.params)
            if cmd.cog and str(list(params.keys())[0]) in ("cls", "self"): # cls/self only
                params.pop(list(params.keys())[0])
            self.kwargs[str(list(params.keys())[0])] = self
            params.pop(str(list(params.keys())[0]))
            self.kwargs = {**self.kwargs, **(await get_ctx_kw(self, params))}
            if cmd.cog:
                cog = self.bot.cogs.get(cmd.cog.qualified_name)
                if cog:
                    return await (getattr(cog, cmd.callback.__name__))(**self.kwargs)

            return await cmd.callback(**self.kwargs)

        elif cmd.type == 2:
            if "members" not in self.interaction.data["resolved"]:
                _data = self.interaction.data["resolved"]["users"]
                for i, v in _data.items():
                    v["id"] = int(i)
                    user = v
                target = discord.User(state=self.interaction._state, data=user)
            else:
                _data = self.interaction.data["resolved"]["members"]
                for i, v in _data.items():
                    v["id"] = int(i)
                    member = v
                _data = self.interaction.data["resolved"]["users"]
                for i, v in _data.items():
                    v["id"] = int(i)
                    user = v
                    member["user"] = user
                target = discord.Member(
                    data=member,
                    guild=self.interaction._state._get_guild(ctx.interaction.guild_id),
                    state=self.interaction._state,
                )
            if cmd.cog:
                cog = self.bot.cogs.get(cmd.cog.qualified_name)
                if cog:
                    return await (getattr(cog, cmd.callback.__name__))(self, target)
            return await cmd.callback(self, target)

        else:
            _data = self.interaction.data["resolved"]["messages"]
            for i, v in _data.items():
                v["id"] = int(i)
                message = v
            channel = self._state.get_channel(int(message["channel_id"]))
            if channel is None:
                u = discord.User(state=self._state, data=message['author'])
                channel = await u._get_channel()

            target = discord.Message(state=self.interaction._state, channel=channel, data=message)
            if cmd.cog:
                cog = self.bot.cogs.get(cmd.cog.qualified_name)
                if cog:
                    return await (getattr(cog, cmd.callback.__name__))(self, target)
            return await cmd.callback(self, target)


    @cached_property
    def channel(self) -> Union[discord.abc.GuildChannel, discord.DMChannel, None]:
        return self.interaction.channel

    @cached_property
    def channel_id(self) -> int:
        return self.interaction.channel_id

    @cached_property
    def guild(self) -> Union[discord.Guild, None]:
        return self.interaction.guild

    @cached_property
    def guild_id(self) -> int:
        return self.interaction.guild_id

    @cached_property
    def message(self) -> discord.InteractionMessage:
        return self.interaction.message

    @cached_property
    def user(self) -> Union[discord.User, discord.Member]:
        return self.interaction.user

    @cached_property
    def response(self) -> discord.InteractionResponse:
        return self.interaction.response

    author = user

    @property
    def respond(self) -> Coroutine:
        return self.interaction.response.send_message

    @property
    def edit(self) -> Coroutine:
        return self.interaction.edit_original_message

    @property
    def send(self) -> Coroutine:
        if not self.response.is_done():
            return self.respond

        return self.channel.send

    @property
    def defer(self) -> Coroutine:
        return self.interaction.response.defer

    @property
    def followup(self) -> Coroutine:
        return self.interaction.followup


class InteractionData:
    """The data given for slash commands in `ctx.data`

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
    def __init__(self, type: int, name: str, id: int, options: Optional[List['Option']] = None) -> None:
        self.type = type
        self.name = name
        self.id = int(id)
        self.options = options

    def __repr__(self) -> str:
        return f"<InteractionData type={self.type} id={self.id} name={self.name} options={self.options}>"

    def __str__(self) -> str:
        return self.__repr__()

    @classmethod
    def from_dict(cls, d: dict) -> 'InteractionData':
        options = []
        bot=d.pop('bot')
        if int(d.get('id')) in bot.subcommands:
            for i in d.get('options'):
                if i['type'] == 2:
                    data = i["options"][0]
                else:
                    data = i
        else:
            data = d
        if data.get('options'):
            for i in data.get('options'):
                options.append(Option.from_dict(i))
        
        return cls(d['type'], data['name'], d['id'], options)

class Choice:
    """Choice for the option value 
    
    Parameters 
    ------------
    name: :class:`~str`
        name of the choice, (required)
    value: Optional[:class:`~str`]
        value of the choice used for backends, (optional)"""
    def __init__(self, name: str, value: Optional[str] = None) -> None:
        self.name = name
        self.value = value or self.name

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "value": self.value}

    def __repr__(self) -> str:
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
                 choices: Optional[List[Choice]] = []) -> None:
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
    def from_dict(cls, data) -> 'Option':
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

    def __repr__(self) -> str:
        return f"<Option name={self.name} description={self.description} type={self.type} required={self.required} value={self.value} choices={self.choices}>"

class SlashCommand(BaseCommand):
    """SlashCmd wrapper class 
    
    Parameters
    ------------
    name: :class:`~str`
       Name of the cmd, (required)
    description: Optional[:class:`~str`]
       description of the cmd, (optional)
    guild_ids: Optional[List[:class:`~int`]]
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
        Name not given when call not given
    """
    def __new__(cls, *args, **kwargs) -> 'SlashCommand':
        self = super().__new__(cls)

        self.__original_kwargs__ = kwargs.copy()
        return self

    def __init__(self,
                 name: str = None,
                 description: Optional[str] = "No description.",
                 guild_ids: Optional[List[int]] = None,
                 options: Optional[List[Option]] = [],
                 callback: Optional[Coroutine] = None) -> None:
        self.options: str = options
        self.description: str = description
        self.guild_ids: List[int] = guild_ids
        self.cog = None
        self.type: int = 1
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

    def __str__(self) -> str:
        return self.__repr__()

    def to_dict(self) -> dict:
        ret = {
            "name": self.name,
            "description": self.description,
            "options": list(d.to_dict() for d in self.options)
        }
        if self.is_subcommand:
            ret["type"] = OptionType.SUB_COMMAND.value
        return ret

    def __eq__(self, other: BaseCommand):
        return self.name == other.name and self.description == other.description

    @missing
    async def callback(self, ctx: InteractionContext) -> Any:
        raise NotImplementedError

class SubCommandGroup(BaseCommand):
    """SubCommand wrapper class

    .. versionadded:: 2.0

    Parameters
    ------------
    name: :class:`~str`
        Name of the group
    guild_ids: Optional[List[:class:`~int`]]
        Guild ids for which cmd is to be added
    """
    def __init__(self,
                 name: str = None,
                 guild_ids: Optional[List[int]] = [],
                 parent = None) -> None:
        self.parent = parent
        self.name: str = name
        self.description: str = ""
        self.guild_ids: List[int] = guild_ids
        self.type: int = 1
        self.subcommands: List[Union[SubCommandGroup, SlashCommand]] = []

    def subcommand(self, *args, cls=MISSING, **kwargs) -> Callable[[Callable], SlashCommand]:
        if cls is MISSING:
            cls = SlashCommand
        def wrap(func) -> SlashCommand:
            command = cls(*args, callback=func, **kwargs)
            command.is_subcommand = True
            command.__func__ = func
            self.subcommands.append(command)
            return command

        return wrap

    def __eq__(self, other: BaseCommand) -> bool:
        return self.name == other.name and self.description == other.description

    def subcommandgroup(self, name: str) -> 'SubCommandGroup':
        """The group for which more subcommand is to be added

        Parameters
        ------------
        name: :class:`~str`
            Name of this group"""
        if self.parent is not None:
            raise TypeError("Subcommand groups can't have more groups")

        sub_command_group = SubCommandGroup(name, description, parent=self)
        self.subcommands.append(sub_command_group)
        return sub_command_group

    def to_dict(self) -> dict:
        ret = {
            "name": self.name,
            "description": self.description,
            "options": [o.to_dict() for o in self.subcommands]
        }
        if self.parent is not None:
            ret["type"] = OptionType.SUB_COMMAND_GROUP.value
        return ret

    def __repr__(self) -> str:
        return "<SubCommandGroup name={0.name} description={1} subcommands={0.subcommands}>".format(self, self.description)

class UserCommand(BaseCommand):
    """Context-Menu user command wrapper class

    .. versionadded:: 2.0
    
    Parameters
    ------------
    name: :class:`~str`
       Name of the cmd, (required)
    guild_ids: Optional[List[:class:`~int`]]
       id of the guild for which command is to be added, (optional)
    callback: Optional[Coroutine]
       the callback which is to be called when a command fires, (optional)
       
    Raises 
    --------
    TypeError 
        Callback is not coroutine
    ValueError 
        Name not given when call not given
    """
    def __new__(cls, *args, **kwargs) -> 'UserCommand':
        self = super().__new__(cls)

        self.__original_kwargs__ = kwargs.copy()
        return self

    def __init__(
        self,
        name: str = None,
        guild_ids: Optional[List[int]] = [],
        callback: Optional[Coroutine] = None
    ) -> None:
        self.type: int = 2
        self.description = ""
        self.cog = None
        self.guild_ids: Optional[List[int]] = guild_ids
        if callback:
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError('Callback must be a coroutine.')
            self.name = name or callback.__name__
            self.callback = callback
        elif (hasattr(self, 'callback') and self.callback is not MISSING):
            if not callback:
                callback = self.callback
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError('Callback must be a coroutine.')
            self.name = name or self.__class__.__name__
        else:
            if not name:
                raise ValueError("You must specify name when callback is None")
            self.name  = name

    @missing
    async def callback(self, ctx, usr):
        raise NotImplementedError

    def __repr__(self) -> str:
        return "<UserCommand name={0.name} guild_ids={0.guild_ids}>".format(self)

    def to_dict(self) -> Dict[str, Union[str, int]]:
        return {"name": self.name, "description": "", "type": self.type}

class MessageCommand(BaseCommand):
    """Context-menu message wrapper class

    .. versionadded:: 2.0

    Parameters
    ------------
    name: :class:`~str`
       Name of the cmd, (required)
    guild_ids: Optional[List[:class:`~int`]]
       id of the guild for which command is to be added, (optional)
    callback: Optional[Coroutine]
       the callback which is to be called when a command fires, (optional)
       
    Raises 
    --------
    TypeError 
        Callback is not coroutine
    ValueError 
        Name not given when call not given
    """
    def __new__(cls, *args, **kwargs) -> 'MessageCommand':
        self = super().__new__(cls)

        self.__original_kwargs__ = kwargs.copy()
        return self

    def __init__(self,
        name: str = None,
        guild_ids: Optional[List[int]] = [],
        callback: Optional[Coroutine] = None
    ) -> None:
        self.type: int = 3
        self.description = ""
        self.cog = None
        self.guild_ids: Optional[List[int]] = guild_ids
        if callback:
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError('Callback must be a coroutine.')
            self.name = name or callback.__name__
            self.callback = callback
        elif (hasattr(self, 'callback') and self.callback is not MISSING):
            if not callback:
                callback = self.callback
            if not asyncio.iscoroutinefunction(callback):
                raise TypeError('Callback must be a coroutine.')
            self.name = name or self.__class__.__name__
        else:
            if not name:
                raise ValueError("You must specify name when callback is None")
            self.name  = name

    def to_dict(self) -> Dict[str, Union[str, int]]:
        return {"name": self.name, "description": self.description, "type": self.type}

    def __repr__(self) -> str:
        return "<MessageCommand name={0.name} guild_ids={0.guild_ids}>".format(self)

    @missing
    async def callback(self, ctx, msg):
        raise NotImplementedError

def command(cls: BaseCommand = MISSING, **kwargs) -> Callable[[Callable], BaseCommand]:
    """The appcommands wrapper 
    
    Parameters
    ------------
    name: :class:`~str`
        Name of the command, (required)
    description: Optional[:class:`~str`]
        Description of the command, Only for slashcommands
    guild_ids: Optional[List[:class:`~int`]]
        Id of the guild for which command is to be added, (optional)
    options: Optional[List[:class:`~appcommands.models.Option`]]
        Options for the command, detects automatically if not given, Only for slashcommands
    cls: :class:`~appcommands.models.BaseCommand`
        The custom command class, must be a subclass of :class:`~appcommands.models.BaseCommand`, (optional)

    Example
    ----------
    
    .. code-block:: python3
    
        from appcommands import command
        
        @command(name="hi", description="Hello!")
        async def hi(ctx, user: discord.Member = None):
            user = user or ctx.user
            await ctx.send(f"Hi {user.mention}")

    Raises
    --------
    TypeError
        The passed callback is not coroutine or it is already an AppCommand
    """
    if cls is MISSING:
        cls = SlashCommand

    def wrapper(func) -> BaseCommand:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError('Callback must be a coroutine.')
        if isinstance(func, BaseCommand):
            raise TypeError('Callback is already a appcommand.')

        result = cls(callback=func, **kwargs)
        result.__func__ = func
        return result

    return wrapper

def slashcommand(cls: SlashCommand = MISSING, **kwargs) -> Callable[[Callable], SlashCommand]:
    """The slash command wrapper

    .. versionadded:: 2.0

    Parameters
    ------------
    name: :class:`~str`
        Name of the command, (required)
    description: Optional[:class:`~str`]
        Description of the command, (optional)
    guild_ids: Optional[List[:class:`~int`]]
        Id of the guild for which command is to be added, (optional)
    options: Optional[List[:class:`~appcommands.models.Option`]]
        Options for the command, detects automatically if not given, (optional)
    cls: :class:`~appcommands.models.SlashCommand`
        The custom command class, must be a subclass of :class:`~appcommands.models.SlashCommand`, (optional)

    Example
    ----------
    
    .. code-block:: python3
    
        from appcommands import slashcommand
        
        @slashcommand(name="hi", description="Hello!")
        async def hi(ctx, user: discord.Member = None):
            user = user or ctx.user
            await ctx.send(f"Hi {user.mention}")

    Raises
    --------
    TypeError
        The passed callback is not coroutine or it is already an AppCommand
    """
    if cls is MISSING:
       cls = SlashCommand

    return command(cls=cls, **kwargs)

def usercommand(cls: UserCommand = MISSING, **kwargs) -> Callable[[Callable], SlashCommand]:
    """The user command wrapper

    .. versionadded:: 2.0

    Parameters
    ------------
    name: :class:`~str`
        Name of the command, (required)
    guild_ids: Optional[List[:class:`~int`]]
        Id of the guild for which command is to be added, (optional)
    cls: :class:`~appcommands.models.UserCommand`
        The custom command class, must be a subclass of :class:`~appcommands.models.SlashCommand`, (optional)

    Example
    ----------
    
    .. code-block:: python3
    
        from appcommands import usercommand
        
        @usercommand(name="hi")
        async def mention(ctx, user: discord.Member);
            await ctx.send(f"{ctx.author.mention} mentioned {user.mention}")

    Raises
    --------
    TypeError
        The passed callback is not coroutine or it is already an AppCommand
    """
    if cls is MISSING:
        cls = UserCommand

    return command(cls=cls, **kwargs)

def messagecommand(cls: MessageCommand = MISSING, **kwargs) -> Callable[[Callable], SlashCommand]:
    """The message command wrapper 

    .. versionadded:: 2.0

    Parameters
    ------------
    name: :class:`~str`
        Name of the command, (required)
    guild_ids: Optional[List[:class:`~int`]]
        Id of the guild for which command is to be added, (optional)
    cls: :class:`~appcommands.models.MessageCommand`
        The custom command class, must be a subclass of :class:`~appcommands.models.MessageCommand`, (optional)

    Example
    ----------
    
    .. code-block:: python3
    
        from appcommands import messagecommand
        
        @messagecommand(name="hi")
        async def mention(ctx, message: discord.Message):
            await ctx.send(f"{message.id}")

    Raises
    --------
    TypeError
        The passed callback is not coroutine or it is already an AppCommand
    """
    if cls is MISSING:
        cls = MessageCommand

    return command(cls=cls, **kwargs)

def slashgroup(**kwargs) -> SubCommandGroup:
    """The slash subcommand group wrapper

    .. versionadded:: 2.0

    Parameters
    ------------
    name: :class:`~str`
        Name of the command
    guild_ids: Optional[List[:class:`~int`]]
        List of the guilds for command, (optional)

    Example
    ---------

    .. code-block:: python3

        from appcommands import slashgroup

        misc = slashgroup(name="misc", guild_ids=[...])
        @misc.subcommand()
        async def ping(ctx):
            await ctx.send(bot.latency)

    Returns
    ---------
    :class:`~appcommands.models.SubCommandGroup`
        The SubCommandGroup which will be returned
    """
    return SubCommandGroup(**kwargs)
