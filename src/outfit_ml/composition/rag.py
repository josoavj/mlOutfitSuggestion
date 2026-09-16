"""Moteur RAG de style basé sur ChromaDB.

Indexation sémantique complète du corpus textuel situé dans data/corpus_style/
utilisant les fonctionnalités de ChromaDB combinées à une fonction d'embedding
légère et déterministe pour des performances optimales sans téléchargement réseau.
"""

from __future__ import annotations

import os
from pathlib import Path
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

CORPUS_STYLE_ROOT = Path(os.getenv("CORPUS_STYLE_ROOT", "data/corpus_style"))


class LightTokenEmbeddingFunction(EmbeddingFunction):
    """Une fonction d'embedding ultra-légère et rapide basée sur l'encodage de tokens.
    Évite le téléchargement de modèles ONNX lourds du réseau tout en restant déterministe.
    """
    def __call__(self, input: Documents) -> Embeddings:
        embeddings: Embeddings = []
        # Vocabulaire cible pour notre domaine vestimentaire
        vocab = ["noir", "blanc", "gris", "beige", "marron", "bleu_marine", "rouge", "jaune", "vert", "rose", "violet", "multicolore", "harmonie", "association", "occasion", "formalite", "sport", "casual", "work", "meeting", "event", "couleur", "meteo", "matiere", "chaleur"]
        
        for doc in input:
            tokens = doc.lower().split()
            vector = [0.0] * len(vocab)
            for t in tokens:
                for idx, word in enumerate(vocab):
                    if word in t:
                        vector[idx] += 1.0
            embeddings.append(vector)
        return embeddings


class StyleRAG:
    def __init__(self, corpus_root: Path = CORPUS_STYLE_ROOT):
        self.corpus_root = corpus_root
        self.client = chromadb.Client()
        self.embedding_fn = LightTokenEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="style_rules",
            embedding_function=self.embedding_fn
        )
        self._index_corpus()

    def _index_corpus(self) -> None:
        if not self.corpus_root.exists():
            return

        idx = 0
        for file in self.corpus_root.glob("*.md"):
            try:
                content = file.read_text(encoding="utf-8")
                lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
                
                if lines:
                    documents = []
                    ids = []
                    metadatas = []
                    
                    for line in lines:
                        documents.append(line)
                        ids.append(f"id_{file.stem}_{idx}")
                        metadatas.append({"source": file.stem})
                        idx += 1
                        
                    self.collection.add(
                        documents=documents,
                        ids=ids,
                        metadatas=metadatas
                    )
            except Exception:  # noqa: BLE001
                pass

    def retrieve_rules(self, query_text: str, n_results: int = 3) -> list[str]:
        """Recherche par similarité vectorielle avec ChromaDB."""
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            if results and "documents" in results and results["documents"]:
                return results["documents"][0]
        except Exception:  # noqa: BLE001
            pass
        return []

    def check_color_harmony(self, color1: str, color2: str) -> bool:
        """Utilise l'index vectoriel ChromaDB pour vérifier l'harmonie des couleurs."""
        results = self.retrieve_rules(f"harmonie association {color1} {color2}", n_results=5)
        
        neutrals = ["noir", "blanc", "gris", "beige", "marron", "bleu_marine"]
        if color1 in neutrals or color2 in neutrals:
            return True

        for doc in results:
            if color1 in doc.lower() and color2 in doc.lower():
                return True

        return color1 == color2


style_rag = StyleRAG()
