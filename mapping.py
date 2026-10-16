from itertools import product

# ==========================================================
# TOKEN VOCABULARY
# ==========================================================

TOKEN_MAP = {

    # ------------------------------------------------------
    # Identifier
    # ------------------------------------------------------

    "id": ["id", "identifier"],
    "no": ["number", "no"],
    "num": ["number"],

    # ------------------------------------------------------
    # User / Customer
    # ------------------------------------------------------

    "usr": ["user"],
    "user": ["user"],

    "cust": ["customer"],
    "customer": ["customer"],

    "benef": ["beneficiary"],
    "beneficiary": ["beneficiary"],

    # ------------------------------------------------------
    # Account
    # ------------------------------------------------------

    "acc": ["account"],
    "acct": ["account"],
    "account": ["account"],

    # ------------------------------------------------------
    # Application
    # ------------------------------------------------------

    "app": ["application"],
    "application": ["application"],

    # ------------------------------------------------------
    # Transaction
    # ------------------------------------------------------

    "txn": ["transaction"],
    "trx": ["transaction"],
    "tran": ["transaction"],
    "transaction": ["transaction"],

    "ref": ["reference"],
    "reference": ["reference"],

    # ------------------------------------------------------
    # Product
    # ------------------------------------------------------

    "prod": ["product"],
    "prd": ["product"],
    "product": ["product"],

    "desc": ["description"],
    "description": ["description"],

    # ------------------------------------------------------
    # Amount
    # ------------------------------------------------------

    "amt": ["amount"],
    "amount": ["amount"],

    "min": ["min", "minimum"],
    "max": ["max", "maximum"],

    "bal": ["balance"],

    # ------------------------------------------------------
    # Currency
    # ------------------------------------------------------

    "ccy": ["currency", "ccy"],
    "curr": ["currency"],
    "currency": ["currency"],

    # ------------------------------------------------------
    # Charge
    # ------------------------------------------------------

    "charge": ["charge"],
    "charges": ["charges"],
    "fee": ["fee"],

    # ------------------------------------------------------
    # Time / Date
    # ------------------------------------------------------

    "ts": ["timestamp", "time stamp", "ts"],
    "tm": ["time", "timestamp"],
    "dt": ["date"],

    "created": ["created", "create"],
    "create": ["create"],

    "maker": ["maker"],
    "checker": ["checker"],

    "effective": ["effective"],

    # ------------------------------------------------------
    # Status
    # ------------------------------------------------------

    "sts": ["status"],
    "status": ["status"],

    "auth": [
        "authentication",
        "authorization",
        "auth"
    ],

    # ------------------------------------------------------
    # Branch / Location
    # ------------------------------------------------------

    "br": ["branch"],
    "branch": ["branch"],

    "loc": ["location"],
    "location": ["location"],

    "addr": ["address"],
    "address": ["address"],

    "city": ["city"],
    "state": ["state"],
    "country": ["country"],

    # ------------------------------------------------------
    # Banking
    # ------------------------------------------------------

    "ifsc": ["ifsc"],

    "imps": ["imps"],
    "neft": ["neft"],
    "rtgs": ["rtgs"],
    "upi": ["upi"],

    # ------------------------------------------------------
    # Notification
    # ------------------------------------------------------

    "notif": ["notification"],
    "notification": ["notification"],

    # ------------------------------------------------------
    # Device
    # ------------------------------------------------------

    "imei": ["imei"],
    "device": ["device"],
    "mobile": ["mobile", "phone"],

    # ------------------------------------------------------
    # Tax
    # ------------------------------------------------------

    "gst": ["gst", "tax"],

    # ------------------------------------------------------
    # Group
    # ------------------------------------------------------

    "grp": ["group"],

    # ------------------------------------------------------
    # Misc
    # ------------------------------------------------------

    "ver": ["version"],
    "version": ["version"],

    "pwd": ["password"]
}


# ==========================================================
# BUSINESS TERM GENERATOR
# ==========================================================

def build_business_terms(column_name: str):

    tokens = column_name.lower().split("_")

    expanded = []

    for token in tokens:

        expanded.append(
            TOKEN_MAP.get(token, [token])
        )

    terms = []

    for combo in product(*expanded):

        terms.append(" ".join(combo))

    return list(dict.fromkeys(terms))


# ==========================================================
# BACKWARD COMPATIBILITY
# ==========================================================

def prettify_column(column_name: str):

    """
    Existing code expects one string.

    Return the first generated business term.

    """

    return build_business_terms(column_name)[0]

