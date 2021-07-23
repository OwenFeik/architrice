import os

from .cockatrice import Cockatrice
from .mtgo import Mtgo

targetlist = [t for t in [Cockatrice, Mtgo] if os.name in t.SUPPORTED_OS]

# singleton cache; sources have no data so only a single instance is required
_sources = {}


def get_target(name):
    if name is None:
        return None
    name = name.lower()  # case insensitivity
    for target in targetlist:
        if target.NAME.lower() == name or target.SHORT.lower() == name:
            if target.SHORT not in _sources:
                _sources[target.SHORT] = target()
            return _sources[target.SHORT]
    return None
