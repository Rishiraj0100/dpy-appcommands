.. currentmodule:: appcommands

API Reference
=============

SubModules

appcommands.client Module
----------------------------------

.. currentmodule:: appcommands.client

.. autoclass:: Bot
    :members: add_app_command, remove_app_command, appcommands, slashcommands, subcommands, messagecommands, usercommands, register_commands, slashgroup

    .. automethod:: slashcommand

    .. automethod:: messagecommand

    .. automethod:: usercommand

.. autoclass:: AutoShardedBot
    :members:

appcommands.models Module
----------------------------------

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

.. autoclass:: UserCommand
    :members:

.. autoclass:: MessageCommand
    :members:

.. automethod:: appcommands.models.command()

.. automethod:: appcommands.models.slashcommand()

.. automethod:: appcommands.models.usercommand()

.. automethod:: appcommands.models.messagecommand()


appcommands.cog Module
----------------------------------

.. currentmodule:: appcommands.cog

.. autoclass:: SlashCog

appcommands.enums Module
----------------------------------

.. currentmodule:: appcommands.enums

.. autoclass:: OptionType
    :members:

