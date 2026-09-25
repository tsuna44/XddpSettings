def validate(value):
    if not (0 <= value <= 100):
        raise ValueError("value out of range: expected 0..100")
