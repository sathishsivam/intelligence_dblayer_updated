def prettify_column(col_name: str):
    replacements = {
        "br":"branch",
        "ts":"time stamp",
        "txn": "transaction",
        "acct": "account",
        "acc": "account",
        "amt": "amount",
        "no": "number",
        "num": "number",
        "dt":"Date",
    }

    return " ".join(
        replacements[w] if w in replacements else w
        for w in col_name.lower().split("_")
    )

