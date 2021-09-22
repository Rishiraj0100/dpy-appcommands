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

.. autoclass:: InteractionContext
    :members:

.. autoclass:: Choice
    :members:

.. autoclass:: Option
    :members:

.. autoclass:: SlashCommand
    :members:

.. autoclass:: SubCommandGroup
    :members:
    :exclude-members: subcommand

    .. automethod:: SubCommandGroup.subcommand()
        :decorator:

.. autoclass:: UserCommand
    :members:

.. autoclass:: MessageCommand
    :members:

.. automethod:: appcommands.models.command(**kwargs)
    :decorator:

.. autofunction:: appcommmands.models.slashgroup

.. automethod:: appcommands.models.slashcommand(**kwargs)
    :decorator:

.. automethod:: appcommands.models.usercommand(**kwargs)
    :decorator:

.. automethod:: appcommands.models.messagecommand()
    :decorator:


appcommands.cog Module Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: appcommands.cog

.. autoclass:: App

appcommands.enums Module Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: appcommands.enums

.. autoclass:: OptionType
    :members:

