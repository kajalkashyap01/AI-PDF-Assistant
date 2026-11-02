
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import cohere
import fitz
from pinecone import Pinecone, ServerlessSpec


class VectorStore:
    """
    Extract PDF text, create chunks and embeddings,
    store vectors in Pinecone, and retrieve relevant context.

    Supports two modes:
    1. New PDF: extract, chunk, embed and upload its vectors.
    2. Existing PDF: reconnect to its previously saved Pinecone namespace.
    """

    INDEX_NAME = "ai-assistant-pdf-index"

    EMBEDDING_MODEL = "embed-english-v3.0"
    RERANK_MODEL = "rerank-english-v3.0"

    EMBEDDING_DIMENSION = 1024

    RETRIEVE_TOP_K = 20
    RERANK_TOP_K = 6

    def __init__(
        self,
        pdf_path: str,
        cohere_api_key: str,
        pinecone_api_key: str,
        existing_namespace: str | None = None,
    ) -> None:

        if not cohere_api_key:
            raise ValueError("COHERE_API_KEY is missing.")

        if not pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is missing.")

        self.pdf_path = str(pdf_path)

        self.cohere_client = cohere.Client(cohere_api_key)

        self.pinecone_client = Pinecone(
            api_key=pinecone_api_key
        )

        self.chunks: list[dict[str, Any]] = []
        self.embeddings: list[list[float]] = []
        self.page_texts: list[dict[str, Any]] = []

        # Reopen an existing document without re-embedding it.
        if existing_namespace:
            self.document_namespace = existing_namespace
            self.connect_index()
            return

        # Process and index a new document.
        self.document_namespace = self._build_document_namespace()

        self.load_pdf()
        self.split_text()

        if not self.chunks:
            raise ValueError(
                "No readable text was found in this PDF. "
                "The PDF may be scanned or image-only. "
                "OCR is required for scanned pages."
            )

        self.embed_chunks()
        self.index_chunks()

    # -------------------------------------------------
    # PDF EXTRACTION
    # -------------------------------------------------

    def load_pdf(self) -> None:
        """Extract selectable text from every PDF page."""

        try:
            with fitz.open(self.pdf_path) as pdf_document:

                for page_number, page in enumerate(
                    pdf_document,
                    start=1,
                ):

                    page_text = page.get_text("text").strip()

                    if page_text:
                        self.page_texts.append({
                            "page": page_number,
                            "text": page_text,
                        })

        except FileNotFoundError as error:
            raise FileNotFoundError(
                f"PDF not found: {self.pdf_path}"
            ) from error

        except Exception as error:
            raise RuntimeError(
                f"PDF extraction failed: {error}"
            ) from error

        if not self.page_texts:
            raise ValueError(
                "No extractable text was found in the PDF. "
                "The document may require OCR."
            )

    # -------------------------------------------------
    # TEXT CHUNKING
    # -------------------------------------------------

    def split_text(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
    ) -> None:
        """
        Split PDF pages into overlapping chunks.
        Every chunk retains its original page number.
        """

        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")

        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size."
            )

        for page_data in self.page_texts:

            page_number = page_data["page"]

            page_text = " ".join(
                page_data["text"].split()
            )

            start = 0
            text_length = len(page_text)

            while start < text_length:

                end = min(
                    start + chunk_size,
                    text_length,
                )

                if end < text_length:
                    last_space = page_text.rfind(
                        " ", start, end
                    )

                    if last_space > start + chunk_size // 2:
                        end = last_space

                chunk_text = page_text[start:end].strip()

                if chunk_text:
                    self.chunks.append({
                        "text": chunk_text,
                        "page": page_number,
                        "source": Path(self.pdf_path).name,
                    })

                if end >= text_length:
                    break

                start = end - chunk_overlap

    # -------------------------------------------------
    # COHERE EMBEDDINGS
    # -------------------------------------------------

    def embed_chunks(self, batch_size: int = 90) -> None:
        """Generate embeddings in batches."""

        for start in range(0, len(self.chunks), batch_size):

            batch = self.chunks[
                start:start + batch_size
            ]

            response = self.cohere_client.embed(
                texts=[item["text"] for item in batch],
                model=self.EMBEDDING_MODEL,
                input_type="search_document",
            )

            batch_embeddings = response.embeddings

            if len(batch_embeddings) != len(batch):
                raise RuntimeError(
                    "Cohere returned an unexpected number of embeddings."
                )

            self.embeddings.extend(
                [list(vector) for vector in batch_embeddings]
            )

        for embedding in self.embeddings:
            if len(embedding) != self.EMBEDDING_DIMENSION:
                raise ValueError(
                    "Embedding dimension mismatch. "
                    f"Expected {self.EMBEDDING_DIMENSION}, "
                    f"received {len(embedding)}."
                )

    # -------------------------------------------------
    # PINECONE CONNECTION AND VALIDATION
    # -------------------------------------------------

    def connect_index(self) -> None:
        """
        Connect to the existing Pinecone index and validate it.
        Create the index only if it does not already exist.
        """

        existing_indexes = [
            item.name
            for item in self.pinecone_client.indexes.list()
        ]

        if self.INDEX_NAME not in existing_indexes:

            self.pinecone_client.create_index(
                name=self.INDEX_NAME,
                dimension=self.EMBEDDING_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1",
                ),
            )

        index_description = (
            self.pinecone_client.indexes.describe(
                self.INDEX_NAME
            )
        )

        fields = index_description.schema.fields

        dense_field = fields.get("_values")

        if dense_field is None:
            raise ValueError(
                "The existing Pinecone index does not contain "
                "the expected _values dense vector field."
            )

        if dense_field.dimension != self.EMBEDDING_DIMENSION:
            raise ValueError(
                "Pinecone index dimension does not match "
                "the Cohere embedding model."
            )

        if dense_field.metric != "cosine":
            raise ValueError(
                "Pinecone index must use cosine similarity."
            )

        self.index = self.pinecone_client.Index(
            self.INDEX_NAME
        )

    # -------------------------------------------------
    # VECTOR INDEXING
    # -------------------------------------------------

    def index_chunks(self) -> None:
        """Connect to Pinecone and upload the PDF chunks."""

        self.connect_index()
        self.upload_vectors()

    # -------------------------------------------------
    # VECTOR UPLOAD
    # -------------------------------------------------

    def upload_vectors(self) -> None:
        """Upload PDF chunks and their embeddings."""

        vector_records = []

        for index, (chunk, embedding) in enumerate(
            zip(self.chunks, self.embeddings)
        ):

            vector_records.append({
                "id": (
                    f"{self.document_namespace}"
                    f"-chunk-{index}"
                ),
                "values": embedding,
                "metadata": {
                    "text": chunk["text"],
                    "page": chunk["page"],
                    "source": chunk["source"],
                    "chunk_number": index + 1,
                },
            })

        self.index.upsert(
            vectors=vector_records,
            namespace=self.document_namespace,
            batch_size=100,
            show_progress=False,
        )

    # -------------------------------------------------
    # RETRIEVAL AND RERANKING
    # -------------------------------------------------

    def retrieve(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant PDF chunks using vector similarity
        and improve their order using Cohere reranking.
        """

        if not query or not query.strip():
            return []

        query_response = self.cohere_client.embed(
            texts=[query],
            model=self.EMBEDDING_MODEL,
            input_type="search_query",
        )

        query_embedding = list(
            query_response.embeddings[0]
        )

        pinecone_response = self.index.query(
            vector=query_embedding,
            top_k=self.RETRIEVE_TOP_K,
            include_metadata=True,
            namespace=self.document_namespace,
        )

        matches = getattr(
            pinecone_response,
            "matches",
            [],
        )

        retrieved_documents = []

        for match in matches:

            metadata = getattr(
                match,
                "metadata",
                None,
            )

            if metadata and metadata.get("text"):
                retrieved_documents.append(
                    dict(metadata)
                )

        if not retrieved_documents:
            return []

        rerank_response = self.cohere_client.rerank(
            query=query,
            documents=[
                document["text"]
                for document in retrieved_documents
            ],
            model=self.RERANK_MODEL,
            top_n=min(
                self.RERANK_TOP_K,
                len(retrieved_documents),
            ),
        )

        final_documents = []

        for result in rerank_response.results:

            result_index = result.index

            if 0 <= result_index < len(retrieved_documents):
                final_documents.append(
                    retrieved_documents[result_index]
                )

        return final_documents

    # -------------------------------------------------
    # DOCUMENT NAMESPACE
    # -------------------------------------------------

    def _build_document_namespace(self) -> str:
        """
        Generate a unique, stable namespace from PDF contents.
        """

        file_hash = hashlib.sha256()

        try:
            with open(self.pdf_path, "rb") as pdf_file:

                while True:
                    data = pdf_file.read(1024 * 1024)

                    if not data:
                        break

                    file_hash.update(data)

        except FileNotFoundError as error:
            raise FileNotFoundError(
                f"PDF not found: {self.pdf_path}"
            ) from error

        return f"pdf-{file_hash.hexdigest()[:16]}"
