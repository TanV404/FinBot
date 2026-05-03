"""
visualize_graph.py — Renders the NIFTY knowledge graph as an interactive
HTML file using PyVis.

Key fix: VALUE_AT edges now show "Total Revenue | ₹235.56 Billion (2025-12-31)"
in their hover tooltip, so they are actually readable in the visualisation.
"""

import pickle
from pathlib import Path

import networkx as nx
from pyvis.network import Network


def generate_graph(
    graph_path: str | Path | None = None,
    output_path: str = "nifty_fin_graph.html",
) -> None:
    # ── 1. Resolve graph path ─────────────────────────────────────────────────
    candidates = [
        graph_path,
        Path(__file__).resolve().parent.parent / "data" / "networkx" / "nifty_graph.pkl",
        Path("data/networkx/nifty_graph.pkl"),
    ]
    resolved: Path | None = None
    for c in candidates:
        if c and Path(c).exists():
            resolved = Path(c)
            break

    if resolved is None:
        print("❌ Graph file not found. Run ingest.py first.")
        return

    with open(resolved, "rb") as f:
        G: nx.MultiDiGraph = pickle.load(f)

    print(f"📊 Loaded graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # ── 2. Initialise PyVis network ───────────────────────────────────────────
    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#0a0a0c",
        font_color="white",
        notebook=False,
        select_menu=True,
        filter_menu=False,
        cdn_resources="remote",
    )

    net.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -150,
          "centralGravity": 0.01,
          "springLength": 120
        },
        "solver": "forceAtlas2Based",
        "stabilization": { "enabled": true, "iterations": 1200 }
      },
      "edges": {
        "color": {
          "color": "#555555",
          "highlight": "#FF3131",
          "hover": "#FF9900",
          "inherit": false
        },
        "width": 1,
        "selectionWidth": 3,
        "smooth": { "type": "dynamic" },
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.5 } },
        "font": { "size": 10, "color": "#aaaaaa", "strokeWidth": 0 }
      },
      "interaction": {
        "hover": true,
        "hoverConnectedEdges": true,
        "selectConnectedEdges": true,
        "tooltipDelay": 80,
        "navigationButtons": true
      }
    }
    """)

    # ── 3. Node ontology ──────────────────────────────────────────────────────
    ONTOLOGY = {
        "Company":         {"color": "#FF3131", "size": 42},
        "Sector":          {"color": "#BC13FE", "size": 28},
        "Industry":        {"color": "#9B59B6", "size": 22},
        "FinancialMetric": {"color": "#00D4FF", "size": 16},
        "TimePeriod":      {"color": "#39FF14", "size": 14},
        "Person":          {"color": "#FAFF00", "size": 24},
        "Shareholding":    {"color": "#FFAC1C", "size": 16},
        "Asset":           {"color": "#4D4DFF", "size": 18},
        "Location":        {"color": "#CCFF00", "size": 18},
    }
    DEFAULT_STYLE = {"color": "#888888", "size": 14}

    # ── 4. Add nodes ──────────────────────────────────────────────────────────
    for node, attrs in G.nodes(data=True):
        label_type = attrs.get("label", "Unknown")
        style = ONTOLOGY.get(label_type, DEFAULT_STYLE)

        # Tooltip shows category + identity + any extra attrs
        extra = ""
        if attrs.get("full_name"):
            extra += f" | {attrs['full_name']}"
        if attrs.get("value"):
            extra += f" | {attrs['value']}"

        net.add_node(
            str(node),
            label=str(node),
            title=f"{label_type}: {node}{extra}",
            color={
                "background": style["color"],
                "border": "#ffffff",
                "highlight": {"background": style["color"], "border": "#ffffff"},
                "hover":     {"background": style["color"], "border": "#ffffff"},
            },
            size=style["size"],
            group=label_type,
        )

    # ── 5. Add edges ──────────────────────────────────────────────────────────
    for source, target, data in G.edges(data=True):
        relation = data.get("relation", "LINKED")

        # VALUE_AT edges: show metric name + formatted value + date in tooltip
        if relation == "VALUE_AT":
            formatted = data.get("formatted", "")
            date_str  = data.get("date",      "")
            if not formatted:
                # Fallback: format raw value
                try:
                    num = float(data.get("value", "nan"))
                    if abs(num) >= 1e12:
                        formatted = f"₹{num/1e12:.2f}T"
                    elif abs(num) >= 1e9:
                        formatted = f"₹{num/1e9:.2f}B"
                    elif abs(num) >= 1e7:
                        formatted = f"₹{num/1e7:.2f}Cr"
                    else:
                        formatted = str(num)
                except (ValueError, TypeError):
                    formatted = data.get("value", "")

            edge_label   = f"{target}"
            edge_tooltip = f"VALUE_AT | {target}: {formatted}"
            if date_str:
                edge_tooltip += f" ({date_str})"

            net.add_edge(
                str(source), str(target),
                title=edge_tooltip,
                label=edge_label,
                color="#00D4FF",
                width=1.5,
                dashes=False,
            )

        elif relation == "REPORTED_ON":
            # Keep these visual-only edges thin and de-emphasised
            net.add_edge(
                str(source), str(target),
                title="REPORTED_ON",
                color="#333333",
                width=0.5,
                dashes=True,
            )

        else:
            net.add_edge(
                str(source), str(target),
                title=relation,
                label=relation,
            )

    # ── 6. Save and post-process ──────────────────────────────────────────────
    net.save_graph(output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Hide the loading bar; position the config panel top-right
    custom_style = """
    <style>
      #loadingBar { display: none !important; }
      .vis-configuration-wrapper {
        top: 20px !important; right: 20px !important; left: auto !important;
        width: 290px !important;
        background: rgba(10,10,12,0.9) !important;
        border: 1px solid #444 !important;
        color: #eee !important;
        border-radius: 6px !important;
      }
    </style>
    """

    # Filter the dropdown to Company nodes only (keeps it usable)
    filter_js = """
    <script>
    window.addEventListener('load', function () {
      setTimeout(function () {
        var sel = document.querySelector('.form-select') || document.getElementById('select-node');
        if (!sel) return;
        var companyIds = nodes.get({ filter: function(n){ return n.group === 'Company'; } }).map(function(n){ return n.id; });
        Array.from(sel.options).forEach(function(opt) {
          if (opt.value && opt.value !== 'Select a Node by ID' && !companyIds.includes(opt.value)) {
            opt.remove();
          }
        });
      }, 900);
    });
    </script>
    """

    html = html.replace("</head>", custom_style + "</head>")
    html = html.replace("</body>", filter_js + "</body>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Graph saved → {output_path}")


if __name__ == "__main__":
    generate_graph()