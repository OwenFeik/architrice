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


def create_batch_file(shortcut_name, client_path):
    batch_file_path = os.path.join(
        utils.DATA_DIR,
        BATCH_FILE_NAME.format(
            shortcut_name.replace(".lnk", "").lower()
        ),  # e.g. Cockatrice.lnk => run_cockatrice.bat.
    )

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
                if shortcut_target and not BATCH_FILE_NAME in shortcut_target:
                    script_path = create_batch_file(
                        shortcut_name, shortcut_target
                    )
                    relink_shortcut(shortcut_path, script_path)
