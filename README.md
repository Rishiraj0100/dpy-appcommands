# dpy-appcommands
[![PyPi](https://shields.io/pypi/v/dpy-appcommands.svg)](https://pypi.org/project/dpy-appcommands/)
[![PyPi](https://shields.io/pypi/pyversions/dpy-appcommands.svg)](https://pypi.org/project/dpy-appcommands/)
## Support
If you want any support then join my [`discord server`](https://discord.gg/zdrSUu98BP)
## Installation

To install this module, run

```bash
pip install -U dpy-appcommands
```

## Usage

For a headstart, here's an example
but if you want to view full
documentation on it then [`click here`](https://dpy-appcommands.rtfd.io)

```py
import appcommands
from discord.ext import commands

bot = appcommands.Bot(command_prefix=commands.when_mentioned_or('?'))

class Blep(SlashCommand):
    def __init__(self):
        super().__init__(
            name="blep",
            description = "Some blep description",
        )

    async def callback(self, ctx: InteractionContext, pleb: str = None):
        await ctx.reply(f"why {pleb}", ephemeral=True)

# or

@bot.slashcommand(name="test", description="test")
async def test(ctx):
    await ctx.send("tested")

# or

@bot.slashcommand(name="test2", description="test")
async def test(ctx):
    await ctx.respond(f"tested {ctx.author}")

@bot.event
async def on_ready():
    print(f'Logged on as {bot.user} (ID: {bot.user.id})')
    await bot.add_app_command(Blep(), on_discord=True) # awaited

bot.run("TOKEN")
```

### Screenshots

![image](https://user-images.githubusercontent.com/75272148/127775083-6722865b-b38a-4c1c-aeab-67792448224b.png)

![image](https://user-images.githubusercontent.com/75272148/127775088-8504cd9d-0b94-4e82-a683-e8acb6cc0f43.png)

![image](https://user-images.githubusercontent.com/75272148/127775094-75c435c7-6600-4a43-9433-80482692821f.png)
