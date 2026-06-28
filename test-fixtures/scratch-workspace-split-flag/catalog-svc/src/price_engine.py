class PriceEngine:
    def __init__(self):
        self.prices = {}

    def set_price(self, item_id, price):
        self.prices[item_id] = price
