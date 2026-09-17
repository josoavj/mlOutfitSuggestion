"""Modèles Pydantic pour les items de garde-robe individuelle.

Reprend le schéma défini dans wardrobe-composition-spec.md (section 1 et 2).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Category(str, Enum):
    top = "top"
    bottom = "bottom"
    outerwear = "outerwear"
    dress = "dress"
    shoes = "shoes"
    accessory = "accessory"


class Color(str, Enum):
    noir = "noir"
    blanc = "blanc"
    gris = "gris"
    bleu_marine = "bleu_marine"
    bleu_clair = "bleu_clair"
    beige = "beige"
    marron = "marron"
    vert = "vert"
    rouge = "rouge"
    rose = "rose"
    jaune = "jaune"
    orange = "orange"
    violet = "violet"
    multicolore = "multicolore"


class Material(str, Enum):
    # Naturels
    coton = "coton"
    laine = "laine"
    lin = "lin"
    soie = "soie"
    cachemire = "cachemire"
    chanvre = "chanvre"
    cuir = "cuir"
    daim = "daim"
    fourrure = "fourrure"
    
    # Synthétiques & Artificiels
    denim = "denim"
    synthetique = "synthetique"
    polyester = "polyester"
    nylon = "nylon"
    viscose = "viscose"
    lycra = "elashanne"
    acrylic = "acrylique"
    
    # Textures & Tissages
    maille = "maille"
    velours = "velours"
    satin = "satin"
    tulle = "tulle"
    dentelle = "dentelle"
    flanelle = "flanelle"
    tweed = "tweed"
    jersey = "jersey"
    polaire = "polaire"
    canvas = "toile"


class Pattern(str, Enum):
    uni = "uni"
    raye = "raye"
    imprime = "imprime"
    carreaux = "carreaux"
    a_pois = "a_pois"


class Season(str, Enum):
    printemps = "printemps"
    ete = "ete"
    automne = "automne"
    hiver = "hiver"


class WardrobeItemCreate(BaseModel):
    """Payload attendu par POST /wardrobe/items.

    Seuls category, subcategory, color_primary, formality_level et
    warmth_rating sont obligatoires — le reste est optionnel pour garder
    la saisie manuelle rapide (voir spec, section 3).
    """

    category: Category
    subcategory: str = Field(..., min_length=1, max_length=50)
    color_primary: Color
    formality_level: int = Field(..., ge=1, le=5)
    warmth_rating: int = Field(..., ge=1, le=5)

    color_secondary: Optional[Color] = None
    material: Optional[str] = "coton"  # Changé en str pour permettre le manuel
    pattern: Optional[Pattern] = None
    season_suitability: list[Season] = Field(default_factory=list)
    occasion_tags: list[str] = Field(default_factory=list)

    # Image optionnelle — soit une image déjà hébergée, soit un upload
    # base64 que le store se charge de persister et de convertir en URL.
    image_url: Optional[str] = None
    image_base64: Optional[str] = None


class WardrobeItemUpdate(BaseModel):
    """Payload pour PATCH /wardrobe/items/{id} — tous les champs optionnels."""

    subcategory: Optional[str] = None
    color_primary: Optional[Color] = None
    color_secondary: Optional[Color] = None
    material: Optional[str] = None
    pattern: Optional[Pattern] = None
    formality_level: Optional[int] = Field(None, ge=1, le=5)
    warmth_rating: Optional[int] = Field(None, ge=1, le=5)
    season_suitability: Optional[list[Season]] = None
    occasion_tags: Optional[list[str]] = None
    image_url: Optional[str] = None
    is_favorite: Optional[bool] = None


class WardrobeItem(BaseModel):
    """Représentation complète d'un item, telle que stockée et renvoyée."""

    item_id: str = Field(default_factory=lambda: f"itm_{uuid4().hex[:8]}")
    user_id: str

    category: Category
    subcategory: str
    color_primary: Color
    color_secondary: Optional[Color] = None
    material: Optional[str] = "coton"
    pattern: Optional[Pattern] = Pattern.uni
    formality_level: int
    warmth_rating: int
    season_suitability: list[Season] = Field(default_factory=lambda: [Season.printemps, Season.ete, Season.automne, Season.hiver])
    occasion_tags: list[str] = Field(default_factory=list)

    image_url: Optional[str] = None
    auto_tagged: bool = False
    is_favorite: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_suggested_at: Optional[datetime] = None
    last_worn_at: Optional[datetime] = None

    @classmethod
    def from_create(cls, user_id: str, payload: WardrobeItemCreate, image_url: Optional[str]) -> "WardrobeItem":
        return cls(
            user_id=user_id,
            category=payload.category,
            subcategory=payload.subcategory,
            color_primary=payload.color_primary,
            color_secondary=payload.color_secondary,
            material=payload.material,
            pattern=payload.pattern,
            formality_level=payload.formality_level,
            warmth_rating=payload.warmth_rating,
            season_suitability=payload.season_suitability,
            occasion_tags=payload.occasion_tags,
            image_url=image_url,
            auto_tagged=False,
        )
