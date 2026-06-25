class ReorderPlanner:
    def __init__(self, threshold=10):
        self.threshold = threshold

    def needs_reorder(self, current_level):
        return current_level < self.threshold
