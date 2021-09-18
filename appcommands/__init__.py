__author__ = "Rishiraj0100"
__version__ = "1.0.1a"
import discord

if not discord.__version__.startswith("2.0"):
  raise RuntimeError(f"This module requires dpy v2.0 not {discord.__version__}")

from .cog import *
from .enums import *
from .client import *
from .models import *

