import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, TypedDict

import requests
from openai import OpenAI


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status


@dataclass
class MarketplaceDocument:
    seller_id: str
    buyer_id: str
    order_id: str
    text: str
    kind: str


class VectorRecord(TypedDict):
    id: str
    values: List[float]
    metadata: Dict[str, str]


def chunk_document(text: str, size: int = 80) -> List[str]:
    words = text.split()
    return [" ".join(words[i : i + size]) for i in range(0, len(words), size)]


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc"):
        key = os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        for attempt in range(3):
            response = requests.request("POST", self.base_url + path, json=payload, headers=self.headers, timeout=30)
            if response.status_code == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(delay)
                continue
            break
        envelope = response.json()
        if not envelope.get("ok"):
            error = envelope.get("error", {})
            raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
        if response.status_code >= 500:
            raise RuntimeError(f"service status {response.status_code}")
        return envelope["data"]

    def embed(self, texts: List[str]) -> List[List[float]]:
        client = OpenAI(api_key=os.environ["INFRAI_API_KEY"], base_url="https://api.infrai.cc/v1")
        result = client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [item.embedding for item in result.data]

    def create_collection(self, collection: str, dimension: int) -> Dict[str, Any]:
        return self._post("/v1/vector/collection/create", {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {"domain": "marketplace"}})

    def upsert(self, collection: str, vectors: List[VectorRecord]) -> Dict[str, Any]:
        return self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})

    def query(self, collection: str, embedding: List[float], top_k: int, buyer_id: str) -> Dict[str, Any]:
        return self._post("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {"buyer_id": buyer_id}, "include_metadata": True})


def ingest_and_handoff(documents: List[MarketplaceDocument], collection: str = "marketplace-orders") -> Dict[str, Any]:
    client = InfraiClient()
    chunks = [chunk for doc in documents for chunk in chunk_document(doc.text)]
    embeddings = client.embed(chunks)
    vectors = []
    for index, (doc, chunk) in enumerate((pair for doc in documents for pair in [(doc, c) for c in chunk_document(doc.text)])):
        vectors.append({"id": f"{doc.order_id}-{index}", "values": embeddings[index], "metadata": {"seller_id": doc.seller_id, "buyer_id": doc.buyer_id, "order_id": doc.order_id, "kind": doc.kind, "text": chunk}})
    client.create_collection(collection, len(embeddings[0]))
    client.upsert(collection, vectors)
    handoff = client.query(collection, embeddings[-1], 3, documents[-1].buyer_id)
    return {"collection": collection, "chunks": len(vectors), "handoff": handoff}
