Quickstart
==========

Before doing anything, it is highly recommended to read discord.py's quickstart.
You can find it by clicking :ref:`this here <discord:quickstart>`.

Firstly, we will begin from installing dpy-appcommands:

Installing
-----------

.. code-block:: shell

    pip install dpy-appcommands -U

Then we will make a ``Bot``

Initialising
-------------

.. code-block:: python3

    from discord.ext import commands
    from appcommands import Bot

    bot = Bot(command_prefix="$")

Then we will make a  slashcommand

Creating a slashcommand
-----------------------

.. code-block:: python3

    @bot.slashcommand(name="hi", description="Hello!")
    async def hi(ctx):
        await ctx.reply("Hello")

