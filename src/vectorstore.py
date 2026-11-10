
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import cohere
import fitz
from pinecone import Pinecone, ServerlessSpec


class VectorStore:
    """
    Extract PDF text, create meaningful overlapping chunks,
    generate Cohere embeddings, store vectors in Pinecone,
    and retrieve relevant context using vector search and reranking.
    """

    INDEX_NAME = "ai-assistant-pdf-index"

    EMBEDDING_MODEL = "embed-english-v3.0"
    RERANK_MODEL = "rerank-english-v3.0"

    EMBEDDING_DIMENSION = 1024

    RETRIEVE_TOP_K = 30
    RERANK_TOP_K = 10

    DEFAULT_CHUNK_SIZE = 1800
    DEFAULT_CHUNK_OVERLAP = 300

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

        self.index = None

        if existing_namespace:
            self.document_namespace = existing_namespace
            self.connect_index()
            return

        self.document_namespace = (
            self._build_document_namespace()
        )

        self.load_pdf()
        self.split_text()

        if not self.chunks:
            raise ValueError(
                "No readable text was found in this PDF. "
                "The document may be scanned or image-only. "
                "OCR is required for scanned pages."
            )

        self.embed_chunks()
        self.index_chunks()

    # -------------------------------------------------
    # PDF EXTRACTION
    # -------------------------------------------------

    def load_pdf(self) -> None:
        """
        Extract selectable text from every PDF page.

        PDF page numbers are stored using normal
        human-readable numbering starting from page 1.
        """

        self.page_texts.clear()

        try:
            with fitz.open(self.pdf_path) as pdf_document:

                for page_number, page in enumerate(
                    pdf_document,
                    start=1,
                ):

                    page_text = page.get_text("text").strip()

                    if not page_text:
                        continue

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

    @staticmethod
    def _split_long_paragraph(
        paragraph: str,
        chunk_size: int,
    ) -> list[str]:
        """
        Split an oversized paragraph at sentence or word
        boundaries instead of cutting arbitrary text.
        """

        if len(paragraph) <= chunk_size:
            return [paragraph]

        sentences = re.split(
            r"(?<=[.!?])\s+",
            paragraph,
        )

        pieces = []
        current = ""

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            if len(sentence) > chunk_size:

                if current:
                    pieces.append(current)
                    current = ""

                start = 0

                while start < len(sentence):

                    end = min(
                        start + chunk_size,
                        len(sentence),
                    )

                    if end < len(sentence):
                        last_space = sentence.rfind(
                            " ", start, end
                        )

                        if last_space > start:
                            end = last_space

                    pieces.append(
                        sentence[start:end].strip()
                    )

                    start = end

                continue

            candidate = (
                f"{current} {sentence}".strip()
                if current
                else sentence
            )

            if len(candidate) <= chunk_size:
                current = candidate

            else:
                if current:
                    pieces.append(current)

                current = sentence

        if current:
            pieces.append(current)

        return pieces

    def split_text(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        """
        Create overlapping chunks while preserving page numbers
        and paragraph boundaries wherever possible.
        """

        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be positive."
            )

        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size."
            )

        self.chunks.clear()

        for page_data in self.page_texts:

            page_number = page_data["page"]
            original_text = page_data["text"]

            paragraphs = [
                " ".join(paragraph.split())
                for paragraph in re.split(
                    r"\n\s*\n",
                    original_text,
                )
                if paragraph.strip()
            ]

            if not paragraphs:
                paragraphs = [
                    " ".join(original_text.split())
                ]

            # Handle PDFs where every line is separated
            # by a single newline.
            if len(paragraphs) == 1:
                paragraphs = [
                    " ".join(original_text.split())
                ]

            expanded_paragraphs = []

            for paragraph in paragraphs:
                expanded_paragraphs.extend(
                    self._split_long_paragraph(
                        paragraph,
                        chunk_size,
                    )
                )

            current_chunk = ""

            for paragraph in expanded_paragraphs:

                candidate = (
                    f"{current_chunk}\n{paragraph}".strip()
                    if current_chunk
                    else paragraph
                )

                if len(candidate) <= chunk_size:
                    current_chunk = candidate
                    continue

                if current_chunk:
                    self.chunks.append({
                        "text": current_chunk,
                        "page": page_number,
                        "source": Path(self.pdf_path).name,
                    })

                # Preserve the end of the previous chunk
                # to maintain context across boundaries.
                overlap_text = ""

                if current_chunk and chunk_overlap > 0:
                    overlap_text = current_chunk[
                        -chunk_overlap:
                    ].lstrip()

                    if " " in overlap_text:
                        overlap_text = overlap_text[
                            overlap_text.find(" ") + 1:
                        ]

                current_chunk = (
                    f"{overlap_text}\n{paragraph}".strip()
                    if overlap_text
                    else paragraph
                )

                # Safety handling for an oversized paragraph.
                if len(current_chunk) > chunk_size:

                    pieces = self._split_long_paragraph(
                        current_chunk,
                        chunk_size,
                    )

                    for piece in pieces[:-1]:
                        self.chunks.append({
                            "text": piece,
                            "page": page_number,
                            "source": Path(self.pdf_path).name,
                        })

                    current_chunk = pieces[-1]

            if current_chunk.strip():
                self.chunks.append({
                    "text": current_chunk,
                    "page": page_number,
                    "source": Path(self.pdf_path).name,
                })

        # Add stable chunk numbering.
        for index, chunk in enumerate(self.chunks, start=1):
            chunk["chunk_number"] = index

    # -------------------------------------------------
    # COHERE EMBEDDINGS
    # -------------------------------------------------

    def embed_chunks(
        self,
        batch_size: int = 90,
    ) -> None:
        """Generate document embeddings in batches."""

        self.embeddings.clear()

        for start in range(0, len(self.chunks), batch_size):

            batch = self.chunks[
                start:start + batch_size
            ]

            response = self.cohere_client.embed(
                texts=[
                    item["text"]
                    for item in batch
                ],
                model=self.EMBEDDING_MODEL,
                input_type="search_document",
            )

            batch_embeddings = response.embeddings

            if len(batch_embeddings) != len(batch):
                raise RuntimeError(
                    "Cohere returned an unexpected number "
                    "of embeddings."
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
    # PINECONE CONNECTION
    # -------------------------------------------------

    def connect_index(self) -> None:
        """Connect to the Pinecone index and validate it."""

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
        """Connect to Pinecone and upload PDF chunks."""

        self.connect_index()
        self.upload_vectors()

    # -------------------------------------------------
    # VECTOR UPLOAD
    # -------------------------------------------------

    def upload_vectors(self) -> None:
        """Upload chunks, embeddings and metadata."""

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
                    "chunk_number": chunk["chunk_number"],
                },
            })

        if not vector_records:
            raise ValueError(
                "There are no vectors to upload."
            )

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
        Retrieve relevant chunks using semantic search
        and improve their ranking using Cohere reranking.
        """

        if not query or not query.strip():
            return []

        query = query.strip()

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

            if isinstance(match, dict):
                metadata = match.get("metadata")
                score = match.get("score")
            else:
                metadata = getattr(
                    match,
                    "metadata",
                    None,
                )
                score = getattr(
                    match,
                    "score",
                    None,
                )

            if not metadata or not metadata.get("text"):
                continue

            document = dict(metadata)

            if score is not None:
                document["similarity_score"] = score

            retrieved_documents.append(document)

        if not retrieved_documents:
            return []

        # Return vector-search results if reranking fails.
        try:

            rerank_documents = [
                (
                    f"[Page {document.get('page', 'Unknown')}]\n"
                    f"{document['text']}"
                )
                for document in retrieved_documents
            ]

            rerank_response = self.cohere_client.rerank(
                query=query,
                documents=rerank_documents,
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

            if final_documents:
                return final_documents

        except Exception:
            pass

        return retrieved_documents[
            :self.RERANK_TOP_K
        ]

    # -------------------------------------------------
    # DOCUMENT NAMESPACE
    # -------------------------------------------------

    def _build_document_namespace(self) -> str:
        """Generate a stable namespace from PDF contents."""

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
