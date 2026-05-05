import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-flash-lite-latest",
    api_key=os.environ.get("GEMINI_API_KEY"),
)
