from .profile import AddProfile
from .delete import DeleteProfile
from .edit import Edit
from .latest import Latest
from .output import AddOutput
from .relnk import Relnk
from .version import Version

from .sync import Sync

flag_modes = [
    AddProfile(),
    DeleteProfile(),
    Edit(),
    Latest(),
    AddOutput(),
    Relnk(),
    Version(),
]
