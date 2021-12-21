import discord

__all__ = (
    "MISSING",
    "missing",
    "ALL_GUILDS"
)

class _All(object):
    def __repr__(self):
        return "appcommands.ALL_GUILDS"

    def __str__(self):
        return repr(self)

class _MissingSentinel:
    def __eq__(self, other):
        if isinstance(self, other):
            return True
        return False

    def __bool__(self):
        return False

    def __repr__(self):
        return '...'

    def __call__(self):
        return self

    def __await__(self):
        async def _self():
            return self

        return _self().__await__()

MISSING = _MissingSentinel()
ALL_GUILDS = _All()

del globals()["_All"]

def missing(f):
    nm = _MissingSentinel()
    nm.__doc__ = f.__doc__
    return nm
