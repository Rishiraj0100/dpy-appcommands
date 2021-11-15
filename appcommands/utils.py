import discord

__all__ = (
    "MISSING",
    "missing"
)

class _MissingSentinel:
    def __init__(self, **attrs):
        for k, v in attrs.items():
          setattr(self, k, v)

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

def missing(*args, **kwargs):
  def wrap(f):
    return _MissingSentinel(__doc__=f.__doc__)

  return wrap
