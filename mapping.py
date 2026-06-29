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
         # User
        "userid": "user id",
        "user id": "user id",
        "user identifier": "user id",

        # App
        "app id": "application id",
        "user app id": "application id",
        "application id": "application id",

        # Transaction
        "txn ref": "transaction reference",
        "txn reference": "transaction reference",
        "transaction ref": "transaction reference",
        "transaction reference": "transaction reference",

        # Time
        "st tm": "start time",
        "start tm": "start time",
        "start time": "start time",

        "end tm": "end time",
        "end time": "end time",

        "create ts": "create time stamp",
        "created ts": "create time stamp",

        "maker ts": "maker time stamp",
        "checker ts": "checker time stamp",

        # Notification
        "notif reg id": "notification registration id",
        "notification reg id": "notification registration id",
        "notification registration id": "notification registration id",

        # Auth
        "auth status": "authentication status",
        "authentication status": "authentication status",

        # Interface
        "interface id": "interface id",

        # Device
        "device id": "device id"
    }

    return " ".join(
        replacements[w] if w in replacements else w
        for w in col_name.lower().split("_")
    )

