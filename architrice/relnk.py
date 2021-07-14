import logging
import os
import subprocess
import sys

from . import cli
from . import utils

# List of common shortcut locations on windows
# ("Friendly name", "path\\to\\dir")
SHORTCUT_PATHS = [
    ("Start Menu", "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs"),
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

# Snippets used in powershell scripts to read/edit shortcuts
PS_SHORTCUT_SNIPPET = (
    "(New-Object -ComObject WScript.Shell).CreateShortcut('{}')"
)
PS_COMMAND_SNIPPET = 'powershell -command "{}"'

# Name of the .bat file created to run both apps
BATCH_FILE_NAME = "run_archi_cocka_trice.bat"


def create_batch_file(cockatrice_path):
    batch_file_path = os.path.join(utils.DATA_DIR, BATCH_FILE_NAME)
    if not os.path.exists(batch_file_path):
        with open(batch_file_path, "w") as f:
            f.write(
                PS_COMMAND_SNIPPET.format(f"Start-Process '{cockatrice_path}'")
                + f"\n{sys.executable} -m architrice -q"
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


def relink_shortcut(shortcut_path, new_target):
    try:
        subprocess.check_call(
            PS_COMMAND_SNIPPET.format(
                f"$shortcut = {PS_SHORTCUT_SNIPPET.format(shortcut_path)};"
                f"$shortcut.TargetPath = '{new_target}'; $shortcut.Save()"
            ),
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        logging.error(f"Failed to relink shortcut at {shortcut_path}.")
        logging.info("Run `python -m architrice -r` as admin to retry.")
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
                if (cockatrice_path := get_shortcut_target(shortcut_path)) :
                    script_path = create_batch_file(cockatrice_path)
                    relink_shortcut(shortcut_path, script_path)
