# src/tools/vector_store.py
# Shared embedding model + Chroma vector store.
# Imported by both the indexer (index_problems.py) and the RAG retriever.
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# The embedding model — converts text to vectors.
# Uses Gemini to stay on the same provider/key as the rest of the stack (src/llm.py).
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

# ChromaDB — stores vectors locally on disk
vectorstore = Chroma(
    collection_name="leetcode_problems",
    embedding_function=embeddings,
    persist_directory="./data/chroma",  # persists between sessions
)
