def tick_bread(buildings):
    total = 0
    for b in buildings:
        if b == "bakery":
            total += 3
    return total
