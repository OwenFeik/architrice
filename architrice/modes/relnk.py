import logging
import os
import subprocess
import sys

from .. import utils

from . import cli
from . import mode

APP_NAME = utils.APP_NAME

try:
    # List of common shortcut locations on windows
    # ("Friendly name", "path\\to\\dir")
    SHORTCUT_PATHS = [
        (
            "Start Menu",
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
        ),
        (
            "Start Menu",
            os.path.join(os.getenv("USERPROFILE"), "Start Menu", "Programs"),
        ),
        (
            "Task Bar",
            os.path.join(
                os.getenv("APPDATA"),
                "Microsoft",
                "Internet Explorer",
                "Quick Launch",
                "User Pinned",
                "TaskBar",
            ),
        ),
        ("Desktop", os.path.join(os.getenv("USERPROFILE"), "Desktop")),
    ]
except TypeError:
    # not on Windows, getenv returns None, causing join to TypeError
    # we won't use this list on Linux anyway.
    pass

# Snippets used in powershell scripts to read/edit shortcuts
PS_SHORTCUT_SNIPPET = (
    "(New-Object -ComObject WScript.Shell).CreateShortcut('{}')"
)
PS_RELINK_SNIPPET = (
    f"$shortcut = {PS_SHORTCUT_SNIPPET};"
    "$target_path = $shortcut.TargetPath;"
    "$shortcut.TargetPath = '{}';"
    "$shortcut.IconLocation = -join($target_path,',0');"
    "$shortcut.Save();"
)
# Any single quotes in the command must be appropriately escaped,
# use root_format_command instead of directly calling .format
PS_ROOT_SNIPPET = "Start-Process powershell -Verb RunAs -Args '-Command {}'"
PS_COMMAND_SNIPPET = 'powershell -command "{}"'

# Name of the .bat file created to run both apps
BATCH_FILE_NAME = "run_{}.bat"


def batch_file_name(shortcut_name):
    return BATCH_FILE_NAME.format(
        shortcut_name.replace(".lnk", "").lower()
    )  # e.g. Cockatrice.lnk => run_cockatrice.bat.


def create_batch_file(script_name, client_path):
    batch_file_path = os.path.join(utils.DATA_DIR, script_name)

    if not os.path.exists(batch_file_path):
        with open(batch_file_path, "w") as f:
            f.write(
                PS_COMMAND_SNIPPET.format(f"Start-Process '{client_path}'")
                + f"\n{sys.executable} -m architrice\n"
            )

    return batch_file_path


def get_shortcut_target(shortcut_path):
    return (
        subprocess.check_output(
            PS_COMMAND_SNIPPET.format(
                PS_SHORTCUT_SNIPPET.format(shortcut_path) + ".TargetPath"
            )
        )
        .decode()
        .strip()
    )


def root_format_command(command):
    return PS_ROOT_SNIPPET.format(command.replace("'", "''"))


def relink_shortcut(shortcut_path, new_target, as_admin=False):
    command = PS_RELINK_SNIPPET.format(shortcut_path, new_target)
    try:
        subprocess.check_call(
            PS_COMMAND_SNIPPET.format(
                root_format_command(command) if as_admin else command
            ),
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        logging.error(f"Failed to relink shortcut at {shortcut_path}.")
        if not as_admin:
            logging.info("Retrying as admin.")
            relink_shortcut(shortcut_path, new_target, True)
        return
    logging.info(f"Relinked {shortcut_path} to {new_target}.")


def relink_shortcuts(shortcut_name, confirm=False):
    """Relink all shortcuts named `shortcut_name` to also run Architrice."""

    for friendly_name, directory in SHORTCUT_PATHS:
        for sub_directory in os.walk(directory):
            path, _, files = sub_directory
            if not shortcut_name in files:
                continue

            relative_path = os.path.relpath(path, directory)

            if not confirm or cli.get_decision(
                f"Found Cockatrice shortcut on your {friendly_name}"
                + (f" in {relative_path}" if relative_path != "." else "")
                + ". Would you like to update it to run Architrice at launch?"
            ):
                shortcut_path = os.path.join(path, shortcut_name)
                shortcut_target = get_shortcut_target(shortcut_path)
                script_name = batch_file_name(shortcut_name)
                if shortcut_target and not script_name in shortcut_target:
                    script_path = create_batch_file(
                        script_name, shortcut_target
                    )
                    relink_shortcut(shortcut_path, script_path)


class Relnk(mode.Mode):
    def __init__(self):
        super().__init__(
            "r", "relink", "edit shortcuts to run architrice", ["target"]
        )

    def main(args):
        if os.name == "nt":
            target = utils.get_target(args.target, args.interactive)
            if not target:
                logging.info(
                    "Unable to set up shortcuts as no target has been provided."
                )
                return

            if not target.SUPPORTS_RELNK:
                logging.info(
                    "This target doesn't support shortcut configuration."
                )
                return

            relink_shortcuts(
                target.SHORTCUT_NAME,
                not cli.get_decision("Automatically update all shortcuts?"),
            )
        elif os.name == "posix":
            APP_PATH = f"/usr/bin/{APP_NAME}"
            if cli.get_decision(f"Add script to run {APP_NAME} to /usr/bin/?"):
                script_path = os.path.join(utils.DATA_DIR, APP_NAME)
                with open(script_path, "w") as f:
                    f.write(f"{sys.executable} -m {APP_NAME}\n")
                os.chmod(script_path, 0o755)
                subprocess.call(["sudo", "mv", script_path, APP_PATH])
                logging.info(f'Running "{APP_NAME}" will now run {APP_NAME}.')
        else:
            logging.error("Unsupported operating system.")
