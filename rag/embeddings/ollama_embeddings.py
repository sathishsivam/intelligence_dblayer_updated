from langchain_ollama import OllamaEmbeddings


class OllamaEmbeddingService:

    def __init__(
        self,
        model: str = "nomic-embed-text",
    ):
        self.model = model

        self.embeddings = OllamaEmbeddings(
            model=model,
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:
            return []

        return self.embeddings.embed_documents(
            texts
        )

    def embed_query(
        self,
        query: str,
    ) -> list[float]:

        return self.embeddings.embed_query(
            query
        )