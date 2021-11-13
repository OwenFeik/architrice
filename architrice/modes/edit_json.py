import logging
import json

from . import cli
from . import common_json
from . import mode


def edit_profile_json(cache, profile):
    editing = json.dumps(profile.to_json(), indent=4)

    while True:
        try:
            editing = cli.get_text_editor(editing, "profile.json")
            edited_json = json.loads(editing)
            if common_json.verify_profile_json(edited_json):
                break
        except json.JSONDecodeError:
            logging.error("Failed to parse edited JSON.")

        if not cli.get_decision("Try again?"):
            return

    # In the case that the new profile is redundant with an existing
    # profile, the same object is reused, so we don't want to remove it.
    if common_json.import_profile_json(cache, edited_json) is not profile:
        cache.remove_profile(profile)

    logging.info("Successfully updated profile.")


class EditJson(mode.FilterArgsMode):
    def __init__(self):
        super().__init__(
            "e", "edit-json", "edit a profile as JSON", ["profile"]
        )

    def action(self, cache, args):
        if not args.interactive:
            logging.info(
                "Interactivity required to edit as JSON. Ignoring -e flag."
            )
        else:
            edit_profile_json(cache, args.profile)
