import re

def extract_column_terms(query: str):

    query = query.lower()

    # split by "for"
    main_part = re.split(r"\bfor\b", query)[0]

    # extract phrases (simple heuristic)
    phrases = re.findall(r"[a-zA-Z ]+", main_part)

    cleaned = []

    for p in phrases:

        p = p.strip()

        if len(p.split()) >= 2:
            cleaned.append(p)

    return cleaned

col=extract_column_terms("Display the message, user id, insert timestamp, account number, account type for userid is 1680382")
print(col)
