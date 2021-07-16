from .archidekt import Archidekt
from .deckstats import Deckstats
from .moxfield import Moxfield
from .tappedout import TappedOut

sourcelist = [Archidekt, Deckstats, Moxfield, TappedOut]

# singleton cache; sources have no data so only a single instance is required
_sources = {}


def get_source(name):
    name = name.lower()  # case insensitivity
    for source in sourcelist:
        if source.NAME.lower() == name or source.SHORT.lower() == name:
            if source.SHORT not in _sources:
                _sources[source.SHORT] = source()
            return _sources[source.SHORT]
    raise ValueError(f'No source named "{name}" exists.')
