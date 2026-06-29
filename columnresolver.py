from difflib import SequenceMatcher

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def is_valid_term(term: str):
    return len(term.split()) >= 1  # allow single words now


def resolve_columns_from_terms(matched_terms, mapping_text):
    print("Matched Term",matched_terms)

    mapping_dict = {}

    for line in mapping_text.splitlines():
        if "→" not in line:
            continue

        business_term, column = line.split("→")

        business_term = (
            business_term.replace('"', '')
            .replace("-", "")
            .strip()
            .lower()
        )

        mapping_dict[business_term] = column.strip()

    resolved_columns = []
    candidate_columns = []
    ambiguities = []

    for term in matched_terms:
        
        if not is_valid_term(term):
            continue

        term_norm = term.lower().strip()

        scores = []

        for business_term, column in mapping_dict.items():

            score = similarity(term_norm, business_term)

            scores.append({
                "column": column,
                "business_term": business_term,
                "score": round(score, 3)
            })

        scores.sort(key=lambda x: x["score"], reverse=True)

        top1 = scores[0]
        top2 = scores[1] if len(scores) > 1 else None

        # -----------------------------
        # AUTO ACCEPT RULE
        # -----------------------------
        if top1["score"] >= 0.78:

            resolved_columns.append(top1["column"])

        else:

            # -----------------------------
            # HITL CASE
            # -----------------------------
            ambiguities.append({
                "term": term,
                "top1": top1,
                "top2": top2,
                "all_candidates": scores[:5]
            })

        candidate_columns.append({
            "term": term,
            "candidates": scores[:3]
        })

    return {
        "resolved_columns": list(set(resolved_columns)),
        "candidate_columns": candidate_columns,
        "ambiguities": ambiguities
    }