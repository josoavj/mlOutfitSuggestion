"""Moteur RAG de style très léger.

Interroge le corpus textuel situé dans data/corpus_style/ pour en extraire
les règles dynamiquement.
"""

from __future__ import annotations

import os
from pathlib import Path

CORPUS_STYLE_ROOT = Path(os.getenv("CORPUS_STYLE_ROOT", "data/corpus_style"))


class StyleRAG:
    def __init__(self, corpus_root: Path = CORPUS_STYLE_ROOT):
        self.corpus_root = corpus_root
        self._cache: dict[str, str] = {}
        self._load_corpus()

    def _load_corpus(self) -> None:
        if not self.corpus_root.exists():
            return
        for file in self.corpus_root.glob("*.md"):
            try:
                content = file.read_text(encoding="utf-8")
                self._cache[file.stem] = content
            except Exception:  # noqa: BLE001
                pass

    def retrieve_rules(self, keyword: str) -> list[str]:
        """Recherche par mot-clé simple toutes les lignes ou sections contenant le mot-clé."""
        matches: list[str] = []
        keyword_lower = keyword.lower()
        for doc_name, content in self._cache.items():
            for line in content.splitlines():
                if keyword_lower in line.lower():
                    matches.append(line.strip())
        return matches

    def check_color_harmony(self, color1: str, color2: str) -> bool:
        """Vérifie dans le document d'harmonie des couleurs si l'association est valide."""
        content = self._cache.get("harmonie_couleurs", "")
        if not content:
            return True  # Fallback permissif si le corpus est absent

        # Si l'une des couleurs fait partie des neutres universels
        if "neutres" in content.lower():
            neutrals = ["noir", "blanc", "gris", "beige", "marron", "bleu_marine"]
            if color1 in neutrals or color2 in neutrals:
                return True

        # Recherche de la ligne de paire complémentaire
        for line in content.splitlines():
            if color1 in line and color2 in line:
                return True

        return color1 == color2


style_rag = StyleRAG()
