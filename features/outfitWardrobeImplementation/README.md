# Intégration dans mlOutfitSuggestion

## Fichiers à copier

```
src/outfit_ml/wardrobe/__init__.py
src/outfit_ml/wardrobe/models.py
src/outfit_ml/wardrobe/store.py
src/outfit_ml/wardrobe/router.py
src/outfit_ml/composition/__init__.py
src/outfit_ml/composition/models.py
src/outfit_ml/composition/filters.py
src/outfit_ml/composition/compatibility.py
src/outfit_ml/composition/generator.py
src/outfit_ml/composition/scoring.py
src/outfit_ml/composition/diversity.py
src/outfit_ml/composition/engine.py
```

À placer directement sous `src/outfit_ml/` dans le repo (respecte l'arborescence existante).

## Branchement dans `src/outfit_ml/api.py`

```python
from .wardrobe.router import router as wardrobe_router

app.include_router(wardrobe_router)
```

## Ce qui N'EST PAS fait (volontairement, à faire ensuite)

1. **Réentraînement du ranker** — `scoring.py` utilise une heuristique de repli
   explicite (`heuristic_score`), pas `outfit_ranker.joblib`. Le ranker actuel
   a été entraîné sur des tenues prédéfinies, pas sur des combinaisons générées
   dynamiquement — il faut le réentraîner sur des features de combinaison avant
   de le brancher ici (interface déjà prête : `score_fn` dans `engine.py`).
2. **Branchement dans `/recommend*`** — les endpoints existants doivent être
   adaptés pour appeler `compose_outfits()` avec la garde-robe de l'utilisateur
   au lieu de scorer la liste fixe actuelle. Pas fait ici pour éviter de
   modifier `api.py` sans voir son contenu exact.
3. **Corpus RAG (`data/corpus_style/`)** — les règles de compatibilité
   (`compatibility.py`) sont codées en dur pour l'instant. À terme, remplacer
   `_colors_compatible` / `COMPLEMENTARY_PAIRS` par une interrogation du
   corpus, comme prévu dans la spec (section 5).
4. **Migration des tenues existantes** — script de décomposition liste fixe
   → items individuels non inclus (dépend du format exact des données
   actuelles dans `data/`).

## Test rapide (déjà validé)

```bash
pip install fastapi pydantic
python3 -c "
from src.outfit_ml.wardrobe.store import WardrobeStore
from src.outfit_ml.composition.engine import compose_outfits
# ... voir exemple dans la conversation
"
```
