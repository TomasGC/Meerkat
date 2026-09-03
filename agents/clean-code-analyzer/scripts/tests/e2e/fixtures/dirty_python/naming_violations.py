# KNOWN VIOLATIONS: Naming>=3 (magic numbers, single-letter vars, magic strings)


def calculate(a, b):
    x = a * 86400
    if b == "active_user":
        return x * 1440
    return x


def process(d):
    r = []
    for e in d:
        r.append(e)
    return r
