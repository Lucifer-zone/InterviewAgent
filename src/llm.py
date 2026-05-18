import logging
import os
import sys
import time

from dotenv import load_dotenv
from langchain_core.caches import InMemoryCache
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.globals import set_llm_cache

load_dotenv()

# Cache identical LLM prompts so LangGraph's "replay from top of node after interrupt"
# doesn't redo work. Persists for the lifetime of the process.
set_llm_cache(InMemoryCache())

# ─── Logger ─────────────────────────────────────────────────────────────────
logger = logging.getLogger("interview_agent")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class LLMTimingCallback(BaseCallbackHandler):
    """Logs each LLM call with a prompt preview and elapsed time."""

    def _start(self, preview: str):
        self._t0 = time.time()
        logger.info(f"LLM ⇢ {preview[:100]}…")

    def on_llm_start(self, serialized, prompts, **kwargs):
        text = prompts[0] if prompts else ""
        self._start(text.replace("\n", " "))

    def on_chat_model_start(self, serialized, messages, **kwargs):
        # messages is list[list[BaseMessage]] — grab the final user message
        text = ""
        if messages and messages[0]:
            content = messages[0][-1].content
            text = content if isinstance(content, str) else str(content)
        self._start(text.replace("\n", " "))

    def on_llm_end(self, response, **kwargs):
        elapsed = time.time() - getattr(self, "_t0", time.time())
        logger.info(f"LLM ✓ {elapsed:.1f}s")

    def on_llm_error(self, error, **kwargs):
        elapsed = time.time() - getattr(self, "_t0", time.time())
        logger.error(f"LLM ✗ {elapsed:.1f}s — {error}")


# ─── Provider switch ────────────────────────────────────────────────────────
# Flip via env: LLM_PROVIDER=ollama  OR  LLM_PROVIDER=gemini
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")


_callbacks = [LLMTimingCallback()]

if LLM_PROVIDER == "ollama":
    from langchain_ollama import ChatOllama

    llm = ChatOllama(
        model=OLLAMA_MODEL,
        temperature=0.3,
        keep_alive="24h",
        callbacks=_callbacks,
    )
elif LLM_PROVIDER == "gemini":
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        api_key=os.environ.get("GEMINI_API_KEY"),
        callbacks=_callbacks,
    )
else:
    raise ValueError(f"Unknown LLM_PROVIDER={LLM_PROVIDER!r} (expected 'ollama' or 'gemini')")

logger.info(f"LLM provider: {LLM_PROVIDER} | model: {getattr(llm, 'model', '?')}")


def to_text(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(b["text"] for b in content if b.get("type") == "text")
