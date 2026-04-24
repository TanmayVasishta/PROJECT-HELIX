"""
HELIX — Memory Module
ChromaDB persistent vector store.
Uses chromadb directly (no langchain_chroma) to avoid
Pydantic V1 issues on Python 3.14.
"""
import hashlib, time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import chromadb
from config.settings import CHROMA_DB_PATH


class HelixMemory:
    def __init__(self):
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection(
            name="helix_memory"
            # Default embedding: chromadb's built-in (no external dep needed)
        )
        print(f"[Memory] ChromaDB ready. Stored interactions: {self.collection.count()}")

    def store(self, prompt: str, response: str, metadata: dict = None):
        doc_id = hashlib.md5(f"{prompt}{time.time()}".encode()).hexdigest()
        meta = {"timestamp": str(time.time())}
        if metadata:
            meta.update(metadata)
        self.collection.add(
            documents=[f"User: {prompt}\nHELIX: {response}"],
            ids=[doc_id],
            metadatas=[meta]
        )

    def retrieve(self, query: str, n: int = 3) -> str:
        """Fetch relevant past interactions as context string."""
        try:
            count = self.collection.count()
            if count == 0:
                return ""
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n, count)
            )
            docs = results.get("documents", [[]])[0]
            return "\n---\n".join(docs) if docs else ""
        except Exception as e:
            print(f"[Memory] Retrieval warning: {e}")
            return ""

    def clear(self):
        self.client.delete_collection("helix_memory")
        self.collection = self.client.get_or_create_collection(name="helix_memory")
        print("[Memory] Cleared.")
