class SearchIndex:
    def __init__(self):
        self.entries = {}

    def index(self, item_id, text):
        self.entries[item_id] = text
