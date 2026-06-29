import re
from collections import Counter

UUID_RE = re.compile(r"^[a-f0-9\-]{20,}$", re.I)

def detect_type(values):

    total = len(values)
    if total == 0:
        return "unknown"

    uuid_count = 0
    numeric_count = 0
    web_like = 0

    for v in values:
        if v is None:
            continue

        v = str(v).strip().lower()

        if UUID_RE.match(v):
            uuid_count += 1
        elif v.isdigit():
            numeric_count += 1
        elif v in ["web", "android", "ios"]:
            web_like += 1

    if uuid_count / total > 0.6:
        return "uuid"
    if web_like / total > 0.3:
        return "categorical"
    if numeric_count / total > 0.6:
        return "numeric"

    return "mixed"