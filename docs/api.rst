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
    :members: add_app_command, remove_app_command, appcommands, slashcommands, subcommands, messagecommands, usercommands, register_commands, slashgroup

    .. automethod:: Bot.slashcommand(**kwargs)
        :decorator:

    .. automethod:: Bot.messagecommand(**kwargs)
        :decorator:

    .. automethod:: Bot.usercommand(**kwargs)
        :decorator:

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
    :members:

.. attributetable:: appcommands.SubCommandGroup

.. autoclass:: Sappcommands.ubCommandGroup
    :members:
    :exclude-members: subcommand

    .. automethod:: SubCommandGroup.subcommand(**kwargs)
        :decorator:

.. autoclass:: appcommands.MessageCommand
    :members:

.. autoclass:: appcommands.UserCommand
    :members:

Module References
------------------

appcommands.models Module Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. attributetable:: appcommands.InteractionContext

.. autoclass:: appcommands.InteractionContext
    :members:

.. attributetable:: appcommands.Choice

.. autoclass:: appcommands.Choice
    :members:

.. attributetable:: appcommands.Option

.. autoclass:: appcommands.Option
    :members:


appcommands.cog Module Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: appcommands.Cog

appcommands.enums Module Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. attributetable:: appcommands.OptionType

.. autoclass:: appcommands.OptionType
    :members:

