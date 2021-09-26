.. currentmodule:: appcommands

API Reference
=============

The following section outlines the API of appcommands module

Bots
-----

Bot
~~~~

.. attributetable:: appcommands.client.Bot

.. autoclass:: appcommands.client.Bot
    :members: add_app_command, remove_app_command, appcommands, slashcommands, subcommands, messagecommands, usercommands, register_commands, slashgroup

    .. automethod:: Bot.slashcommand(**kwargs)
        :decorator:

    .. automethod:: Bot.messagecommand(**kwargs)
        :decorator:

    .. automethod:: Bot.usercommand(**kwargs)
        :decorator:

AutoShardedBot
~~~~~~~~~~~~~~~~

.. attributetable:: appcommands.client.AutoShardedBot

.. autoclass:: AutoShardedBot
    :members:


Commands
----------

Decorators
~~~~~~~~~~~~

.. autofunction:: appcommands.models.command
    :decorator:

.. autofunction:: appcommands.models.messagecommand
    :decorator:

.. autofunction:: appcommands.models.slashcommand
    :decorator:

.. autofunction:: appcommands.models.usercommand
    :decorator:

Commands
~~~~~~~~~~~

.. currentmodule:: appcommands.models

.. attributetable:: SlashCommand

.. autoclass:: SlashCommand
    :members:

.. attributetable:: SubCommandGroup

.. autoclass:: SubCommandGroup
    :members:
    :exclude-members: subcommand

    .. automethod:: SubCommandGroup.subcommand(**kwargs)
        :decorator:

.. autoclass:: MessageCommand
    :members:

.. autoclass:: UserCommand
    :members:

Module References
------------------

appcommands.models Module Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: appcommands.models

.. attributetable:: InteractionContext

.. autoclass:: InteractionContext
    :members:

.. attributetable:: Choice

.. autoclass:: Choice
    :members:

.. attributetable:: Option

.. autoclass:: Option
    :members:


appcommands.cog Module Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: appcommands.cog

.. autoclass:: Cog

appcommands.enums Module Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: appcommands.enums

.. autoclass:: OptionType
    :members:

