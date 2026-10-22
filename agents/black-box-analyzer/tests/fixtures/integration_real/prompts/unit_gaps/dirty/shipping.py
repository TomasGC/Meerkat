def shipping_cost(weight_kg, country):
    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    base = 5.0 if country == "FR" else 12.0
    if weight_kg > 20:
        return base + (weight_kg - 20) * 0.8
    return base
