"""
RAG Engine - Retrieval Augmented Generation

Refinements added:
  R4 — Structured citations: every response includes filename, section, chunk index
  R5 — Multi-resource fusion: retrieves from ALL indexed resources, ranks by
       similarity, merges into a single grounded context before generating
"""

from typing import List, Dict, Any, Optional
import re
import numpy as np


class SimpleVectorDB:
    """In-memory vector store with cosine-similarity search."""

    def __init__(self):
        self.vectors:  List[np.ndarray]    = []
        self.metadata: List[Dict[str, Any]] = []

    def add(self, vector: List[float], metadata: Dict[str, Any]):
        self.vectors.append(np.array(vector))
        self.metadata.append(metadata)

    def search(self, query_vector: List[float],
               top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.vectors:
            return []
        qv   = np.array(query_vector)
        qn   = np.linalg.norm(qv)
        if qn == 0:
            return []
        sims = []
        for vec in self.vectors:
            vn = np.linalg.norm(vec)
            sims.append(float(np.dot(qv, vec) / (qn * vn)) if vn else 0.0)
        top = np.argsort(sims)[-top_k:][::-1]
        return [{"similarity": sims[i], "metadata": self.metadata[i]}
                for i in top]


class RAGEngine:
    """Retrieval-Augmented Generation with multi-resource fusion and citations."""

    # ── Embedding constants ───────────────────────────────────────────────────
    _DIM  = 256
    _STOP = {
        "the", "a", "an", "is", "it", "in", "on", "at", "to", "of",
        "and", "or", "but", "for", "with", "this", "that", "are",
        "was", "be", "by", "as", "so", "we", "he", "she", "they",
    }

    def __init__(self, llm, user_id: str, state: dict):
        self.llm       = llm
        self.user_id   = user_id
        self.state     = state
        self.vector_db = SimpleVectorDB()
        self._ensure_rag_structure()
        self._load_existing_vectors()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _ensure_rag_structure(self):
        self.state.setdefault("rag_storage", {})
        self.state["rag_storage"].setdefault(self.user_id, {
            "embeddings": [], "indexed_chunks": 0, "last_indexed": None
        })

    def _load_existing_vectors(self):
        for entry in self.state["rag_storage"][self.user_id]["embeddings"]:
            vec = entry["vector"]
            if len(vec) != self._DIM:
                vec = self.generate_embedding(entry["metadata"].get("text", ""))
                entry["vector"] = vec
            self.vector_db.add(vec, entry["metadata"])

    # ── Embedding ─────────────────────────────────────────────────────────────

    def generate_embedding(self, text: str) -> List[float]:
        """
        TF-weighted bag-of-words embedding (256 dims).
        Symmetric: query and document embeddings are built identically,
        so cosine similarity is reliable.
        """
        vector = [0.0] * self._DIM
        words  = re.sub(r"[^a-z0-9\s]", "", text.lower()).split()
        if not words:
            return vector
        tf: Dict[str, float] = {}
        for w in words:
            if w not in self._STOP and len(w) > 1:
                tf[w] = tf.get(w, 0.0) + 1.0
        for w, freq in tf.items():
            h = hash(w)
            for k in range(3):
                vector[(h + k * 97) % self._DIM] += freq
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_chunks(self, resource_id: str, chunks: List[Dict[str, Any]],
                     resource_metadata: Dict[str, Any]) -> int:
        """Embed all chunks and store in vector DB + state."""
        count = 0
        for i, chunk in enumerate(chunks):
            embedding = self.generate_embedding(chunk["text"])
            metadata  = {
                "resource_id":       resource_id,
                "chunk_index":       i,
                "text":              chunk["text"],
                "tokens":            chunk.get("tokens", 0),
                "chunk_type":        chunk.get("type", "paragraph"),
                "resource_filename": resource_metadata.get("filename", ""),
                "resource_subject":  resource_metadata.get("subject", ""),
                "topics":            resource_metadata.get("topics_covered", []),
                # R4: section label inferred from chunk type
                "section":           chunk.get("section_title", f"Section {i+1}"),
            }
            self.vector_db.add(embedding, metadata)
            self.state["rag_storage"][self.user_id]["embeddings"].append(
                {"vector": embedding, "metadata": metadata}
            )
            count += 1
        self.state["rag_storage"][self.user_id]["indexed_chunks"] += count
        return count

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 5,
                 filter_subject: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        R5 — Multi-resource retrieval.
        Searches ALL indexed resources (no hard exclusion by subject).
        Subject filter is a soft preference: prefer matching subject chunks
        but always fall back to best available.
        Threshold 0.25 separates genuine topic matches from noise.
        """
        qe = self.generate_embedding(query)
        # Fetch a wide pool for R5 fusion
        all_results = self.vector_db.search(qe, top_k=max(top_k * 4, 20))

        if not all_results:
            return []

        # Soft subject preference
        if filter_subject:
            nf = self._normalize_subject(filter_subject)
            preferred = [r for r in all_results
                         if self._normalize_subject(
                             r["metadata"]["resource_subject"]) == nf]
            # Keep all results for fusion; preferred chunks get a slight boost
            for r in preferred:
                r["similarity"] = min(1.0, r["similarity"] * 1.1)
            # Re-sort after boost
            all_results.sort(key=lambda x: x["similarity"], reverse=True)

        # Apply similarity threshold
        # 0.05 is deliberately permissive: short documents and hash-based
        # embeddings produce lower raw similarity scores than neural embeddings.
        # A subject-filtered pool is already narrow; we don't need a high bar.
        THRESHOLD = 0.05
        above = [r for r in all_results if r["similarity"] >= THRESHOLD]
        return (above or all_results[:top_k])[:top_k]

    # ── Grounded explanation ──────────────────────────────────────────────────

    def generate_grounded_explanation(self, topic: str, query: str,
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """
        R5 — Retrieve from ALL resources, merge into one context.
        R4 — Return structured citations per chunk used.
        """
        retrieved = self.retrieve(
            query=f"{topic} {query}",
            top_k=5,
            filter_subject=context.get("subject")
        )

        if not retrieved:
            return {
                "explanation": self._generate_from_llm(topic, query, context),
                "sources":     [],
                "citations":   [],
                "grounded":    False,
                "message":     "No uploaded resources found. Using AI knowledge."
            }

        context_str = self._build_context_string(retrieved)
        sources     = self._extract_sources(retrieved)
        citations   = self._extract_citations(retrieved)   # R4
        layer       = context.get("layer", 1)
        prompt      = self._build_grounded_prompt(topic, query, context_str, layer)
        explanation = self.llm.invoke(prompt).content

        return {
            "explanation": explanation,
            "sources":     sources,
            "citations":   citations,   # R4: structured [{filename, section, chunk}]
            "grounded":    True,
            "chunks_used": len(retrieved),
            "message":     f"Based on {len(sources)} uploaded resource(s)"
        }

    # ── Citation helpers ──────────────────────────────────────────────────────

    def _build_context_string(self, retrieved: List[Dict[str, Any]]) -> str:
        """R5: merge chunks from multiple resources into one context block."""
        parts = []
        for i, r in enumerate(retrieved, 1):
            m = r["metadata"]
            # R4: include filename + section in context so LLM can cite them
            parts.append(
                f"[Source {i} | {m['resource_filename']} | {m['section']}]\n"
                f"{m['text']}"
            )
        return "\n\n".join(parts)

    def _extract_sources(self, retrieved: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Unique source list (one entry per resource file)."""
        seen: Dict[str, Dict[str, Any]] = {}
        for r in retrieved:
            m   = r["metadata"]
            rid = m["resource_id"]
            if rid not in seen:
                seen[rid] = {
                    "resource_id": rid,
                    "filename":    m["resource_filename"],
                    "subject":     m["resource_subject"],
                    "chunks_used": 0
                }
            seen[rid]["chunks_used"] += 1
        return list(seen.values())

    def _extract_citations(self, retrieved: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        R4: Structured citation list — one entry per chunk used.
        Each entry carries filename, section label, and chunk index so the UI
        can render:  "cpu_notes.txt › Section 2 › chunk 1"
        """
        citations = []
        for r in retrieved:
            m = r["metadata"]
            citations.append({
                "filename":    m["resource_filename"],
                "section":     m.get("section", f"Section {m['chunk_index']+1}"),
                "chunk_index": m["chunk_index"],
                "similarity":  round(r["similarity"], 3),
                "preview":     m["text"][:120] + ("…" if len(m["text"]) > 120 else "")
            })
        return citations

    def _build_grounded_prompt(self, topic: str, query: str,
                                context_str: str, layer: int) -> str:
        """Layer-appropriate grounded prompt with citation instruction."""
        instruction = (
            "After the explanation, add a '### Sources' section listing which "
            "source(s) you used (use the [Source N | filename | section] labels "
            "from the context)."
        )
        if layer == 1:
            return (
                f"Using ONLY the following context from the student's uploaded resources:\n\n"
                f"{context_str}\n\n"
                f"Explain {topic} intuitively with a real-life analogy. "
                f"Simple language, no jargon.\n\n"
                f"{instruction}\n\nQuestion: {query}"
            )
        elif layer == 2:
            return (
                f"Using ONLY the following context from the student's uploaded resources:\n\n"
                f"{context_str}\n\n"
                f"Explain {topic} in a structured way:\n"
                f"1. Definition\n2. Key components\n3. How it works\n4. Formula (if applicable)\n\n"
                f"{instruction}\n\nQuestion: {query}"
            )
        elif layer == 3:
            return (
                f"Using ONLY the following context from the student's uploaded resources:\n\n"
                f"{context_str}\n\n"
                f"Provide advanced understanding of {topic}:\n"
                f"1. Edge cases and limitations\n2. Comparison with alternatives\n"
                f"3. Real-world applications\n4. Problem-solving approach\n\n"
                f"{instruction}\n\nQuestion: {query}"
            )
        return (
            f"Using ONLY the following context:\n\n{context_str}\n\n"
            f"Answer: {query} about {topic}\n\n{instruction}"
        )

    # ── Fallback (no resources uploaded) ─────────────────────────────────────

    def _generate_from_llm(self, topic: str, query: str,
                            context: Dict[str, Any]) -> str:
        layer = context.get("layer", 1)
        if layer == 1:
            p = f"Explain {topic} intuitively with simple analogies. Question: {query}"
        elif layer == 2:
            p = f"Explain {topic} in a structured way with definitions and components. Question: {query}"
        elif layer == 3:
            p = f"Advanced understanding of {topic} with edge cases and applications. Question: {query}"
        else:
            p = f"Answer: {query} about {topic}"
        return self.llm.invoke(p).content

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _normalize_subject(self, subject: str) -> str:
        mapping = {
            "os": "operating systems",
            "operating system": "operating systems",
            "db": "databases", "database": "databases", "dbms": "databases",
            "ds": "data structures", "data structure": "data structures",
            "algo": "algorithms",   "algorithm": "algorithms",
            "cn": "computer networks", "networks": "computer networks",
            "ml": "machine learning",
        }
        n = subject.lower().strip()
        return mapping.get(n, n)

    def get_rag_stats(self) -> Dict[str, Any]:
        d = self.state["rag_storage"][self.user_id]
        return {
            "indexed_chunks":   d["indexed_chunks"],
            "total_embeddings": len(d["embeddings"]),
            "vector_db_size":   len(self.vector_db.vectors),
            "last_indexed":     d.get("last_indexed"),
            "resources_count":  len({e["metadata"]["resource_id"]
                                     for e in d["embeddings"]})
        }

    def clear_index(self):
        self.vector_db = SimpleVectorDB()
        self.state["rag_storage"][self.user_id] = {
            "embeddings": [], "indexed_chunks": 0, "last_indexed": None
        }
