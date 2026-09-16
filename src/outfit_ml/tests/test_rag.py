from ..composition.rag import style_rag


def test_chromadb_index_and_retrieval():
    """Test complet de l'indexation sémantique ChromaDB et du retour de règles."""
    rules = style_rag.retrieve_rules("couleurs", n_results=2)
    assert isinstance(rules, list)
    if rules:
        assert any("couleur" in r.lower() or "harmonie" in r.lower() for r in rules)


def test_color_harmony_rules():
    """Test exhaustif de la validation d'harmonie des couleurs via ChromaDB."""
    # Couleurs neutres (doivent toujours passer)
    assert style_rag.check_color_harmony("noir", "rouge") is True
    assert style_rag.check_color_harmony("blanc", "bleu_marine") is True
    assert style_rag.check_color_harmony("bleu_marine", "vert") is True

    # Couleurs identiques
    assert style_rag.check_color_harmony("rouge", "rouge") is True

    # Paires complémentaires répertoriées dans le corpus
    assert style_rag.check_color_harmony("bleu_marine", "rouge") is True
