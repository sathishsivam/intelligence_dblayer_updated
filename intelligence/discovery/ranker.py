def rank_tables(ranked_tables):

    ranked_tables.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return ranked_tables