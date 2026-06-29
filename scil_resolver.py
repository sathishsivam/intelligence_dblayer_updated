from difflib import SequenceMatcher

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def normalize(text: str):
    import re
    return re.sub(r"\s+", " ", text).strip().lower()


def build_mapping_dict(mapping_text: str):
    mapping = {}

    for line in mapping_text.splitlines():
        if "→" not in line:
            continue

        business, column = line.split("→")

        business = normalize(
            business.replace('"', '').replace("-", "")
        )

        mapping[business] = column.strip()

    return mapping


def resolve_columns(matched_terms, mapping_text, threshold=0.78, top_k=5):

    mapping = build_mapping_dict(mapping_text)

    resolved = []
    ambiguities = []

    for term in matched_terms:

        term_norm = normalize(term)

        scores = [
            {
                "column": col,
                "business_term": bt,
                "score": round(similarity(term_norm, bt), 3)
            }
            for bt, col in mapping.items()
        ]

        scores.sort(key=lambda x: x["score"], reverse=True)

        top1 = scores[0]
        top2 = scores[1] if len(scores) > 1 else None

        # -------------------------
        # DECISION RULE
        # -------------------------
        if top1["score"] >= threshold and (not top2 or (top1["score"] - top2["score"]) > 0.08):

            resolved.append(top1["column"])

        else:
            ambiguities.append({
                "term": term,
                "top1": top1,
                "top2": top2,
                "all_candidates": scores[:top_k]
            })

    return {
        "resolved_columns": list(set(resolved)),
        "ambiguities": ambiguities
    }
