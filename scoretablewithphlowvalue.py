import re
from collections import Counter


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
    "find","columns","column","show","get","fetch","give",
    "table","tables",
}


LOW_VALUE_TERMS = {
    "id",
    "number",
    "name",
    "status",
    "type",
    "date",
    "code",
    "flag"
}




def build_term_frequency(all_schema_texts):

    counter = Counter()

    for schema in all_schema_texts:

        words = re.findall(r'\w+', schema.lower())

        unique_words = set(words)

        counter.update(unique_words)

    return counter


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



def score_table(query, schema_text, mapping_text=""):

    query = query.lower()

    schema = schema_text.lower()

    mapping = mapping_text.lower()

    score = 0

    matched_terms = []

    query_terms = extract_query_terms(query)

    phrases = extract_dynamic_phrases(mapping_text)

    # -----------------------------------
    # PHRASE MATCH (Highest Priority)
    # -----------------------------------
    for phrase in phrases:

        if phrase in query:

            score += 60

            matched_terms.append(phrase)

    # -----------------------------------
    # COLUMN MATCH
    # -----------------------------------
    for term in query_terms:

        pattern = rf'\b{term}\b'

        if re.search(pattern, schema):

            # LOW VALUE TOKENS
            if term in LOW_VALUE_TERMS:

                score += 2

            else:

                score += 10

            matched_terms.append(term)

    # -----------------------------------
    # MAPPING MATCH
    # -----------------------------------
    for term in query_terms:

        pattern = rf'\b{term}\b'

        if re.search(pattern, mapping):

            if term in LOW_VALUE_TERMS:

                score += 5

            else:

                score += 20

            matched_terms.append(term)

    # -----------------------------------
    # PREFIX DENSITY BOOST
    # -----------------------------------
    beneficiary_cols = len(
        re.findall(r'beneficiary_', schema)
    )

    event_cols = len(
        re.findall(r'event_', schema)
    )

    branch_cols = len(
        re.findall(r'branch_', schema)
    )

    if "beneficiary" in query:

        score += beneficiary_cols * 15

    if "event" in query:

        score += event_cols * 15

    if "branch" in query:

        score += branch_cols * 15

    # -----------------------------------
    # REMOVE DUPLICATES
    # -----------------------------------
    matched_terms = list(set(matched_terms))

    return {
        "score": score,
        "matched_terms": matched_terms
    }
