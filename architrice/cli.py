from . import utils

PROMPT = "> "


def get_choice(options, prompt, values=None):
    print(prompt)
    for i, option in enumerate(options):
        print(f"\t[{i + 1}] {option}")

    FAILURE_MESSAGE = "Please enter the number of one of the options."

    while True:
        choice = input(PROMPT).strip()

        if choice in options:
            i = options.index(choice)
        elif choice.isnumeric() and 0 <= (i := int(choice) - 1) < len(options):
            pass
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
    if (d := input(f"{prompt} {opts} {PROMPT}").strip().lower()) in [
        "y",
        "yes",
    ]:
        return True
    elif default and not d:
        return True
    else:
        return False


def get_string(prompt):
    while not (string := input(f"{prompt} {PROMPT}")):
        pass
    return string.strip()


def get_path(prompt):
    return utils.expand_path(input(f"{prompt} {PROMPT}"))
