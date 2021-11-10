import json

from . import mode


class ExportJson(mode.FilterArgsMode):
    def __init__(self):
        super().__init__(
            "j", "export-json", "export matching profiles as JSON", ["profiles"]
        )

    def action(self, cache, args):
        print(
            json.dumps(
                [profile.to_json() for profile in cache.profiles], indent=4
            )
        )
