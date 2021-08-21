import os
import tempfile

import architrice

architrice.utils.DATA_DIR = os.path.join(tempfile.gettempdir(), 'architrice')
architrice.database.init()

