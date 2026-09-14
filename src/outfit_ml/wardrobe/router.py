"""Endpoints /wardrobe/items — à monter sur l'app FastAPI existante.

Dans src/outfit_ml/api.py :

    from .wardrobe.router import router as wardrobe_router
    app.include_router(wardrobe_router)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .models import WardrobeItem, WardrobeItemCreate, WardrobeItemUpdate
from .store import WardrobeItemNotFound, wardrobe_store

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


@router.post("/items", response_model=WardrobeItem, status_code=201)
def create_item(user_id: str, payload: WardrobeItemCreate) -> WardrobeItem:
    return wardrobe_store.create_item(user_id, payload)


@router.get("/items", response_model=list[WardrobeItem])
def list_items(user_id: str, category: Optional[str] = Query(default=None)) -> list[WardrobeItem]:
    return wardrobe_store.list_items(user_id, category)


@router.patch("/items/{item_id}", response_model=WardrobeItem)
def update_item(item_id: str, user_id: str, payload: WardrobeItemUpdate) -> WardrobeItem:
    try:
        return wardrobe_store.update_item(user_id, item_id, payload)
    except WardrobeItemNotFound:
        raise HTTPException(status_code=404, detail=f"Item {item_id} introuvable pour cet utilisateur")


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str, user_id: str) -> None:
    try:
        wardrobe_store.delete_item(user_id, item_id)
    except WardrobeItemNotFound:
        raise HTTPException(status_code=404, detail=f"Item {item_id} introuvable pour cet utilisateur")
