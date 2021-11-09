import logging
import json

from .. import sources
from .. import targets
from .. import utils

from . import cli
from . import common
from . import mode


def verify_output_json(output, i="\b"):
    if not "target" in output:
        logging.error(f"Output {i} is missing a target.")
        return False
    elif not isinstance(output["target"], str):
        logging.error("Output targets must be strings.")
        return False

    try:
        targets.get(output["target"], True)
    except ValueError as e:
        logging.error(str(e))
        return False

    if not "output_dir" in output:
        logging.error(f"Output {i} is missing an output directory.")
        return False
    elif not isinstance(output["output_dir"], str):
        logging.error("Output directories must be strings.")
        return False

    output["output_dir"] = utils.expand_path(output["output_dir"])
    if not utils.check_dir(output["output_dir"]):
        logging.error(f"Output directory {i} already exists and is a file.")
        return False

    if "include_maybe" in output:
        if not isinstance(output["include_maybe"], bool):
            logging.error(
                "The include_maybe flag of an Output must be a string."
            )
            return False
    else:
        output["include_maybe"] = False

    return True


def verify_profile_json(data):
    if not "source" in data:
        logging.error("Profile is missing a source.")
        return False
    elif not isinstance(data["source"], str):
        logging.error("Source must be a string.")
        return False

    try:
        source = sources.get(data["source"], True)
    except ValueError as e:
        logging.error(str(e))
        return False

    if not "user" in data:
        logging.error("Profile is missing a user.")
        return False
    elif not isinstance(data["user"], str):
        logging.error("User must be a string.")
        return False

    if common.get_verified_user(source, data.get("user")) is None:
        return False

    if "name" in data and not (
        data["name"] is None or isinstance(data["name"], str)
    ):
        logging.error("Name must be a string.")
        return False

    if not "outputs" in data:
        data["outputs"] = []

    if not isinstance(data["outputs"], list):
        logging.error("Outputs must be in a list.")
        return False

    for i, output in enumerate(data.get("outputs")):
        if not verify_output_json(output, i):
            return False

    return True


def edit_profile_json(cache, profile):
    editing = json.dumps(profile.to_json(), indent=4)

    while True:
        try:
            editing = cli.get_text_editor(editing, "profile.json")
            edited_json = json.loads(editing)
            if verify_profile_json(edited_json):
                break
        except json.JSONDecodeError:
            logging.error("Failed to parse edited JSON.")

        if not cli.get_decision("Try again?"):
            return

    new_profile = cache.build_profile(
        sources.get(edited_json["source"]),
        edited_json["user"],
        edited_json["name"],
    )

    # In the case that the new profile is redundant with an existing profile,
    # the same object is reused, so we don't want to remove it.
    if new_profile is not profile:
        cache.remove_profile(profile)

    for output in edited_json["outputs"]:
        cache.build_output(
            new_profile,
            targets.get(output["target"]),
            output["output_dir"],
            output["include_maybe"],
        )
    logging.info("Successfully updated profile.")


class Edit(mode.FilterArgsMode):
    def __init__(self):
        super().__init__("e", "edit", "edit a profile as JSON", ["profile"])

    def action(self, cache, args):
        if not args.interactive:
            logging.info(
                "Interactivity required to edit as JSON. Ignoring -e flag."
            )
        else:
            edit_profile_json(cache, args.profile)
