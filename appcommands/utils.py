import discord

__all__ = (
    "MISSING",
   "missing"
)

class _MissingSentinel:
    """This function should must be a |coroutine_link|_

    This is invoked when a command is called.
    """
    def __eq__(self, other):
        return False

    def __bool__(self):
        return False

    def __repr__(self):
        return '...'

    async def __call__(self):
        return self

    def __await__(self):
        async def _self():
            return self

        return _self().__await__()

MISSING = _MissingSentinel()

def missing(*args, **kwargs) -> MISSING:
  return MISSING
