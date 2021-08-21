import os

from .cockatrice import Cockatrice
from .generic import Generic
from .mtgo import Mtgo
from .xmage import XMage

targetlist = [
    t for t in [Cockatrice, Generic, Mtgo, XMage] if os.name in t.SUPPORTED_OS
]

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
