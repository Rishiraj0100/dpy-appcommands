:orphan:

.. currentmodule:: appcommands
.. _faq:

Frequently Asked Questions
===========================

This is a list of Frequently Asked Questions regarding using ``dpy-appcommands``. Feel free to suggest a
new question or submit one via pull requests.

.. contents:: Questions
    :local:

General
--------

How do I make a Bot?
~~~~~~~~~~~~~~~~~~~~~

The simple answer is to use :class:`.Bot`

For Example:

.. code-block:: python3

    import appcommands

    bot = appcommands.Bot(command_prefix="$")

How do I make a ShardedBot?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Simple answer is to use :class:`.AutoShardedBot`

For Example:

.. code-block:: python3

    import appcommands

    bot = appcommands.AutoShardedBot(command_prefix="$")

How to make bot to not work with prefix commands?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To not add prefix command, Simply don't give `command_prefix`
parameter in :class:`.Bot` or :class:`.AutoShardedBot`

For example:

.. code-block:: python3

    import appcommands

    bot = appcommands.Bot() # No command_prefix parameter

