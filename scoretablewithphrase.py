import re

# -----------------------------------
# Stop Words
# -----------------------------------
STOP_WORDS = {
    "the", "is", "am", "are", "was", "were",
    "be", "been", "being", "out",
    "what", "which", "who", "where", "when",
    "how", "along", "with", "will", "shall",
    "can", "could", "would", "should",
    "a", "an", "of", "to", "in", "on", "for",
    "and", "or", "by", "from",
    "find"
}


# -----------------------------------
# Extract Query Terms
# -----------------------------------
def extract_query_terms(query: str):

    words = re.findall(r'\w+', query.lower())

    return [
        word for word in words
        if word not in STOP_WORDS
    ]


# -----------------------------------
# Extract Dynamic Phrases
# -----------------------------------
def extract_dynamic_phrases(mapping_text):

    phrases = []

    lines = mapping_text.splitlines()

    for line in lines:

        match = re.search(r'"(.*?)"', line)

        if match:

            phrases.append(
                match.group(1).lower()
            )

    return phrases


# -----------------------------------
# Main Scoring Engine
# -----------------------------------
def score_table(query, schema_text, mapping_text=""):

    query = query.lower()

    schema = schema_text.lower()

    mapping = mapping_text.lower()

    score = 0

    matched_terms = []

    # -----------------------------------
    # Query Terms
    # -----------------------------------
    query_terms = extract_query_terms(query)

    # -----------------------------------
    # Dynamic Phrases
    # -----------------------------------
    phrases = extract_dynamic_phrases(mapping_text)

    # -----------------------------------
    # Dynamic Phrase Match
    # -----------------------------------
    for phrase in phrases:

        if phrase in query:

            score += 60

            matched_terms.append(phrase)

    # -----------------------------------
    # Exact Column Match
    # -----------------------------------
    for term in query_terms:

        pattern = rf'\b{term}\b'

        if re.search(pattern, schema):

            score += 10

            matched_terms.append(term)

    # -----------------------------------
    # Mapping Match
    # -----------------------------------
    for term in query_terms:

        pattern = rf'\b{term}\b'

        if re.search(pattern, mapping):

            score += 20

            matched_terms.append(term)

    # -----------------------------------
    # Column Prefix Intelligence
    # -----------------------------------
    schema_columns = re.findall(
        r'([a-zA-Z0-9_]+)\s+\(',
        schema
    )

    prefixes = set()

    for col in schema_columns:

        if "_" in col:

            prefixes.add(col.split("_")[0])

    for prefix in prefixes:

        if prefix in query:

            score += 30

            matched_terms.append(prefix)

    # -----------------------------------
    # Remove duplicates
    # -----------------------------------
    matched_terms = list(set(matched_terms))

    return {
        "score": score,
        "matched_terms": matched_terms
    }