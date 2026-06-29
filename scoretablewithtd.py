import re
from collections import Counter

# =========================================================
# STOP WORDS
# =========================================================
STOP_WORDS = {
    "the", "is", "am", "are", "was", "were",
    "be", "been", "being",
    "what", "which", "who", "where", "when",
    "how", "along", "with", "will", "shall",
    "can", "could", "would", "should",
    "a", "an", "of", "to", "in", "on", "for",
    "and", "or", "by", "from",
    "find", "show", "get", "fetch", "give",
    "table", "tables", "column", "columns"
}


# =========================================================
# QUERY TERM EXTRACTION
# =========================================================
def extract_query_terms(query: str):

    words = re.findall(r'\w+', query.lower())

    return [
        word for word in words
        if word not in STOP_WORDS
    ]


# =========================================================
# QUERY FEATURE EXTRACTION
# =========================================================
def extract_query_features(query):

    query_terms = extract_query_terms(query)

    phrases = []

    # -------------------------------
    # BIGRAMS
    # -------------------------------
    for i in range(len(query_terms) - 1):

        phrases.append(
            f"{query_terms[i]} {query_terms[i+1]}"
        )

    # -------------------------------
    # TRIGRAMS
    # -------------------------------
    for i in range(len(query_terms) - 2):

        phrases.append(
            f"{query_terms[i]} "
            f"{query_terms[i+1]} "
            f"{query_terms[i+2]}"
        )

    return query_terms, phrases


# =========================================================
# EXTRACT PHRASES FROM MAPPING
# =========================================================

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


# =========================================================
# BUILD TERM FREQUENCY
# =========================================================
"""
This function builds a document frequency dictionary for all candidate schemas. 
Its purpose is to identify which terms are common across many tables and 
which terms are rare and therefore more valuable for table ranking. 
"""
def build_term_frequency(all_schema_texts): # receive a list of schema texts.

    counter = Counter() #Creates an empty frequency dictionary.

    for schema in all_schema_texts:

        words = re.findall(r'\w+', schema.lower()) # matches:letters,numbers,underscores ,remains one token rather than being split example beneficiary_id.

        unique_words = set(words) # Remove Duplicates Within a Table

        counter.update(unique_words)

    return counter


# =========================================================
# DETECT LOW VALUE TERM DYNAMICALLY aka TERM IMPORTANCE ANALYZER
# =========================================================
def is_low_value_term(
        term,
        term_frequency,
        total_tables,
        threshold=0.40
):

    if not term_frequency:
        return False

    frequency_ratio = (
        term_frequency.get(term, 0) / total_tables
    )

    return frequency_ratio >= threshold


# =========================================================
# EXTRACT SCHEMA PREFIXES
# =========================================================
def extract_schema_prefixes(schema):

    prefixes = set()

    columns = re.findall(
        r'([a-zA-Z0-9]+)_',
        schema
    )

    for col in columns:

        prefixes.add(col)

    return prefixes


# =========================================================
# DYNAMIC PREFIX BOOST
# =========================================================
def calculate_dynamic_prefix_boost(query,schema):
    score = 0
    matched_terms = []
    query_terms = extract_query_terms(query)
    schema_prefixes = extract_schema_prefixes(schema)
    for term in query_terms:
        if term in schema_prefixes:
            prefix_count = len(
                re.findall(
                    rf'{re.escape(term)}_',
                    schema
                )
            )

            boost = prefix_count * 15

            score += boost

            matched_terms.append(term)

    return score, matched_terms

# =========================================================
# TOKEN COVERAGE SCORING
# =========================================================
def calculate_token_coverage(
        query_terms,
        schema,
        mapping
):

    matched = set()

    schema_words = set(
        re.findall(r'\w+', schema.lower())
    )

    mapping_words = set(
        re.findall(r'\w+', mapping.lower())
    )

    combined_words = (
        schema_words.union(mapping_words)
    )

    for term in query_terms:

        if term in combined_words:

            matched.add(term)

    if not query_terms:
        return 0, []

    coverage_ratio = (
        len(matched) / len(query_terms)
    )

    coverage_score = coverage_ratio * 100

    return coverage_score, list(matched)



# =========================================================
# REMOVAL OF REDUNDANT IN MATCHED_TERMS
# =========================================================

def remove_redundant_terms(matched_terms):

    final_terms = []

    sorted_terms = sorted(
        matched_terms,
        key=len,
        reverse=True
    )

    for term in sorted_terms:

        is_subterm = False

        for existing in final_terms:

            if term in existing and term != existing:

                is_subterm = True
                break

        if not is_subterm:


            final_terms.append(term)

    return final_terms


# =========================================================
# MAIN SCORING ENGINE
# =========================================================
def score_table(
        query,
        schema_text,
        mapping_text="",
        term_frequency=None,
        total_tables=1
):

    query = query.lower()

    schema = schema_text.lower()

    mapping = mapping_text.lower()

    score = 0

    matched_terms = []

    # =====================================================
    # QUERY FEATURES
    # =====================================================
    query_terms, query_phrases = (
        extract_query_features(query)
    )

    # =====================================================
    # MAPPING PHRASES
    # =====================================================
    mapping_phrases = (
        extract_dynamic_phrases(mapping_text)
    )


    # =====================================================
    # PHRASE MATCH
    # =====================================================
    for query_phrase in query_phrases:

        for mapping_phrase in mapping_phrases:

            # EXACT PHRASE MATCH
            if query_phrase == mapping_phrase:

                score += 80

                matched_terms.append(
                    query_phrase
                )

            # PARTIAL PHRASE MATCH
            elif (
                query_phrase in mapping_phrase
                or mapping_phrase in query_phrase
            ):

                score += 40

                matched_terms.append(
                    mapping_phrase
                )

    # =====================================================
    # COLUMN MATCH
    # =====================================================
    for term in query_terms:

        pattern = rf'\b{re.escape(term)}\b'

        if re.search(pattern, schema):

            if is_low_value_term(
                    term,
                    term_frequency,
                    total_tables
            ):

                score += 2

            else:

                score += 10

            matched_terms.append(term)

    # =====================================================
    # MAPPING MATCH
    # =====================================================
    for term in query_terms:

        pattern = rf'\b{re.escape(term)}\b'

        if re.search(pattern, mapping):

            if is_low_value_term(
                    term,
                    term_frequency,
                    total_tables
            ):

                score += 5

            else:

                score += 20

            matched_terms.append(term)

    # =====================================================
    # TOKEN COVERAGE
    # =====================================================
    coverage_score, coverage_terms = (
        calculate_token_coverage(
            query_terms,
            schema,
            mapping
        )
    )

    score += coverage_score

    matched_terms.extend(coverage_terms)

    # =====================================================
    # PREFIX BOOST
    # =====================================================
    prefix_score, prefix_terms = (
        calculate_dynamic_prefix_boost(
            query,
            schema
        )
    )

    score += prefix_score

    matched_terms.extend(prefix_terms)

    # =====================================================
    # REMOVE REDUNDANT TERMS 
    # =====================================================
    # matched_terms = list(set(matched_terms))
    matched_terms = remove_redundant_terms(
    list(set(matched_terms)))
    
    return {
        "score": round(score, 2),
        "matched_terms": matched_terms
    }
