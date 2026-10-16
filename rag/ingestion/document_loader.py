from pathlib import Path

import pymupdf


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
}


class DocumentLoader:

    def load(self, file_path: str) -> dict:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Document not found: {file_path}"
            )

        extension = path.suffix.lower()

        if extension == ".pdf":
            return self._load_pdf(path)

        if extension in {".txt", ".md"}:
            return self._load_text(path)

        raise ValueError(
            f"Unsupported document type: {extension}"
        )

    def _load_pdf(self, path: Path) -> dict:

        pages = []

        with pymupdf.open(path) as document:

            for page_number, page in enumerate(document, start=1):

                text = page.get_text("text")

                if text and text.strip():
                    pages.append(
                        {
                            "page_number": page_number,
                            "text": text.strip(),
                        }
                    )

            page_count = len(document)

        full_text = "\n\n".join(
            page["text"]
            for page in pages
        )

        return {
            "file_name": path.name,
            "file_type": ".pdf",
            "page_count": page_count,
            "text": full_text,
            "pages": pages,
        }

    def _load_text(self, path: Path) -> dict:

        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        return {
            "file_name": path.name,
            "file_type": path.suffix.lower(),
            "page_count": 1,
            "text": text,
            "pages": [
                {
                    "page_number": 1,
                    "text": text,
                }
            ],
        }