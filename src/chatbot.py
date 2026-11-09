
from __future__ import annotations

import re
from typing import Any

import cohere


class Chatbot:
    CHAT_MODEL = "command-a-03-2025"

    def __init__(
        self,
        vectorstore: Any,
        cohere_api_key: str,
    ) -> None:

        if not cohere_api_key:
            raise ValueError("COHERE_API_KEY is missing.")

        self.vectorstore = vectorstore
        self.cohere_client = cohere.Client(cohere_api_key)

    # -------------------------------------------------
    # QUESTION DETECTION
    # -------------------------------------------------

    def get_requested_question_number(
        self,
        message: str,
    ) -> int | None:
        """Detect requests for a numbered PDF question."""

        text = message.lower().strip()

        patterns = [
            r"\b(?:first|1st)\s+question\b",
            r"\bquestion\s+(?:number\s+)?1\b",
            r"\bq\s*1\b",
            r"\bq1\b",
        ]

        if any(re.search(pattern, text) for pattern in patterns):
            return 1

        match = re.search(
            r"\b(?:question|q)\s*(?:number\s*)?(\d{1,2})\b",
            text,
        )

        if match:
            return int(match.group(1))

        return None

    # -------------------------------------------------
    # EXTRACT QUESTION IN PDF ORDER
    # -------------------------------------------------

    def extract_question(
        self,
        question_number: int,
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """
        Extract a complete top-level question from the PDF
        in original page order, including its subquestions.
        """

        page_texts = getattr(
            self.vectorstore,
            "page_texts",
            [],
        )

        if not page_texts:
            return None, []

        ordered_pages = sorted(
            page_texts,
            key=lambda item: item["page"],
        )

        document_text = "\n\n".join(
            page["text"]
            for page in ordered_pages
        )

        # Find headings such as Q1., Q2., Q10.
        heading_pattern = re.compile(
            r"(?im)^[ \t]*Q[ \t]*(\d{1,2})[ \t]*[.:]"
        )

        headings = list(
            heading_pattern.finditer(document_text)
        )

        selected_heading = None
        next_heading = None

        for index, heading in enumerate(headings):

            if int(heading.group(1)) == question_number:
                selected_heading = heading

                if index + 1 < len(headings):
                    next_heading = headings[index + 1]

                break

        if selected_heading is None:
            return None, []

        start = selected_heading.start()

        end = (
            next_heading.start()
            if next_heading
            else len(document_text)
        )

        question_text = document_text[start:end].strip()

        # Keep the original page references.
        source_pages = []

        for page in ordered_pages:

            if page["text"].strip() in question_text:
                source_pages.append({
                    "page": page["page"],
                    "source": getattr(
                        self.vectorstore,
                        "pdf_path",
                        "Uploaded PDF",
                    ),
                    "text": page["text"],
                })

        if not source_pages:
            source_pages = [{
                "page": ordered_pages[0]["page"],
                "source": "Uploaded PDF",
                "text": question_text,
            }]

        return question_text, source_pages

    # -------------------------------------------------
    # NORMAL SEMANTIC RETRIEVAL
    # -------------------------------------------------

    def retrieve_sources(
        self,
        user_message: str,
    ) -> list[dict[str, Any]]:

        if not user_message.strip():
            return []

        return self.vectorstore.retrieve(user_message)

    # -------------------------------------------------
    # PREPARE DOCUMENT CONTEXT
    # -------------------------------------------------

    def build_chat_documents(
        self,
        retrieved_documents: list[dict[str, Any]],
    ) -> list[dict[str, str]]:

        documents = []

        for document in retrieved_documents:

            text = str(
                document.get("text", "")
            ).strip()

            if not text:
                continue

            page = document.get("page", "Unknown")
            source = document.get("source", "Uploaded PDF")

            documents.append({
                "text": (
                    f"Source: {source}\n"
                    f"Page: {page}\n"
                    f"Content:\n{text}"
                )
            })

        return documents

    # -------------------------------------------------
    # AI INSTRUCTIONS
    # -------------------------------------------------

    def get_preamble(self) -> str:

        return """
You are DocuMind AI, an expert academic assignment-solving assistant.

Your task is to solve questions extracted from the user's uploaded PDF.
The PDF may contain questions only and may not contain their solutions.
You must solve the questions using your subject knowledge.

IMPORTANT ANSWER FORMATTING RULES:

1. Give complete, correct and assignment-ready answers.
2. Keep answers concise but include all important points required by the marks.
3. Do not use very large headings.
4. Use small section headings such as:
   **Answer**
   **Explanation**
   **Calculation**
   **Final Answer**
5. Do not repeat the entire question unnecessarily.
6. Use tables wherever the question asks for comparisons.
7. Use bullet points for theory answers.
8. Avoid unnecessary introductions and conclusions.

NUMERICAL PROBLEM RULES:

Whenever a question contains numerical calculations:

1. Write the given values first.
2. Identify what needs to be calculated.
3. Write the correct formula.
4. Substitute the given values into the formula.
5. Show every important calculation step clearly.
6. Include correct units in the calculations.
7. Explain the result briefly where necessary.
8. Highlight the final answer clearly.
9. Never skip calculations or give only the final result.
10. Check the arithmetic and units before answering.

NETWORKING NUMERICALS:
For subnetting, transmission delay, bandwidth, throughput,
congestion window and other networking calculations,
show the relevant formula and step-by-step working.
For diagrams, provide a neat text-based diagram when appropriate.

SOURCE RULES:
Use the uploaded PDF to identify the exact question.
Do not claim that a question cannot be solved just because
the PDF does not contain its answer.
Do not change the question's given values or requirements.
Mention the PDF page number when available.

The final answer must be accurate, readable, properly structured,
and suitable for a college assignment.
"""

    # -------------------------------------------------
    # GENERATE RESPONSE
    # -------------------------------------------------

    def respond(
        self,
        user_message: str,
    ):

        question_number = (
            self.get_requested_question_number(
                user_message
            )
        )

        # SPECIAL HANDLING FOR NUMBERED QUESTIONS
        if question_number is not None:

            question_text, sources = (
                self.extract_question(question_number)
            )

            if not question_text:

                message = (
                    f"The user requested question number "
                    f"{question_number}, but that question "
                    f"could not be identified in the PDF. "
                    f"Explain this clearly without inventing "
                    f"the missing question."
                )

                return (
                    self.cohere_client.chat_stream(
                        model=self.CHAT_MODEL,
                        message=message,
                        preamble=self.get_preamble(),
                    ),
                    [],
                )

            prompt = f"""
The user wants the complete solution of question
number {question_number} from the uploaded PDF.

QUESTION EXTRACTED FROM THE PDF:

{question_text}

TASK:

Solve the entire question above.

IMPORTANT:
- Include every subquestion.
- Do not solve a different question.
- The PDF contains questions and may not contain solutions.
- Use your own subject knowledge to solve the question.
- Show all required calculations and explanations.
- Make the answer suitable for an academic assignment.
"""

            documents = [{
                "text": (
                    f"Question number: {question_number}\n"
                    f"PDF question:\n{question_text}"
                )
            }]

            response_stream = (
                self.cohere_client.chat_stream(
                    model=self.CHAT_MODEL,
                    message=prompt,
                    documents=documents,
                    preamble=self.get_preamble(),
                )
            )

            return response_stream, sources

        # NORMAL SEMANTIC QUESTION HANDLING

        retrieved_documents = self.retrieve_sources(
            user_message
        )

        chat_documents = self.build_chat_documents(
            retrieved_documents
        )

        response_stream = self.cohere_client.chat_stream(
            model=self.CHAT_MODEL,
            message=user_message,
            documents=chat_documents if chat_documents else None,
            preamble=self.get_preamble(),
        )

        return response_stream, retrieved_documents
