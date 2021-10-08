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

MISSING = _MissingSentiel()

def missing(*args, **kwargs) -> MISSING:
  return MISSING
