import abc


class Target(abc.ABC):
    def __init__(self, name, short, file_extension):
        self.name = name
        self.short = short
        self.file_extension = file_extension

    def suggest_directory(self):
        pass

    def save_deck(self, deck, path):
        pass

    def create_file_name(self, deck_name):
        return deck_name + self.file_extension
