def detect_ambiguities(ambiguities):
    """
    Now HITL is ONLY for real uncertainty cases
    """

    filtered = []

    for item in ambiguities:

        top1 = item["top1"]
        top2 = item["top2"]

        if not top2:
            continue

        # true ambiguity condition
        if abs(top1["score"] - top2["score"]) < 0.05:
            filtered.append(item)

    return filtered

