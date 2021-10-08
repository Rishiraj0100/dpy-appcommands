.. currentmodule:: appcommands

API Reference
=============

The following section outlines the API of appcommands module

Bots
-----

Bot
~~~~

.. attributetable:: appcommands.Bot

.. autoclass:: appcommands.Bot
    :members: add_app_command, remove_app_command, appcommands, slashcommands, subcommands, messagecommands, usercommands, register_commands

    .. automethod:: Bot.slashcommand(**kwargs)
        :decorator:

    .. automethod:: Bot.messagecommand(**kwargs)
        :decorator:

    .. automethod:: Bot.usercommand(**kwargs)
        :decorator:

    .. automethod:: Bot.slashgroup

AutoShardedBot
~~~~~~~~~~~~~~~~

.. attributetable:: appcommands.AutoShardedBot

.. autoclass:: appcommands.AutoShardedBot
    :members:


Commands
----------

Decorators
~~~~~~~~~~~~

.. autofunction:: appcommands.command
    :decorator:

.. autofunction:: appcommands.messagecommand
    :decorator:

.. autofunction:: appcommands.slashcommand
    :decorator:

.. autofunction:: appcommands.usercommand
    :decorator:


Commands
~~~~~~~~~~~

.. attributetable:: appcommands.SlashCommand

.. autoclass:: appcommands.SlashCommand

    .. automethod:: SlashCommand.callback

.. attributetable:: appcommands.SubCommandGroup

.. autoclass:: appcommands.SubCommandGroup
    :members:
    :exclude-members: subcommand

    .. automethod:: SubCommandGroup.subcommand(**kwargs)
        :decorator:

.. attributetable:: appcommands.MessageCommand

.. autoclass:: appcommands.MessageCommand

    .. automethod:: MessageCommand.callback

.. attributetable:: appcommands.UserCommand

.. autoclass:: appcommands.UserCommand

    .. automethod:: UserCommand.callback

Checks
~~~~~~~

.. automethod:: appcommands.blacklist_roles()

.. automethod:: appcommands.blacklist_users()

.. automethod:: appcommands.whitelist_roles()

.. automethod:: appcommands.whitelist_users()

More References
----------------

Contexts
~~~~~~~~~~

.. attributetable:: appcommands.InteractionContext

.. autoclass:: appcommands.InteractionContext
    :members:

Options
~~~~~~~~
.. attributetable:: appcommands.Choice

.. autoclass:: appcommands.Choice
    :members:

.. attributetable:: appcommands.Option

.. autoclass:: appcommands.Option
    :members:

Cogs
~~~~~

.. autoclass:: appcommands.Cog

.. autoclass:: appcommands.CogMeta

