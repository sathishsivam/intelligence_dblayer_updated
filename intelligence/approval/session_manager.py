from session import session_store


def get_session(session_id):

    return session_store.get(session_id)


def update_session(session_id, values):

    session_store.update(
        session_id,
        values,
    )
    
def get_runtime_context(session_id: str):
    session = get_session(session_id)

    if session is None:
        return None

    return session.get("runtime_context")