import os

from .cockatrice import Cockatrice
from .generic import Generic
from .mtgo import Mtgo
from .xmage import XMage

targetlist = [
    t for t in [Cockatrice, Generic, Mtgo, XMage] if os.name in t.SUPPORTED_OS
]

# singleton cache; sources have no data so only a single instance is required
_targets = {}


def get(name, error_on_fail=False):
    if name:
        name = name.lower()  # case insensitivity
        for target in targetlist:
            if target.NAME.lower() == name or target.SHORT.lower() == name:
                if target.SHORT not in _targets:
                    _targets[target.SHORT] = target()
                return _targets[target.SHORT]

    if error_on_fail:
        raise ValueError(f'No target matching "{name}" exists.')
    return None
