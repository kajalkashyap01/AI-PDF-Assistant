
from __future__ import annotations

import re
from typing import Any

import cohere
from web_search import search_web


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

        text = message.lower().strip()

        patterns = [
            (r"\b(?:first|1st)\s+question\b", 1),
            (r"\b(?:second|2nd)\s+question\b", 2),
            (r"\b(?:third|3rd)\s+question\b", 3),
            (r"\b(?:fourth|4th)\s+question\b", 4),
            (r"\b(?:fifth|5th)\s+question\b", 5),
            (r"\b(?:sixth|6th)\s+question\b", 6),
            (r"\b(?:seventh|7th)\s+question\b", 7),
            (r"\b(?:eighth|8th)\s+question\b", 8),
            (r"\b(?:ninth|9th)\s+question\b", 9),
            (r"\b(?:tenth|10th)\s+question\b", 10),
        ]

        for pattern, number in patterns:
            if re.search(pattern, text):
                return number

        numeric_patterns = [
            r"\bquestion\s+(?:number\s*)?(\d{1,2})\b",
            r"\bq\s*\.?\s*(\d{1,2})\b",
        ]

        for pattern in numeric_patterns:
            match = re.search(pattern, text)

            if match:
                return int(match.group(1))

        return None

    # -------------------------------------------------
    # PDF PAGE TEXT
    # -------------------------------------------------

    def get_ordered_pages(self) -> list[dict[str, Any]]:

        page_texts = getattr(
            self.vectorstore,
            "page_texts",
            [],
        )

        if not page_texts:
            return []

        pages = []

        for index, item in enumerate(page_texts, start=1):

            if not isinstance(item, dict):
                continue

            text = str(item.get("text", "")).strip()

            if not text:
                continue

            page_number = item.get("page", index)

            try:
                page_number = int(page_number)
            except (TypeError, ValueError):
                page_number = index

            pages.append({
                "page": page_number,
                "text": text,
            })

        return sorted(
            pages,
            key=lambda item: item["page"],
        )

    # -------------------------------------------------
    # QUESTION HEADING DETECTION
    # -------------------------------------------------

    def get_question_headings(
        self,
        document_text: str,
    ) -> list[re.Match]:

        heading_pattern = re.compile(
            r"(?im)^[ \t]*"
            r"(?:Q(?:uestion)?)[ \t]*"
            r"(?:No\.?[ \t]*)?\.?[ \t]*"
            r"(\d{1,2})"
            r"(?=[ \t]*(?:[.):\-]|\([a-z]\)|[a-z]\)|$))"
        )

        return list(
            heading_pattern.finditer(document_text)
        )

    # -------------------------------------------------
    # EXTRACT QUESTION IN PDF ORDER
    # -------------------------------------------------

    def extract_question(
        self,
        question_number: int,
    ) -> tuple[str | None, list[dict[str, Any]]]:

        pages = self.get_ordered_pages()

        if not pages:
            return None, []

        document_parts = []
        page_positions = []
        current_position = 0

        for page in pages:

            page_text = page["text"]

            start = current_position
            end = start + len(page_text)

            page_positions.append({
                "page": page["page"],
                "start": start,
                "end": end,
            })

            document_parts.append(page_text)
            current_position = end + 2

        document_text = "\n\n".join(document_parts)

        headings = self.get_question_headings(
            document_text
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
            if next_heading is not None
            else len(document_text)
        )

        question_text = document_text[start:end].strip()

        if not question_text:
            return None, []

        source_pages = []

        for position in page_positions:

            page_start = position["start"]
            page_end = position["end"]

            overlap_start = max(start, page_start)
            overlap_end = min(end, page_end)

            if overlap_start >= overlap_end:
                continue

            relative_start = overlap_start - page_start
            relative_end = overlap_end - page_start

            page = next(
                (
                    item for item in pages
                    if item["page"] == position["page"]
                ),
                None,
            )

            if page is None:
                continue

            page_content = page["text"][
                relative_start:relative_end
            ].strip()

            if page_content:
                source_pages.append({
                    "page": position["page"],
                    "source": getattr(
                        self.vectorstore,
                        "pdf_path",
                        "Uploaded PDF",
                    ),
                    "text": page_content,
                })

        return question_text, source_pages

    # -------------------------------------------------
    # NORMALIZE RETRIEVED SOURCES
    # -------------------------------------------------

    def normalize_source(
        self,
        document: dict[str, Any],
    ) -> dict[str, Any]:

        metadata = document.get("metadata", {})

        if not isinstance(metadata, dict):
            metadata = {}

        text = (
            document.get("text")
            or metadata.get("text")
            or metadata.get("chunk_text")
            or ""
        )

        page = (
            document.get("page")
            or metadata.get("page")
            or metadata.get("page_number")
            or "Unknown"
        )

        source = (
            document.get("source")
            or metadata.get("source")
            or metadata.get("filename")
            or getattr(
                self.vectorstore,
                "pdf_path",
                "Uploaded PDF",
            )
        )

        return {
            "text": str(text).strip(),
            "page": page,
            "source": str(source),
            "source_type": "pdf",
        }

    # -------------------------------------------------
    # NORMAL SEMANTIC RETRIEVAL
    # -------------------------------------------------

    def retrieve_sources(
        self,
        user_message: str,
    ) -> list[dict[str, Any]]:

        if not user_message.strip():
            return []

        retrieved_documents = self.vectorstore.retrieve(
            user_message
        )

        if not retrieved_documents:
            return []

        normalized_documents = []

        for document in retrieved_documents:

            if not isinstance(document, dict):
                continue

            normalized = self.normalize_source(document)

            if normalized["text"]:
                normalized_documents.append(normalized)

        return normalized_documents

    # -------------------------------------------------
    # WEB SEARCH
    # -------------------------------------------------

    def retrieve_web_sources(
        self,
        search_query: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:

        if not search_query.strip():
            return []

        try:

            results = search_web(
                search_query,
                max_results=max_results,
            )

            web_sources = []

            for index, item in enumerate(results, start=1):

                if not isinstance(item, dict):
                    continue

                content = str(
                    item.get("content", "")
                ).strip()

                url = str(
                    item.get("url", "")
                ).strip()

                if not content:
                    continue

                title = str(
                    item.get("title", "Web source")
                ).strip()

                web_sources.append({
                    "text": content,
                    "page": "Web",
                    "source": title,
                    "title": title,
                    "url": url,
                    "score": item.get("score", 0),
                    "source_type": "web",
                    "web_number": index,
                })

            return web_sources

        except Exception as error:
            print(f"Web search error: {error}")
            return []

    # -------------------------------------------------
    # COMBINE PDF AND WEB SOURCES
    # -------------------------------------------------

    def combine_sources(
        self,
        pdf_sources: list[dict[str, Any]],
        web_sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        combined = []

        for source in pdf_sources:
            item = dict(source)
            item["source_type"] = "pdf"
            combined.append(item)

        combined.extend(web_sources)

        return combined

    # -------------------------------------------------
    # PREPARE PDF CONTEXT
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
            source = document.get(
                "source",
                "Uploaded PDF",
            )

            documents.append({
                "text": (
                    f"[PDF SOURCE]\n"
                    f"Source: {source}\n"
                    f"Page: {page}\n"
                    f"Content:\n{text}"
                )
            })

        return documents

    # -------------------------------------------------
    # PREPARE WEB CONTEXT
    # -------------------------------------------------

    def build_web_chat_documents(
        self,
        web_sources: list[dict[str, Any]],
    ) -> list[dict[str, str]]:

        documents = []

        for source in web_sources:

            documents.append({
                "text": (
                    "[WEB SOURCE]\n"
                    f"Title: {source.get('title', 'Web source')}\n"
                    f"URL: {source.get('url', '')}\n"
                    f"Content:\n{source.get('text', '')}"
                )
            })

        return documents

    # -------------------------------------------------
    # AI INSTRUCTIONS
    # -------------------------------------------------

    def get_preamble(self) -> str:

        return """
You are an expert academic assignment-solving assistant.

The user uploads a PDF containing academic questions,
study material, examples and other educational content.

Your responsibility is to understand the exact question
and provide a correct, complete, assignment-ready solution.

GENERAL ANSWERING RULES:

1. Answer the exact question asked by the user.
2. Use the uploaded PDF as the primary source for question details.
3. Use your subject knowledge to solve questions when the PDF
   contains questions but does not provide their answers.
4. Never invent values, question statements or requirements.
5. Include all requested subquestions.
6. Do not unnecessarily repeat the question.
7. Keep answers concise but sufficiently detailed for the marks.
8. Use simple, clear academic language.
9. Use tables for comparisons when appropriate.
10. Use bullet points for theory answers.
11. Include diagrams when the question requires them.
12. Do not omit important information to make an answer shorter.

PDF CONTEXT RULES:

1. Carefully read the provided PDF question and context.
2. Treat the extracted question as the main task.
3. Use relevant supporting information from the PDF.
4. Do not confuse examples with the actual question.
5. Do not combine unrelated questions.
6. Preserve all given values and conditions.
7. If the PDF contains multiple subquestions, answer every one
   requested by the user.
8. If the question continues across pages, consider the complete
   question rather than only the first page.
9. Never claim that a question cannot be solved merely because
   its solution is absent from the PDF.

NUMERICAL PROBLEM RULES:

For every numerical problem:

1. Write the given values.
2. Identify what needs to be calculated.
3. Write the relevant formula.
4. Substitute the given values.
5. Show the important calculation steps.
6. Include correct units.
7. Explain the result briefly where necessary.
8. Highlight the final answer.
9. Verify the arithmetic before presenting the result.

NETWORKING NUMERICALS:

For subnetting, routing, transmission delay,
bandwidth, throughput, congestion control and
other networking problems:

- Use the correct networking formula.
- Show calculations step by step.
- Include intermediate results where necessary.
- Use correct units and conversions.
- Include routing tables or diagrams when required.

SOURCE RULES:

1. Use retrieved PDF content to understand the question.
2. Do not treat retrieved passages as the answer if they
   do not actually answer the question.
3. Use subject knowledge for calculations and explanations.
4. Do not change the question's given values.
5. Mention PDF page numbers when available.
6. If information is genuinely missing, state that clearly.

FORMATTING:

Use suitable headings such as:

**Answer**
**Explanation**
**Given**
**Formula**
**Calculation**
**Final Answer**

Keep the final response readable, accurate and
suitable for a college assignment.

--------------------------------------------------
ADDITIONAL WEB SEARCH AND INDEPENDENT SOLVING RULES
--------------------------------------------------

1. The uploaded PDF is the primary source for understanding
   the user's question.

2. The PDF may contain questions without their solutions.
   This does not mean the question cannot be answered.

3. Use your own subject knowledge, logical reasoning,
   formulas and calculations to solve questions.

4. Additional web search results may be provided as
   supporting context.

5. Use web information when the PDF does not contain enough
   information or when additional verification is required.

6. Do not blindly copy web search results. Verify that they
   are relevant and technically correct.

7. Never refuse to solve a question merely because its
   solution is absent from the uploaded PDF.

8. Clearly distinguish information obtained from the PDF
   and information obtained from external web sources.

9. Never invent a web source, URL, citation or reference.

10. If web results are irrelevant or insufficient, solve
    the question using your own subject knowledge.

PART-SPECIFIC QUESTION RULE:

1. Always read the user's complete request carefully.

2. If the user asks for a particular subquestion, such as
   Question 5(b), Question 5(ii), or only the second part,
   solve ONLY that requested part.

3. Do not solve the other parts unless the user asks for them.

4. If the user requests the complete question, solve all
   its required subquestions.

5. The user's requested scope takes priority over the
   general instruction to include all subquestions.

--------------------------------------------------
DIAGRAM AND FLOWCHART GENERATION RULES
--------------------------------------------------

IMPORTANT: You are capable of creating diagrams using
Mermaid syntax. Your response must contain the actual
diagram code whenever a diagram is requested.

1. NEVER respond with statements such as:
   - "I am unable to draw diagrams."
   - "Unfortunately, I cannot draw diagrams."
   - "I cannot provide a diagram."
   - "I do not know how to draw diagrams."
   - "As an AI, I cannot create diagrams."

2. When the user requests a diagram, generate it directly
   using Mermaid syntax.

3. Put the Mermaid diagram inside a fenced code block
   using exactly this opening marker:

   ```mermaid

4. Always close the Mermaid code block with three
   backticks.

5. Do not put Mermaid code inside an ordinary code block.
   The code block must be labelled mermaid so that
   the application can render it.

6. Select the appropriate Mermaid diagram type:

   - Flowcharts: flowchart TD
   - Horizontal flowcharts: flowchart LR
   - Sequence diagrams: sequenceDiagram
   - Class diagrams: classDiagram
   - State diagrams: stateDiagram-v2
   - Entity relationship diagrams: erDiagram
   - Network topologies: graph TD or graph LR

7. For computer networks, use technically correct
   routers, switches, hosts, servers, links and labels.

8. For architecture diagrams, show the important
   components and their connections.

9. For sequence diagrams, show the participants,
   messages and correct direction of communication.

10. For process diagrams, show the correct order of
    steps and decision branches.

11. For numerical problems, calculate the values
    before placing them in a diagram.

12. Do not invent components or connections that
    contradict the question or uploaded PDF.

13. Add a short explanation before or after the diagram
    whenever useful.

14. If the user asks for a diagram only, provide the
    diagram without unnecessary theory.

15. If the user asks for both an explanation and a diagram,
    provide both.

16. If the question explicitly asks for a diagram,
    the actual Mermaid code is compulsory.

17. Before completing your answer, verify that the
    Mermaid block is present, closed and syntactically
    complete.

EXAMPLE OF A VALID FLOWCHART:

```mermaid
flowchart TD
    A[Start] --> B[Read Input]
    B --> C{Input Valid?}
    C -->|Yes| D[Process Input]
    C -->|No| E[Show Error]
    E --> B
    D --> F[Display Result]
    F --> G[End]
```

EXAMPLE OF A VALID SEQUENCE DIAGRAM:

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant Database

    Client->>Server: Send Request
    Server->>Database: Query Data
    Database-->>Server: Return Data
    Server-->>Client: Send Response
```

Never replace a requested diagram with a text-only
description of how someone could draw it.

--------------------------------------------------
FINAL RESPONSE CHECK
--------------------------------------------------

Before sending every answer:

1. Check that the requested question has been answered.
2. Check that all requested parts are included.
3. Check numerical calculations and units.
4. Check that the response follows the requested scope.
5. If a diagram was requested, check that actual Mermaid
   code is included in a mermaid fenced code block.
6. Never claim inability to draw a diagram.
"""

    # -------------------------------------------------
    # GENERATE RESPONSE
    # -------------------------------------------------

    def respond(
        self,
        user_message: str,
    ):

        if not user_message.strip():
            raise ValueError("Please enter a question.")

        question_number = (
            self.get_requested_question_number(
                user_message
            )
        )

        # ---------------------------------------------
        # NUMBERED QUESTION HANDLING
        # ---------------------------------------------

        if question_number is not None:

            question_text, pdf_sources = (
                self.extract_question(question_number)
            )

            if not question_text:

                prompt = (
                    f"The user requested question number "
                    f"{question_number} from the uploaded PDF, "
                    f"but the question could not be identified. "
                    f"Politely explain that it could not be found. "
                    f"Do not invent or guess the question."
                )

                response_stream = self.cohere_client.chat_stream(
                    model=self.CHAT_MODEL,
                    message=prompt,
                    preamble=self.get_preamble(),
                )

                return response_stream, []

            # Search the web using the extracted question.
            web_sources = self.retrieve_web_sources(
                question_text,
                max_results=5,
            )

            all_sources = self.combine_sources(
                pdf_sources,
                web_sources,
            )

            documents = [{
                "text": (
                    "[PDF SOURCE]\n"
                    f"Question number: {question_number}\n"
                    f"Complete question extracted from PDF:\n"
                    f"{question_text}"
                )
            }]

            for source in pdf_sources:

                source_text = source.get(
                    "text", ""
                ).strip()

                if not source_text:
                    continue

                documents.append({
                    "text": (
                        "[PDF SUPPORTING CONTENT]\n"
                        f"Page: {source.get('page', 'Unknown')}\n"
                        f"{source_text}"
                    )
                })

            documents.extend(
                self.build_web_chat_documents(
                    web_sources
                )
            )

            prompt = f"""
The user wants an answer based on question number
{question_number} from the uploaded PDF.

ORIGINAL USER REQUEST:
{user_message}

COMPLETE QUESTION EXTRACTED FROM THE PDF:

{question_text}

YOUR TASK:

Understand the original user request and solve the
question according to the requested scope.

IMPORTANT REQUIREMENTS:

- If the user asks for only one part, solve only that part.
- If the user asks for the complete question, solve all parts.
- Do not solve unrelated questions or subquestions.
- Use the extracted PDF question as the authoritative
  question statement.
- Use relevant PDF content as supporting information.
- The PDF may contain questions without their solutions.
- Use your subject knowledge to solve them correctly.
- Use relevant web results for additional information
  or verification.
- Do not copy irrelevant web search results.
- Show calculations step by step for numerical problems.
- Include formulas, substitutions, units and final answers.
- Include tables or diagrams when required.
- Do not refuse simply because a solution is missing
  from the PDF.
- Make the answer suitable for a college assignment.

DIAGRAM REQUIREMENT:

If the question asks for a diagram, architecture,
flowchart, sequence diagram or network topology,
you MUST generate the actual diagram.

Use a fenced Mermaid code block beginning with
```mermaid and ending with three backticks.

Never say that you are unable to draw diagrams.
Do not replace the diagram with a text description.
"""

            response_stream = self.cohere_client.chat_stream(
                model=self.CHAT_MODEL,
                message=prompt,
                documents=documents if documents else None,
                preamble=self.get_preamble(),
            )

            return response_stream, all_sources

        # ---------------------------------------------
        # NORMAL SEMANTIC QUESTION HANDLING
        # ---------------------------------------------

        pdf_sources = self.retrieve_sources(
            user_message
        )

        web_sources = self.retrieve_web_sources(
            user_message,
            max_results=5,
        )

        all_sources = self.combine_sources(
            pdf_sources,
            web_sources,
        )

        chat_documents = self.build_chat_documents(
            pdf_sources
        )

        web_documents = self.build_web_chat_documents(
            web_sources
        )

        combined_documents = (
            chat_documents + web_documents
        )

        prompt = f"""
Answer the user's question accurately.

USER QUESTION:
{user_message}

Use the uploaded PDF as the primary source.

If the PDF does not contain sufficient information,
use relevant web search results and your own subject
knowledge to construct the answer.

Do not assume that the PDF must contain a ready-made
solution.

If the user asks for only a specific part, answer only
that part.

For numerical problems, show the calculation steps.
For theory questions, provide a clear academic answer.

DIAGRAM REQUIREMENT:

If the user requests a diagram, flowchart, architecture,
sequence diagram, network topology or graphical
representation, generate the actual diagram using Mermaid.

Put the diagram inside a fenced code block labelled
mermaid, for example:

```mermaid
flowchart TD
    A[Start] --> B[Process]
    B --> C[End]
```

Do not say that you cannot draw diagrams.
Do not provide only a text description instead of
the requested diagram.

Do not refuse merely because the solution is missing
from the PDF.
"""

        response_stream = self.cohere_client.chat_stream(
            model=self.CHAT_MODEL,
            message=prompt,
            documents=(
                combined_documents
                if combined_documents
                else None
            ),
            preamble=self.get_preamble(),
        )

        return response_stream, all_sources
