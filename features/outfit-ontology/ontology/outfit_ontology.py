"""Construit l'ontologie OWL du domaine vestimentaire (mlOutfitSuggestion).

Formalise en OWL ce qui est aujourd'hui dispersé entre :
- composition/compatibility.py (NEUTRALS, COMPLEMENTARY_PAIRS codés en dur)
- composition/rag.py (harmonie des couleurs via recherche "sémantique" dans
  un corpus markdown — une approximation, pas un vrai raisonnement)
- recommend.py (formality_map / warmth_map codés en dur pour les occasions)
- wardrobe/models.py (catégories comme simple enum, sans hiérarchie ni
  contrainte de disjonction — rien n'empêchait par ex. qu'un item soit
  mal catégorisé)

Usage :
    from ontology.outfit_ontology import build_ontology
    onto = build_ontology()
    onto.save(file="ontology/outfit_ontology.owl", format="rdfxml")

Ou simplement :
    python -m ontology.outfit_ontology
"""

from __future__ import annotations

from owlready2 import (
    AllDisjoint,
    ConstrainedDatatype,
    DataProperty,
    Imp,
    ObjectProperty,
    SymmetricProperty,
    Thing,
    get_ontology,
)

ONTOLOGY_IRI = "http://mloutfitsuggestion.local/ontology/outfit.owl"

# Reprend directement data/corpus_style/harmonie_couleurs.md, mais sous une
# forme que le raisonneur peut exploiter plutôt qu'un texte à interroger par
# recherche sémantique approximative.
NEUTRAL_COLORS = ["Noir", "Blanc", "Gris", "Beige", "Marron", "BleuMarine"]
ALL_COLORS = NEUTRAL_COLORS + [
    "BleuClair", "Vert", "Rouge", "Rose", "Jaune", "Orange", "Violet", "Multicolore",
]
COMPLEMENTARY_COLOR_PAIRS = [
    ("BleuMarine", "Rouge"),
    ("BleuClair", "Beige"),
    ("Vert", "Beige"),
    ("Rose", "Gris"),
    ("Jaune", "BleuMarine"),
    ("Violet", "Gris"),
]

# Reprend le formality_map actuellement codé en dur dans recommend.py
OCCASION_MIN_FORMALITY = {
    "Sport": 1,
    "Casual": 2,
    "Work": 3,
    "Meeting": 4,
    "Event": 5,
}


def build_ontology():
    onto = get_ontology(ONTOLOGY_IRI)

    onto.metadata.comment.append(
        "Ontologie du domaine vestimentaire pour mlOutfitSuggestion — "
        "catégories, couleurs, formalité, occasions, et règles de "
        "compatibilité entre pièces."
    )
    onto.metadata.versionInfo.append("0.1.0")

    with onto:

        # -- Classes racines --------------------------------------------

        class Garment(Thing):
            """Une pièce de vêtement individuelle (≈ WardrobeItem)."""

        class Outfit(Thing):
            """Une combinaison de pièces formant une tenue (≈ OutfitCombination)."""

        class Color(Thing):
            """Une couleur de pièce vestimentaire (ex: Noir, BleuMarine)."""

        class Material(Thing):
            """Une matière (ex: coton, laine, denim)."""

        class Pattern(Thing):
            """Un motif (ex: uni, rayé, imprimé)."""

        class Season(Thing):
            """Une saison (printemps, été, automne, hiver)."""

        class Occasion(Thing):
            """Un contexte d'usage (travail, sport, événement...), avec une
            exigence de formalité minimale (requiresMinFormality)."""

        class StyleTag(Thing):
            """Un style déclaré par l'utilisateur (minimaliste, élégant...)."""

        class BodyShape(Thing):
            """Une morphologie (sablier, rectangle, poire...)."""

        # -- Catégories de Garment, mutuellement exclusives --------------

        class Top(Garment):
            """Haut (chemise, t-shirt, pull...)."""

        class Bottom(Garment):
            """Bas (jean, pantalon, jupe...)."""

        class Outerwear(Garment):
            """Vêtement porté par-dessus (veste, manteau...)."""

        class Dress(Garment):
            """Robe ou combinaison — remplace la paire top+bottom."""

        class Shoes(Garment):
            """Chaussures."""

        class Accessory(Garment):
            """Accessoire (ceinture, écharpe, sac...)."""

        AllDisjoint([Top, Bottom, Outerwear, Dress, Shoes, Accessory])

        class TShirt(Top):
            """T-shirt."""

        class Shirt(Top):
            """Chemise."""

        class Sweater(Top):
            """Pull."""

        class Jean(Bottom):
            """Jean."""

        class Trousers(Bottom):
            """Pantalon (hors jean)."""

        class Sneakers(Shoes):
            """Baskets."""

        class DressShoes(Shoes):
            """Chaussures habillées (mocassins, derbies...)."""

        # -- Sous-classes d'Occasion --------------------------------------

        class CasualOccasion(Occasion):
            """Sortie décontractée, weekend."""

        class WorkOccasion(Occasion):
            """Journée de travail non formelle."""

        class MeetingOccasion(Occasion):
            """Réunion, entretien — formalité élevée requise."""

        class EventOccasion(Occasion):
            """Événement, soirée, cérémonie — formalité maximale requise."""

        class SportOccasion(Occasion):
            """Activité sportive."""

        AllDisjoint([CasualOccasion, WorkOccasion, MeetingOccasion, EventOccasion, SportOccasion])

        # -- Propriétés objet ----------------------------------------------

        class hasPrimaryColor(Garment >> Color, ObjectProperty):
            """Couleur dominante de la pièce."""

        class hasSecondaryColor(Garment >> Color, ObjectProperty):
            """Couleur secondaire (motif, détail)."""

        class hasMaterial(Garment >> Material, ObjectProperty):
            """Matière dominante de la pièce."""

        class hasPattern(Garment >> Pattern, ObjectProperty):
            """Motif de la pièce."""

        class suitableForSeason(Garment >> Season, ObjectProperty):
            """Saisons pour lesquelles la pièce est adaptée."""

        class suitableForBodyShape(Garment >> BodyShape, ObjectProperty):
            """Morphologies pour lesquelles la pièce est recommandée."""

        class hasStyle(Garment >> StyleTag, ObjectProperty):
            """Style(s) associé(s) à la pièce."""

        class isPartOf(Garment >> Outfit, ObjectProperty):
            """Inverse de hasPart."""

        class hasPart(Outfit >> Garment, ObjectProperty):
            """Pièces qui composent la tenue."""
            inverse_property = isPartOf

        class harmonizesWith(Color >> Color, ObjectProperty, SymmetricProperty):
            """Remplace la recherche 'sémantique' de composition/rag.py par
            un graphe d'harmonie explicite et interrogeable."""

        class colorCompatibleWith(Garment >> Garment, ObjectProperty, SymmetricProperty):
            """Inférée par la règle SWRL ci-dessous, jamais assertée à la main."""

        # -- Propriétés de données -----------------------------------------

        class formalityLevel(Garment >> int, DataProperty):
            """Non fonctionnelle — équivalent de `formality_levels` (liste)."""

        class warmthLevel(Garment >> int, DataProperty):
            """Non fonctionnelle — équivalent de `warmth_ratings` (liste)."""

        class requiresMinFormality(Occasion >> int, DataProperty):
            """Formalité minimale (1-5) attendue pour cette occasion."""

        # -- Classes définies — classification automatique -----------------

        class CasualGarment(Garment):
            equivalent_to = [Garment & formalityLevel.some(ConstrainedDatatype(int, max_inclusive=2))]

        class FormalGarment(Garment):
            equivalent_to = [Garment & formalityLevel.some(ConstrainedDatatype(int, min_inclusive=4))]

        class WarmGarment(Garment):
            equivalent_to = [Garment & warmthLevel.some(ConstrainedDatatype(int, min_inclusive=4))]

        class LightGarment(Garment):
            equivalent_to = [Garment & warmthLevel.some(ConstrainedDatatype(int, max_inclusive=2))]

        class FormalOutfit(Outfit):
            equivalent_to = [Outfit & hasPart.only(FormalGarment)]

        class CasualOutfit(Outfit):
            equivalent_to = [Outfit & hasPart.only(CasualGarment)]

        # -- Individus : couleurs + harmonies -------------------------------

        colors = {name: Color(name) for name in ALL_COLORS}

        harmony_pairs: set[tuple[str, str]] = set()
        for neutral in NEUTRAL_COLORS:
            for other in ALL_COLORS:
                if other != neutral:
                    harmony_pairs.add(tuple(sorted((neutral, other))))
        for a, b in COMPLEMENTARY_COLOR_PAIRS:
            harmony_pairs.add(tuple(sorted((a, b))))

        for a, b in harmony_pairs:
            colors[a].harmonizesWith.append(colors[b])

        # -- Individus : occasions + formalité requise ----------------------

        occasion_classes = {
            "Sport": SportOccasion,
            "Casual": CasualOccasion,
            "Work": WorkOccasion,
            "Meeting": MeetingOccasion,
            "Event": EventOccasion,
        }
        for name, cls in occasion_classes.items():
            individual = cls(name)
            individual.requiresMinFormality = [OCCASION_MIN_FORMALITY[name]]

        # -- Règle SWRL : compatibilité couleur entre 2 pièces --------------

        color_compat_rule = Imp()
        color_compat_rule.set_as_rule(
            """
            Garment(?g1), Garment(?g2), hasPrimaryColor(?g1, ?c1),
            hasPrimaryColor(?g2, ?c2), harmonizesWith(?c1, ?c2),
            DifferentFrom(?g1, ?g2)
            -> colorCompatibleWith(?g1, ?g2)
            """
        )

    return onto


if __name__ == "__main__":
    onto = build_ontology()
    onto.save(file="ontology/outfit_ontology.owl", format="rdfxml")
    print("Ontologie sauvegardée dans ontology/outfit_ontology.owl")
