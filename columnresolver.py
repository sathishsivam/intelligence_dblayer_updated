def resolve_columns_from_terms(
    matched_terms,
    mapping_text
):
    resolved = []

    mapping_dict = {}

    for line in mapping_text.splitlines():

        if "→" not in line:
            continue

        business_term, column = line.split("→")

        business_term = (
            business_term
            .replace('"', '')
            .replace("-", "")
            .strip()
            .lower()
        )

        mapping_dict[business_term] = column.strip()

    for term in matched_terms:

        term = term.lower()

        if term in mapping_dict:
            resolved.append(mapping_dict[term])

    return list(set(resolved))

