from .add import Add
from .delete import Delete
from .edit import Edit
from .latest import Latest
from .relnk import Relnk
from .version import Version

modelist = [
    Add(),
    Delete(),
    Edit(),
    Latest(),
    Relnk(),
    Version()
]
