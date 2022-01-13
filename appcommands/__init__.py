__author__ = "Rishiraj0100"
__version__ = "2.0.4.5"
import discord

if not discord.__version__.startswith("2.0"):
  raise RuntimeError(f"This module requires dpy v2.0 not {discord.__version__}")

from .cog import *
from .core import *
from .enums import *
from .client import *

from .utils import ALL_GUILDS
