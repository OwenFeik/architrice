from .cockatrice import Cockatrice
from .mtgo import Mtgo

targetlist = [Cockatrice, Mtgo]

# singleton cache; sources have no data so only a single instance is required
_sources = {}


def get_target(name):
    name = name.lower()  # case insensitivity
    for target in targetlist:
        if target.NAME.lower() == name or target.SHORT.lower() == name:
            if target.SHORT not in _sources:
                _sources[target.SHORT] = target()
            return _sources[target.SHORT]
    raise ValueError(f'No target named "{name}" exists.')
