"""Choose a real embedding provider (API or local) and implement this contract."""
import json
import os
import re
import time
from typing import Protocol
import urllib.error
import urllib.request
from dotenv import load_dotenv


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Gemini API embedding adapter with automatic active model resolution (768 dimensions)."""

    def __init__(self, model_name: str = "gemini-embedding-001", api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing in starter/.env")

        # Standard dimension for pgvector schema
        self.dimensions = 768
        self.model_name = self._resolve_model(model_name)

    def _resolve_model(self, preferred_model: str) -> str:
        """Verify preferred model or automatically pick an active embedding model."""
        clean_pref = preferred_model.split("/")[-1]
        # Query list of models from Gemini API to see which embedding model is currently active
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                models = data.get("models", [])
                embed_models = [
                    m["name"].split("/")[-1]
                    for m in models
                    if "embedContent" in m.get("supportedGenerationMethods", [])
                    or "batchEmbedContents" in m.get("supportedGenerationMethods", [])
                ]
                if clean_pref in embed_models:
                    return clean_pref
                if "gemini-embedding-001" in embed_models:
                    return "gemini-embedding-001"
                if "text-embedding-005" in embed_models:
                    return "text-embedding-005"
                if embed_models:
                    return embed_models[0]
        except Exception:
            pass

        # Fallback to preferred or gemini-embedding-001
        return "gemini-embedding-001" if clean_pref == "text-embedding-004" else clean_pref

    def _embed_batch(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        if not texts:
            return []

        normalized_model = (
            self.model_name if self.model_name.startswith("models/") else f"models/{self.model_name}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/{normalized_model}:batchEmbedContents?key={self.api_key}"

        requests_payload = []
        for t in texts:
            req_item = {
                "model": normalized_model,
                "content": {"parts": [{"text": t}]},
                "taskType": task_type,
                "outputDimensionality": self.dimensions,
            }
            requests_payload.append(req_item)

        body = json.dumps({"requests": requests_payload}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        max_retries = 5
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    embeddings = res_json.get("embeddings", [])
                    vectors = [e["values"] for e in embeddings]
                    if len(vectors) != len(texts):
                        raise ValueError(f"Expected {len(texts)} embeddings, got {len(vectors)}")
                    return vectors
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                # If batchEmbedContents fails or returns 404, fallback to single calls with embedContent
                if e.code == 404:
                    return self._embed_single_fallback(texts, task_type)
                if e.code == 429 and attempt < max_retries - 1:
                    wait_sec = 45
                    try:
                        err_data = json.loads(err_body)
                        for detail in err_data.get("error", {}).get("details", []):
                            if "retryDelay" in detail:
                                wait_sec = int(float(detail["retryDelay"].rstrip("s"))) + 2
                                break
                        else:
                            m = re.search(r"retry in ([0-9\.]+)s", err_body)
                            if m:
                                wait_sec = int(float(m.group(1))) + 2
                    except Exception:
                        pass
                    print(f"\n   ⏳ [Rate Limit 429] Chạm trần Free Tier (100 req/phút). Tự động nghỉ {wait_sec}s rồi tiếp tục...", flush=True)
                    time.sleep(wait_sec)
                    continue
                raise RuntimeError(f"Gemini API HTTP {e.code} error: {err_body}") from e
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                raise RuntimeError(f"Gemini API request failed: {e}") from e

        raise RuntimeError("Failed to obtain embeddings from Gemini API")

    def _embed_single_fallback(self, texts: list[str], task_type: str) -> list[list[float]]:
        """Fallback to individual embedContent calls if batchEmbedContents is unsupported."""
        normalized_model = (
            self.model_name if self.model_name.startswith("models/") else f"models/{self.model_name}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/{normalized_model}:embedContent?key={self.api_key}"

        results: list[list[float]] = []
        for t in texts:
            payload = {
                "model": normalized_model,
                "content": {"parts": [{"text": t}]},
                "taskType": task_type,
                "outputDimensionality": self.dimensions,
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                vec = res_json.get("embedding", {}).get("values", [])
                results.append(vec)
            time.sleep(0.1)
        return results

    def embed_documents(self, texts: list[str], batch_size: int = 50) -> list[list[float]]:
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            vectors = self._embed_batch(batch, task_type="RETRIEVAL_DOCUMENT")
            all_vectors.extend(vectors)
            if i + batch_size < len(texts):
                time.sleep(0.5)
        return all_vectors

    def embed_query(self, question: str) -> list[float]:
        vectors = self._embed_batch([question], task_type="RETRIEVAL_QUERY")
        return vectors[0]
