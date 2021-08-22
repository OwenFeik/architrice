import logging
import os
import subprocess
import tempfile

from . import utils

PROMPT = "> "

# Text editing on linux is done through tempfile
EDITOR_ENVIRONMENT_VARIABLE = "EDITOR"
EDITOR_FALLBACK = "nano" if os.name == "posix" else "notepad"


def get_choice(options, prompt, values=None):
    print(prompt)
    for i, option in enumerate(options):
        print(f"\t[{i + 1}] {option}")

    FAILURE_MESSAGE = "Please enter the number of one of the options."

    while True:
        choice = input(PROMPT).strip()

        if choice in options:
            i = options.index(choice)
        elif choice.isnumeric() and 0 < int(choice) <= len(options):
            i = int(choice) - 1
        else:
            print(FAILURE_MESSAGE)
            continue

        if values:
            return values[i]
        return options[i]


def get_decision(prompt, default=True):
    opts = (
        "(" + ("Y" if default else "y") + "/" + ("n" if default else "N") + ")"
    )

    d = input(f"{prompt} {opts} {PROMPT}").strip().lower()
    if d in [
        "y",
        "yes",
    ]:
        return True
    elif default and not d:
        return True
    else:
        return False


def get_string(prompt):
    while True:
        string = input(f"{prompt} {PROMPT}")
        if string:
            return string.strip()


def get_path(prompt):
    return utils.expand_path(input(f"{prompt} {PROMPT}"))


def get_text_editor_posix(default, editor, file_name):
    with tempfile.NamedTemporaryFile(suffix=file_name) as tf:
        tf.write(default.encode())
        tf.flush()
        subprocess.call(
            [
                editor,
                tf.name,
            ]
        )
        tf.seek(0)
        return tf.read().decode()


def get_text_editor_nt(default, editor, file_name):
    path = os.path.join(utils.DATA_DIR, file_name)
    with open(path, "w") as f:
        f.write(default)

    subprocess.call([editor, path], shell=True)

    with open(path, "r") as f:
        return f.read()
    os.remove(path)


def get_text_editor(default="", file_name=None):
    editor = os.environ.get(EDITOR_ENVIRONMENT_VARIABLE, EDITOR_FALLBACK)

    if os.name == "posix":
        return get_text_editor_posix(default, editor, file_name)
    elif os.name == "nt":
        return get_text_editor_nt(default, editor, file_name)
    else:
        logging.error("Unsupported operating system.")
