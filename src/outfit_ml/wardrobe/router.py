from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from ..api import require_api_key, limiter

from .models import WardrobeItem, WardrobeItemCreate, WardrobeItemUpdate
from .store import WardrobeItemNotFound, wardrobe_store

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


@router.post("/items", response_model=WardrobeItem, status_code=201)
@limiter.limit(os.getenv("RATE_LIMIT_WARDROBE", "30/minute"))
def create_item(
    request: Request,
    user_id: str, 
    payload: WardrobeItemCreate,
    _: None = Depends(require_api_key)
) -> WardrobeItem:
    return wardrobe_store.create_item(user_id, payload)


@router.get("/items", response_model=list[WardrobeItem])
@limiter.limit(os.getenv("RATE_LIMIT_WARDROBE", "30/minute"))
def list_items(
    request: Request,
    user_id: str, 
    category: Optional[str] = Query(default=None),
    _: None = Depends(require_api_key)
) -> list[WardrobeItem]:
    return wardrobe_store.list_items(user_id, category)


@router.patch("/items/{item_id}", response_model=WardrobeItem)
@limiter.limit(os.getenv("RATE_LIMIT_WARDROBE", "30/minute"))
def update_item(
    request: Request,
    item_id: str, 
    user_id: str, 
    payload: WardrobeItemUpdate,
    _: None = Depends(require_api_key)
) -> WardrobeItem:
    try:
        return wardrobe_store.update_item(user_id, item_id, payload)
    except WardrobeItemNotFound:
        raise HTTPException(status_code=404, detail=f"Item {item_id} introuvable pour cet utilisateur")


@router.delete("/items/{item_id}", status_code=204)
@limiter.limit(os.getenv("RATE_LIMIT_WARDROBE", "30/minute"))
def delete_item(
    request: Request,
    item_id: str, 
    user_id: str,
    _: None = Depends(require_api_key)
) -> None:
    try:
        wardrobe_store.delete_item(user_id, item_id)
    except WardrobeItemNotFound:
        raise HTTPException(status_code=404, detail=f"Item {item_id} introuvable pour cet utilisateur")
