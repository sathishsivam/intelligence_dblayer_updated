class SessionStore:
    def __init__(self):
        self.sessions = {}

    def create(self, session_id: str, data: dict):
        self.sessions[session_id] = data

    def get(self, session_id: str):
        return self.sessions.get(session_id)

    def update(self, session_id: str, patch: dict):
        if session_id in self.sessions:
            self.sessions[session_id].update(patch)


# Singleton instance used across the application
session_store = SessionStore()
