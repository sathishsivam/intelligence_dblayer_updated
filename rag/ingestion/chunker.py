from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentChunker:

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],
        )

    def chunk(
        self,
        document: dict,
    ) -> list[dict]:

        chunks = []

        for page in document["pages"]:

            page_text = page["text"]

            page_chunks = self.splitter.split_text(
                page_text
            )

            for index, chunk_text in enumerate(
                page_chunks
            ):

                if not chunk_text.strip():
                    continue

                chunks.append(
                    {
                        "chunk_index": len(chunks),
                        "page_number": page["page_number"],
                        "text": chunk_text.strip(),
                    }
                )

        return chunks