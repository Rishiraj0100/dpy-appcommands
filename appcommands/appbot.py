import appcommands, re, zlib, discord, io, aiohttp, os

from os import environ as env
from typing import Any, List
from appcommands import OptionType, Option, Choice


installed: bool = False

flags: List[str] = [
  "jishaku no underscore",
  "jishaku force paginator",
  "jishaku no dm traceback",
  "jishaku retain",
  "jishaku hide"
]

class AppBot(appcommands.Bot):
  def __init__(self, **kwargs) -> None:
    if kwargs.get("_using_super", False) or False: kwargs.pop("_using_super"); return super().__init__(**kwargs)
    super().__init__(
      command_prefix="$",
      strip_after_prefix=True,
      case_insensitive=True
    )

  async def on_connect(self) -> None:
    self.session = aiohttp.ClientSession(loop=self.loop)
    await self.change_presence(
      activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="dpy-appcommands v{v}".format(
          v=appcommands.__version__
        )
      ),
      status=discord.Status.dnd
    )
    print(f"{self.user} started!")

    async def close(self):
      await super().close()
      await self.session.close()


bot: AppBot = AppBot()

def enable(content: str, v: str = "t") -> None:
  t: str = content.upper()
  while " " in t:
    t: str = t.replace(" ", "_")

  env[t]: str = v

for flag in flags:
  enable(flag)

def finder(text, collection, *, key=None, lazy=True):
  suggestions = []
  text = str(text)
  pat = ".*?"
  pat = pat.join(map(re.escape, text))
  regex = re.compile(pat, flags=re.IGNORECASE)
  for item in collection:
    to_search = key(item) if key else item
    r = regex.search(to_search)
    if r:
      suggestions.append((len(r.group()), r.start(), item))

  def sort_key(tup):
    if key:
      return tup[0], tup[1], key(tup[2])
    return tup

  if lazy:
    return (z for _, _, z in sorted(suggestions, key=sort_key))
  else:
    return [z for _, _, z in sorted(suggestions, key=sort_key)]


_ = "_"
Q = Option(_, "query to get documentation", OptionType.STRING, True)

# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/api.py


class SphinxObjectFileReader:
  BUFSIZE: int = 16 * 1024

  def __init__(self, buffer):
    self.stream = io.BytesIO(buffer)

  def readline(self):
    return self.stream.readline().decode("utf-8")

  def skipline(self):
    self.stream.readline()

  def read_compressed_chunks(self):
    decompressor = zlib.decompressobj()
    while True:
      chunk = self.stream.read(self.BUFSIZE)
      if len(chunk) == 0:
        break
      yield decompressor.decompress(chunk)
    yield decompressor.flush()


  def read_compressed_lines(self):
    buf = b""
    for chunk in self.read_compressed_chunks():
      buf += chunk
      pos = buf.find(b"\n")
      while pos != -1:
        yield buf[:pos].decode("utf-8")
        buf = buf[pos + 1 :]
        pos = buf.find(b"\n")

class RTFMCog(appcommands.Cog):
  def __init__(self, bot: AppBot):
    self.bot: AppBot = bot

  def parse_object_inv(self, stream, url):
    result = {}
    inv_version = stream.readline().rstrip()
    if inv_version != "# Sphinx inventory version 2":
      raise RuntimeError("Invalid objects.inv file version.")

    projname = stream.readline().rstrip()[11:]
    version = stream.readline().rstrip()[11:]
    line = stream.readline()
    if "zlib" not in line:
      raise RuntimeError("Invalid objects.inv file, not z-lib compatible.")

    entry_regex = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
    for line in stream.read_compressed_lines():
      match = entry_regex.match(line.rstrip())
      if not match:
        continue

      name, directive, prio, location, dispname = match.groups()
      domain, _, subdirective = directive.partition(":")
      if directive == "py:module" and name in result:
        continue

      if directive == "std:doc":
        subdirective = "label"

      if location.endswith("$"):
        location = location[:-1] + name

      key = name if dispname == "-" else dispname
      prefix = f"{subdirective}:" if domain == "std" else ""

      if projname == "discord.py":
        key = key.replace("discord.ext.commands.", "").replace("discord.", "")
      elif projname == "dpy-appcommands":
        key = key.replace("appcommands.", "")

      result[f"{prefix}{key}"] = os.path.join(url, location)

    return result

  async def build_rtfm_lookup_table(self, page_types):
    cache = {}
    for key, page in page_types.items():
      sub = cache[key] = {}
      async with self.bot.session.get(page + "/objects.inv") as resp:
        if resp.status != 200:
          raise RuntimeError("Cannot build rtfm lookup table, try again later.")

        stream = SphinxObjectFileReader(await resp.read())
        cache[key] = self.parse_object_inv(stream, page)

      self._rtfm_cache = cache

  async def do_rtfm(self, ctx, key, obj):
    page_types = {
      "appcommands": "https://dpy-appcommands.readthedocs.io/en/stable",
      "python": "https://docs.python.org/3",
      "discord_master": "https://discordpy.readthedocs.io/en/master",
      "discord_stable": "https://discordpy.readthedocs.io/en/stable"
    }

    for v in ["2.7","3.5","3.6","3.7","3.8","3.9","3.10","3.11"]:
      page_types["python" + v] = "https://docs.python.org/" + v

    if obj is None:
      await ctx.send(page_types[key], ephemeral=True)
      return

    if not hasattr(self, "_rtfm_cache"):
      await self.build_rtfm_lookup_table(page_types)

    obj = re.sub(r"^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)", r"\1", obj)
    obj = re.sub(r"^(?:appcommands\.)?(.+)", r"\1", obj)

    if key.startswith("discord"):
      q = obj.lower()
      for name in dir(discord.abc.Messageable):
        if name[0] == "_":
          continue

        if q == name:
          obj = f"abc.Messageable.{name}"
          break

    cache = list(self._rtfm_cache[key].items())

    def transform(tup):
      return tup[0]

    matches = finder(obj, cache, key=lambda t: t[0], lazy=False)[:8]

    e = discord.Embed(colour=0x00ffff)
    if len(matches) == 0:
      return await ctx.send("Could not find anything. Sorry.", ephemeral=True)

    e.description = "\n".join(f"[`{key}`]({url})" for key, url in matches)
    await ctx.send(embed=e,)

  rtfm = appcommands.slashgroup(
    name="rtfm",
    description="Rtfm Commands"
  )

  @rtfm.subcommand(name="appcommands", description="Search documentation of dpy-appcommands objects.")
  async def rtfm_apc(self, ctx, *, query: Q = None):
    await self.do_rtfm(ctx, "appcommands", query)

  @rtfm.subcommand(name="discordpy", description="Search documentation of discord.py objects.")
  async def rtfm_dsc(
    self,
    ctx,
    query: Q = None,
    version: Option(
      _,
      "Version (default: master)",
      required = False,
      choices = [
        Choice("master (2.0)", "master"),
        Choice("stable (1.7.3)", "stable")
      ]
    ) = "master"
  ):
    await self.do_rtfm(ctx, f"discord_{version}", query)

  @rtfm.subcommand(name="python", description="Search documentation of Python objects.")
  async  def rtfm_py(
    self,
    ctx,
    query: Q = None,
    version: Option(
      _,
      "Version (default: 3.10)",
      required = False,
      choices = [
        Choice("3.11"),
        Choice("3.10"),
        Choice("3.9"),
        Choice("3.8"),
        Choice("3.7"),
        Choice("3.6"),
        Choice("3.5"),
        Choice("2.7")
      ]
    ) = "3.10",
  ):
    await self.do_rtfm(ctx, f"python{version}", query,)

def install(bot: AppBot):
  if installed: return
  global help_, uid, uid_, mid

  @bot.slashcommand(name="help", description="Get help of a command")
  async def help_(ctx, command: str = None):
    if command is None:
      embed = discord.Embed(title="App Bot's Help Menu")
      for cmd in bot.get_slash_commands().values():
        embed.add_field(name=f"`/{cmd.full_name}`", value=cmd.description, inline=False)
    elif not bot.get_slash_command(command): return await ctx.send(f"Command `{command}` not found!", ephemeral=True)
    else:
      cmd=bot.get_slash_command(command)
      fmt=f"**`/{cmd.full_name}`**\n\n{cmd.description}"
      embed = discord.Embed(title="App Bot's Help Menu", description=fmt)
    await ctx.send(embed=embed)
    
  @bot.usercommand(name="id")
  async def uid(ctx, user: discord.User):
    await ctx.send(f"Id of {user.mention} is `{user.id}`", ephemeral=True)

  @bot.slashcommand(name="id", description="Get ID of a User")
  async def uid_(ctx, user: discord.User):
    await ctx.send(f"Id of {user.mention} is `{user.id}`", ephemeral=True)

  @bot.messagecommand(name="id")
  async def mid(ctx, message: discord.Message):
    await ctx.send(f"Id of that message is `{message.id}`", ephemeral=True)

  bot.remove_command("help")

  globals()["installed"] = True

  globals()["bot"] = bot

def export():
  return bot

def setup(func):
  func(bot)

def run(token: str = None, *, task: bool = False):
  try:
    bot.add_cog(RTFMCog(bot))
    bot.load_extension("jishaku")
  except:
    pass

  if task: return bot.loop.create_task(bot.start(token or env.get("APP_BOT_TOKEN")))
  bot.run(token or env.get("APP_BOT_TOKEN"))
