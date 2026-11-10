# AI PDF Assistant – RAG-Based Document Question Answering System 🤖📄

An AI-powered PDF Question Answering Assistant built using **Retrieval-Augmented Generation (RAG)**. It allows users to upload PDF documents, ask questions based on their content, and receive context-aware answers using relevant information retrieved from the uploaded documents.

The application combines **Python, Streamlit, Cohere, Pinecone, and SQLite** to provide an interactive document question-answering experience.

## ✨ Features

- **PDF Upload and Processing:** Upload PDF documents and extract their text using PyMuPDF.
- **Text Chunking:** Divide extracted document text into smaller chunks for efficient processing and retrieval.
- **Text Embeddings:** Use Cohere embedding models to convert document chunks into numerical vector representations.
- **Vector Storage and Retrieval:** Store and retrieve document embeddings using Pinecone.
- **Semantic Reranking:** Use Cohere's reranking capabilities to improve the relevance of retrieved document content.
- **AI-Powered Question Answering:** Generate context-aware responses using Cohere's language model and retrieved document information.
- **Interactive PDF Viewer:** View uploaded PDF documents within the application.
- **Chat Interface:** Ask questions and interact with the uploaded document through a conversational interface.
- **Conversation History:** Maintain previous conversations using a local SQLite database.
- **Document Management:** Manage uploaded documents through the application interface.
- **Custom User Interface:** A structured and styled interface developed using Streamlit and custom CSS.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Streamlit | Web application interface |
| Cohere | Text embeddings, reranking, and AI response generation |
| Pinecone | Vector database for storing and retrieving embeddings |
| PyMuPDF | PDF text extraction and rendering |
| SQLite | Local conversation and history storage |
| Python-dotenv | Environment variable and API key management |

## 🧠 How RAG Works in This Project

The application follows a Retrieval-Augmented Generation (RAG) workflow.

1. **Document Upload:** The user uploads a PDF document through the Streamlit interface.
2. **Text Extraction:** PyMuPDF extracts the text from the uploaded PDF.
3. **Text Chunking:** The extracted text is divided into smaller chunks.
4. **Embedding Generation:** Cohere converts the text chunks into vector embeddings.
5. **Vector Storage:** The embeddings are stored in Pinecone.
6. **Question Processing:** The user enters a question about the uploaded document.
7. **Similarity Search:** Pinecone retrieves relevant document chunks based on the question.
8. **Reranking:** Cohere reranks the retrieved chunks to identify the most relevant context.
9. **Answer Generation:** Cohere's language model uses the retrieved context to generate a response.
10. **Response Display:** The generated answer is displayed in the Streamlit chat interface.

## 📁 Project Structure

```text
AI-PDF-Assistant/
│
├── .devcontainer/
│
├── src/
│   ├── app.py
│   ├── chatbot.py
│   ├── database.py
│   ├── vectorstore.py
│   │
│   ├── assets/
│   │   └── styles.css
│   │
│   ├── components/
│   │   ├── __init__.py
│   │   ├── sidebar.py
│   │   ├── topbar.py
│   │   ├── pdf_viewer.py
│   │   ├── chat_panel.py
│   │   └── conversation_panel.py
│   │
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── documents.py
│   │   ├── settings.py
│   │   └── about.py
│   │
│   └── data/
│
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

### Main Files and Their Responsibilities

- **app.py:** Main entry point of the Streamlit application.
- **chatbot.py:** Handles question answering and interaction with the Cohere language model.
- **vectorstore.py:** Handles PDF processing, text chunking, embeddings, and vector retrieval.
- **database.py:** Manages local SQLite database operations.
- **components/:** Contains reusable interface components such as the sidebar, topbar, PDF viewer, and chat panels.
- **pages/:** Contains the Documents, Settings, and About pages.
- **assets/styles.css:** Contains custom CSS styling for the application.
- **requirements.txt:** Lists the Python dependencies required to run the project.

## 🚀 How to Run the Project

Follow these steps to set up and run the application on your local system.

### 1. Clone the Repository

Clone the repository using:

```bash
git clone https://github.com/kajalkashyap01/AI-PDF-Assistant.git
cd AI-PDF-Assistant
```

### 2. Create a Virtual Environment

Create a virtual environment to manage project dependencies:

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
source venv/bin/activate
```

### 4. Install Dependencies

Install all the required Python packages:

```bash
pip install -r requirements.txt
```

### 5. Configure API Keys

The application requires API keys from Cohere and Pinecone.

Obtain your API keys from:

- **Cohere:** https://dashboard.cohere.com/
- **Pinecone:** https://app.pinecone.io/

Create a `.env` file in the project root directory (the same directory as `requirements.txt`).

Add the following configuration:

```env
COHERE_API_KEY=your_cohere_api_key
PINECONE_API_KEY=your_pinecone_api_key
```

Replace the placeholder values with your actual API keys.

**Important:** Never share your API keys or upload your `.env` file to GitHub. The repository includes `.env.example` to show the required configuration.

### 6. Run the Application

Navigate to the `src` directory:

```bash
cd src
```

Start the Streamlit application:

```bash
streamlit run app.py
```

### 7. Open the Application

After running the command, Streamlit will provide a local URL.

Open the following address in your browser:

```text
http://localhost:8501
```

### 8. Upload a PDF Document

Upload a PDF document through the application interface. The system will process the document and prepare its content for question answering.

### 9. Ask Questions

Enter questions related to the uploaded PDF in the chat interface.

The application retrieves relevant information from the document and generates context-aware answers using the RAG pipeline.

## 🔮 Future Enhancements

The project can be extended with the following improvements:

- Support for multiple document formats such as DOCX and TXT.
- Multilingual document processing and question answering.
- Improved retrieval accuracy and answer generation.
- Export and download options for conversation history.
- Cloud deployment for wider accessibility.
- Additional vector database integrations.
- Enhanced document management and search capabilities.

## 🤝 Contributing

Contributions are welcome!

If you would like to improve this project, you can:

- Report bugs and issues.
- Suggest new features.
- Improve the user interface.
- Optimize document retrieval and processing.
- Improve project documentation.

Feel free to fork the repository and submit a pull request.

## 📜 License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for more information.

## 🙏 Acknowledgments

- **Cohere** for providing language models, embedding, and reranking capabilities.
- **Pinecone** for vector database and similarity search functionality.
- **Streamlit** for providing an easy way to build interactive Python applications.
- **PyMuPDF** for PDF text extraction and document rendering.

---

**Developed as an AI-powered document question-answering project using Retrieval-Augmented Generation (RAG).**