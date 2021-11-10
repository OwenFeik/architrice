from .profile import AddProfile
from .delete import DeleteProfile
from .edit_json import EditJson
from .export_json import ExportJson
from .import_json import ImportJson
from .latest import Latest
from .output import AddOutput
from .relnk import Relnk
from .version import Version
from .clear_cards import ClearCards

from .sync import Sync  # Export

flag_modes = [
    AddProfile(),
    DeleteProfile(),
    EditJson(),
    ExportJson(),
    ImportJson(),
    Latest(),
    AddOutput(),
    Relnk(),
    Version(),
    ClearCards(),
]
