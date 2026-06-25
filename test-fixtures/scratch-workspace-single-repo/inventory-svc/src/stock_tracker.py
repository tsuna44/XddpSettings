class StockTracker:
    def __init__(self):
        self.levels = {}

    def update_level(self, sku, qty):
        self.levels[sku] = qty

    def get_level(self, sku):
        return self.levels.get(sku, 0)
