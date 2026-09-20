"""Génère deux graphes à partir de l'ontologie réelle (pas dessinés à la
main) :

1. graph_class_hierarchy.svg — hiérarchie des classes + disjonctions +
   classes définies (celles que le raisonneur peuple automatiquement)
2. graph_color_harmony.png    — réseau des couleurs et de leurs relations
   harmonizesWith (le graphe que la règle SWRL de compatibilité couleur
   parcourt réellement)

Usage :
    python -m ontology.visualize
"""

from __future__ import annotations

import graphviz
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from .outfit_ontology import build_ontology

OUTPUT_DIR = "docs"


def render_class_hierarchy(onto) -> None:
    dot = graphviz.Digraph("class_hierarchy", format="svg")
    dot.attr(rankdir="TB", fontname="Helvetica", fontsize="11")
    dot.attr("node", fontname="Helvetica", fontsize="10")

    defined_classes = {c.name for c in onto.classes() if c.equivalent_to}

    for cls in onto.classes():
        if cls.name in defined_classes:
            dot.node(cls.name, cls.name, shape="ellipse", style="filled",
                      fillcolor="#e8d5f2", color="#8e44ad")
        else:
            dot.node(cls.name, cls.name, shape="box", style="rounded,filled",
                      fillcolor="#eaf2fb", color="#2980b9")

        for parent in cls.is_a:
            if hasattr(parent, "name") and parent in onto.classes():
                dot.edge(parent.name, cls.name)

    for group in onto.disjoint_classes():
        members = [e.name for e in group.entities if hasattr(e, "name")]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                dot.edge(members[i], members[j], style="dashed", color="#c0392b",
                          arrowhead="none", constraint="false", label="disjoint")

    dot.attr(label=(
        "Rectangles bleus = classes assertées   |   "
        "Ellipses violettes = classes définies (inférées par le raisonneur)\n"
        "Traits pointillés rouges = disjonction (AllDisjoint)"
    ), labelloc="b", fontsize="9")

    dot.render(f"{OUTPUT_DIR}/graph_class_hierarchy", cleanup=True)
    print(f"{OUTPUT_DIR}/graph_class_hierarchy.svg généré")


def render_color_harmony(onto) -> None:
    g = nx.Graph()
    for color in onto.Color.instances():
        g.add_node(color.name)
        for other in color.harmonizesWith:
            g.add_edge(color.name, other.name)

    neutrals = {"Noir", "Blanc", "Gris", "Beige", "Marron", "BleuMarine"}
    node_colors = ["#bdc3c7" if n in neutrals else "#3498db" for n in g.nodes()]

    plt.figure(figsize=(9, 7))
    pos = nx.spring_layout(g, seed=42, k=0.9)
    nx.draw_networkx_edges(g, pos, alpha=0.4)
    nx.draw_networkx_nodes(g, pos, node_color=node_colors, node_size=1400,
                            edgecolors="#2c3e50")
    nx.draw_networkx_labels(g, pos, font_size=9)
    plt.title(
        "Graphe harmonizesWith — gris = couleurs neutres (compatibles avec tout),\n"
        "bleu = couleurs non-neutres (compatibles seulement via paires déclarées)",
        fontsize=10,
    )
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/graph_color_harmony.png", dpi=150)
    print(f"{OUTPUT_DIR}/graph_color_harmony.png généré")
    print(f"  {g.number_of_nodes()} couleurs, {g.number_of_edges()} relations d'harmonie")


if __name__ == "__main__":
    onto = build_ontology()
    render_class_hierarchy(onto)
    render_color_harmony(onto)
