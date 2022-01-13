import copy
import typing
import discord
import asyncio
import inspect
import functools

from .utils import *
from .enums import OptionType, PermissionType

from discord import ui, http
from aiohttp.client import ClientSession
from discord.utils import cached_property, copy_doc
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
    "blacklist_roles",
    "blacklist_users",
    "Choice",
    "command",
    "InteractionContext",
    "InteractionData",
    "MessageCommand",
    "messagecommand",
    "Option",
    "SlashCommand",
    "slashcommand",
    "slashgroup",
    "SubCommandGroup",
    "UserCommand",
    "usercommand",
    "whitelist_roles",
    "whitelist_users"
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
    __permissions__: list = []
    all_guilds: bool = False
    def __repr__(self) -> str:
        return "<appcommands.core.{0.__class__.__name__} name={0.name} description={1}>".format(self, self.description)

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

        self.__permissions__ = list(perm for perm in perms)

    def create_permission(self, id: int, type: PermissionType, permission: bool) -> dict:
        d = {"id": str(id), "type": int(type), "permission": permission}
        self._update_perms(d)
        return d

    def generate_permissions(
        self,
        *,
        allowed_roles: List[int] = [],
        allowed_users: List[int] = [],
        disallowed_roles: List[int] = [],
        disallowed_users: List[int] = []
    ) -> None:
        permissions = []

        if allowed_roles:
            permissions.extend(
                [self.create_permission(id, PermissionType.ROLE.value, True) for id in set(allowed_roles)]
            )
        if allowed_users:
            permissions.extend(
                [self.create_permission(id, PermissionType.USER.value, True) for id in set(allowed_users)]
            )
        if disallowed_roles:
            permissions.extend(
                [self.create_permission(id, PermissionType.ROLE.value, False) for id in set(disallowed_roles)]
            )
        if disallowed_users:
            permissions.extend(
                [self.create_permission(id, PermissionType.USER.value, False) for id in set(disallowed_users)]
            )

        self._update_perms(permissions)

    async def __call__(self, *args, **kwargs):
        if not hasattr(self, callback): raise TypeError(f"'{self.__class__.__name__}' object is not callable")
        if self.cog: args = [self.cog] + args
        return await self.callback(*args, **kwargs)


class InteractionContext:
    """The ctx param given in CMD callbacks
    
    Attributes
    ------------
    bot: Union[:class:`appcommands.Bot`, :class:`appcommands.AutoShardedBot`]
        The appcommands bot instance
    type: :class:`~int`
        Interaction type 
    guild: Union[:class:`discord.Guild`, None]
        The guild in which command is fired, None if it is in DMs 
    channel: Union[:class:`discord.abc.GuildChannel`, :class:`discord.DMChannel`]
        The channel in which command is triggered
    id: :class:`~int`
        id of this interaction
    user: Union[:class:`discord.User`, :class:`discord.Member`]
        The user who fired this cmd 
    token: :class:`~str`
        token of this interaction, (valid for 15 mins)
    """
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

        This function invokes commands

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
                    try:
                        instance = getattr(cog, cmd.callback.__name__)
                    except:
                        return await cmd.__func__(**self.kwargs)
                    else:
                        return await instance(**self.kwargs)

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
                    try:
                        instance = getattr(cog, cmd.callback.__name__)
                    except:
                        return await cmd.__func__(self, target)
                    else:
                        return await instance(self, target)

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
                    try:
                        instance = getattr(cog, cmd.callback.__name__)
                    except:
                        return await cmd.__func__(self, target)
                    else:
                        return await instance(self, target)

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

    @property
    def message(self) -> discord.InteractionMessage:
        return self.interaction._original_message

    @cached_property
    def user(self) -> Union[discord.User, discord.Member]:
        return self.interaction.user

    @cached_property
    def response(self) -> discord.InteractionResponse:
        return self.interaction.response

    author = user

    async def respond(self, *args, **kwargs) -> Coroutine:
        """|coro|

        Responds to this interaction by sending a message.

        Parameters
        -----------
        content: Optional[:class:`str`]
            The content of the message to send.
        embeds: List[:class:`discord.Embed`]
            A list of embeds to send with the content. Maximum of 10. This cannot
            be mixed with the ``embed`` parameter.
        embed: :class:`discord.Embed`
            The rich embed for the content to send. This cannot be mixed with
            ``embeds`` parameter.
        tts: :class:`bool`
            Indicates if the message should be sent using text-to-speech.
        view: :class:`discord.ui.View`
            The view to send with the message.
        ephemeral: :class:`bool`
            Indicates if the message should only be visible to the user who started the interaction.
            If a view is sent with an ephemeral message and it has no timeout set then the timeout
            is set to 15 minutes.

        Raises
        -------
        discord.HTTPException
            Sending the message failed.
        TypeError
            You specified both ``embed`` and ``embeds``.
        ValueError
            The length of ``embeds`` was invalid.
        discord.InteractionResponded
            This interaction has already been responded to before.

        Returns
        --------
        :class:`discord.InteractionMessage`
            The newly sent message.
        """
        await self.interaction.response.send_message(*args, **kwargs)
        return await self.interaction.original_message()

    def edit(self, *args, **kwargs):
        """|coro|

        Edits the original interaction response message.

        Parameters
        ------------
        content: Optional[:class:`str`]
            The content to edit the message with or ``None`` to clear it.
        embeds: List[:class:`discord.Embed`]
            A list of embeds to edit the message with.
        embed: Optional[:class:`discord.Embed`]
            The embed to edit the message with. ``None`` suppresses the embeds.
            This should not be mixed with the ``embeds`` parameter.
        file: :class:`File`
            The file to upload. This cannot be mixed with ``files`` parameter.
        files: List[:class:`discord.File`]
            A list of files to send with the content. This cannot be mixed with the
            ``file`` parameter.
        allowed_mentions: :class:`discord.AllowedMentions`
            Controls the mentions being processed in this message.
            See :meth:`discord.abc.Messageable.send` for more information.
        view: Optional[:class:`~discord.ui.View`]
            The updated view to update this message with. If ``None`` is passed then
            the view is removed.

        Raises
        -------
        discord.HTTPException
            Editing the message failed.
        discord.Forbidden
            Edited a message that is not yours.
        TypeError
            You specified both ``embed`` and ``embeds`` or ``file`` and ``files``
        ValueError
            The length of ``embeds`` was invalid.

        Returns
        --------
        :class:`discord.InteractionMessage`
            The newly edited message.
        """
        return self.interaction.edit_original_message(*args, **kwargs)

    def send(self, *args, **kwargs):
        """|coro|

        If interaction is not responded, then this function responds it,
        or if it is already responded then it sends a message to current channel
        """
        if not self.response.is_done():
            return self.respond(*args, **kwargs)

        return self.channel.send(*args, **kwargs)

    @copy_doc(respond)
    def reply(self, *args, **kwargs):
        return self.respond(*args, **kwargs)

    def defer(self, *args, **kwargs):
        """|coro|

        Defers the interaction response.

        This is typically used when the interaction is acknowledged
        and a secondary action will be done later.

        Parameters
        -----------
        ephemeral: :class:`bool`
            Indicates whether the deferred message will eventually be ephemeral.
            This only applies for interactions of type `discord.InteractionType.application_command`.

        Raises
        -------
        discord.HTTPException
            Deferring the interaction failed.
        discord.InteractionResponded
            This interaction has already been responded to before.
        """
        return self.interaction.response.defer(*args, **kwargs)


    def followup(self, *args, **kwargs) -> Coroutine:
        """:class:`discord.Webhook`: Returns the follow up webhook for follow up interactions."""
        return self.interaction.followup(*args, **kwargs)


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
    options: List[:class:`appcommands.Option`]
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
    choices: Optional[List[:class:`appcommands.Choice`]]
        The choices for this option
    """
    def __init__(
        self,
        name: str,
        description: Optional[str] = "No description.",
        type: Optional[int] = 3,
        required: Optional[bool] = True,
        value: str = None,
        choices: Optional[List[Choice]] = []
    ) -> None:
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
    options: Optional[List[:class:`appcommands.Option`]]
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
        self.parent=None
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
        elif (hasattr(self, 'callback') and ( not (self.callback == MISSING))):
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
        """This function should be a Coroutine.

        This is invoked when a command is called.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return "<SlashCommand name={0.name} description={0.description} options={0.options}>".format(self)

    @property
    def full_name(self):
        if not self.parent: return self.name
        if not self.parent.parent: return self.parent.name + " " + self.name
        return self.parent.parent.name + " " + self.parent.name + " " + self.name

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
    def __init__(
        self,
        name: str,
        description: str = "No Description given.",
        guild_ids: Optional[List[int]] = [],
        parent = None
    ) -> None:
        self.parent = parent
        self.name: str = name
        self.description: str = description
        self.guild_ids: List[int] = guild_ids
        self.type: int = 1
        self.subcommands: List[Union[SubCommandGroup, SlashCommand]] = []

    def subcommand(self, *args, cls=MISSING, **kwargs) -> Callable[[Callable], SlashCommand]:
        r"""A decorator which adds subcommands in the group commands

        .. versionadded:: 2.0

        Parameters
        -----------
        name: :class:`~str`
            name of the command, defaults to function name, (required)
        description: Optional[:class:`~str`]
            description of the command, required
        guild_ids: Optional[List[:class:`~int`]]
            list of ids of the guilds for which command is to be added, (optional)
        options: Optional[List[:class:`appcommands.Option`]]
            the options for command, can be empty
        cls: :class:`appcommands.SlashCommand`
            The custom command class, must be a subclass of :class:`appcommands.SlashCommand`, (optional)

        Example
        ---------

        .. code-block:: python3

            @group.subcommand(name="Hi", description="Hello!")
            async def some_func(ctx):
                await ctx.send("Hello!")

        Raises
        --------
        TypeError
           The passed callback is not coroutine
        """
        if cls is MISSING:
            cls = SlashCommand
        def wrap(func) -> SlashCommand:
            if not asyncio.iscoroutinefunction(func):
                raise TypeError('Callback must be a coroutine.')
            command = cls(*args, callback=func, **kwargs)
            command.is_subcommand, command.parent = True, self
            command.__func__ = func
            self.subcommands.append(command)
            return command

        return wrap

    def __eq__(self, other: BaseCommand) -> bool:
        return self.name == other.name and self.description == other.description

    def subcommandgroup(self, name: str, description: str = "No Description") -> 'SubCommandGroup':
        """The slashgroup for which more subcommand is to be added

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
        elif (hasattr(self, 'callback') and ( not (self.callback == MISSING))):
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
    async def callback(self, ctx, user):
        """This function should be a Coroutine.

        This is invoked when a command is called.
        """
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
        elif (hasattr(self, 'callback') and ( not (self.callback == MISSING))):
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
    async def callback(self, ctx, message):
        """This function should be a Coroutine.

        This is invoked when a command is called.
        """
        raise NotImplementedError

def blacklist_roles(*roles) -> Callable[[Callable], Callable]:
    r"""A decorator which blacklists some roles from
    the command

    Parameters
    -----------
    \*roles
      The id of roles which can't use the command

    Example
    --------

    .. code-block:: python3

        r1, r2 = "Id of 1st role", "Id of 2nd role"

        @bot.slashcommand()
        @appcommands.blacklist_roles(r1, r2)
        async def hi(ctx):
            await ctx.send('tested')
    """
    def wrapper(func) -> Callable:
        if isinstance(func, BaseCommand):
            func.generate_options(disallowed_roles=roles)
        return func
    return wrapper

def whitelist_roles(*roles) -> Callable[[Callable], Callable]:
    r"""A decorator which whitelists some roles only
    to use the command

    Parameters
    -----------
    \*roles
      The id of roles which can use the command

    Example
    --------

    .. code-block:: python3

        r1, r2 = "Id of 1st role", "Id of 2nd role"

        @bot.slashcommand()
        @appcommands.whitelist_roles(r1, r2)
        async def hi(ctx):
            await ctx.send('tested')
    """
    def wrapper(func) -> Callable:
        if isinstance(func, BaseCommand):
            func.generate_options(allowed_roles=roles)
        return func
    return wrapper

def blacklist_users(*users) -> Callable[[Callable], Callable]:
    r"""A decorator which blacklists some users
    from the command

    Parameters
    -----------
    \*users
      The id of users which can't use the command

    Example
    --------

    .. code-block:: python3

        u1, u2 = "Id of 1st user", "Id of 2nd user"

        @bot.slashcommand()
        @appcommands.blacklist_users(u1, u2)
        async def hi(ctx):
            await ctx.send('tested')
    """
    def wrapper(func) -> Callable:
        if isinstance(func, BaseCommand):
            func.generate_options(disallowed_users=users)
        return func
    return wrapper

def whitelist_users(*users) -> Callable[[Callable], Callable]:
    r"""A decorator which whitelists some users only
    to use the command

    Parameters
    -----------
    \*users
      The id of users which can use the command

    Example
    --------

    .. code-block:: python3

        u1, u2 = "Id of 1st user", "Id of 2nd user"

        @bot.slashcommand()
        @appcommands.whitelist_users(u1, u2)
        async def hi(ctx):
            await ctx.send('tested')
    """
    def wrapper(func) -> Callable:
        if isinstance(func, BaseCommand):
            func.generate_options(allowed_users=users)
        return func
    return wrapper

def command(cls: BaseCommand = MISSING, **kwargs) -> Callable[[Callable], BaseCommand]:
    """A decorator for application commands wrapper 
    
    Parameters
    ------------
    name: :class:`~str`
        Name of the command, (required)
    description: Optional[:class:`~str`]
        Description of the command, Only for slashcommands
    guild_ids: Optional[List[:class:`~int`]]
        Id of the guild for which command is to be added, (optional)
    options: Optional[List[:class:`appcommands.Option`]]
        Options for the command, detects automatically if not given, Only for slashcommands
    cls: :class:`appcommands.BaseCommand`
        The custom command class, must be a subclass of :class:`appcommands.BaseCommand`, (optional)

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
    """A decorator for slash commands wrapper

    .. versionadded:: 2.0

    Parameters
    ------------
    name: :class:`~str`
        Name of the command, (required)
    description: Optional[:class:`~str`]
        Description of the command, (optional)
    guild_ids: Optional[List[:class:`~int`]]
        Id of the guild for which command is to be added, (optional)
    options: Optional[List[:class:`appcommands.Option`]]
        Options for the command, detects automatically if not given, (optional)
    cls: :class:`appcommands.SlashCommand`
        The custom command class, must be a subclass of :class:`appcommands.SlashCommand`, (optional)

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

def usercommand(cls: UserCommand = MISSING, **kwargs) -> Callable[[Callable], UserCommand]:
    """A decorator for Context-Menu user commands wrapper

    .. versionadded:: 2.0

    Parameters
    ------------
    name: :class:`~str`
        Name of the command, (required)
    guild_ids: Optional[List[:class:`~int`]]
        Id of the guild for which command is to be added, (optional)
    cls: :class:`appcommands.UserCommand`
        The custom command class, must be a subclass of :class:`appcommands.UserCommand`, (optional)

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

def messagecommand(cls: MessageCommand = MISSING, **kwargs) -> Callable[[Callable], MessageCommand]:
    """A decorator for Context-Menu message commands wrapper 

    .. versionadded:: 2.0

    Parameters
    ------------
    name: :class:`~str`
        Name of the command, (required)
    guild_ids: Optional[List[:class:`~int`]]
        Id of the guild for which command is to be added, (optional)
    cls: Optional[:class:`appcommands.MessageCommand`]
        The custom command class, must be a subclass of :class:`appcommands.MessageCommand`, (optional)

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
    :class:`appcommands.SubCommandGroup`
        The SubCommandGroup which will be returned
    """
    return SubCommandGroup(**kwargs)
