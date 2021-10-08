import discord

__all__ = (
    "MISSING",
   "missing"
)

class _MissingSentinel:
    def __eq__(self, other):
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

MISSING = _MissingSentiel()

def missing(*args, **kwargs) -> MISSING:
  return MISSING
