import os
import tempfile

import architrice

from . import mockapi

architrice.utils.DATA_DIR = os.path.join(tempfile.gettempdir(), 'architrice')
architrice.database.init()

mockapi.mock()

mockapi.stop()
