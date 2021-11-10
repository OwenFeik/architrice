import json
import logging
import os

from . import cli
from . import common_json
from . import mode


class ImportJson(mode.Mode):
    def __init__(self):
        super().__init__(
            "J",
            "import-json",
            "import JSON file (-p) as profile list",
            ["path"],
        )

    def resolve_missing_arg(self, cache, arg, args):
        if arg != "path":
            raise ValueError(f"Can't resolve missing argument: {arg}.")

        return cli.get_path("JSON file to import")

    def action(self, cache, args):
        if os.path.isfile(args.path):
            with open(args.path, "r") as f:
                try:
                    data = json.load(f)
                except json.decoder.JSONDecodeError:
                    logging.error(f"Failed to parse JSON file {args.path}.")
                    return

            if isinstance(data, list):
                # should be a list of profiles
                for i, profile in enumerate(data, 1):
                    identifier = f"Profile {i}"
                    if not isinstance(profile, dict):
                        logging.error(
                            f"Profiles should be key-value. {identifier}"
                            " is not. Aborting."
                        )
                        break
                    elif not common_json.verify_profile_json(profile):
                        identifier = profile.get("name") or identifier
                        logging.error(f"{identifier} is invalid. Aborting.")
                        break
                else:
                    for i, profile in enumerate(data, 1):
                        identifier = profile.get("name") or f"Profile {i}"
                        common_json.import_profile_json(cache, profile)
                        logging.info(f"{identifier} added.")
            elif common_json.verify_profile_json(data):
                # accept a single profile
                common_json.import_profile_json(cache, data)
            else:
                logging.error(
                    "File must contain a single profile or a list of profiles,"
                    " in JSON format."
                )
