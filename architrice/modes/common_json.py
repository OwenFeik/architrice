import logging

from .. import sources
from .. import targets
from .. import utils

from . import common


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


def import_profile_json(cache, profile_json):
    profile = cache.build_profile(
        sources.get(profile_json["source"]),
        profile_json["user"],
        profile_json["name"],
    )

    # In the event profile is an existing profile, we want to clear it's outputs
    # as this process overwrites them. If it's a new profile it won't have any
    # outputs and this is a no-op.
    profile.clear_outputs()

    for output in profile_json["outputs"]:
        cache.build_output(
            profile,
            targets.get(output["target"]),
            output["output_dir"],
            output["include_maybe"],
        )

    return profile
