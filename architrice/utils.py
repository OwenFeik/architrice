import datetime
import re


def create_file_name(deck_name):
    return re.sub("[^a-z_ ]+", "", deck_name.lower()).replace(" ", "_")


def parse_iso_8601(time_string):
    return datetime.datetime.strptime(
        time_string, "%Y-%m-%dT%H:%M:%S.%fZ"
    ).timestamp()
