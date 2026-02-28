from pyvis.network import Network
import os

class GraphVisualizer:
    @staticmethod
    def generate_from_records(records):
        if not records:
            return "<p style='color:#6B7280; text-align:center;'>No graph data found for this query.</p>"

        # White background + dark neutral font
        net = Network(
            height="600px",
            width="100%",
            bgcolor="#FFFFFF",
            font_color="#2E2E2E"
        )

        net.toggle_physics(True)

        # Softer physics for natural layout
        net.set_options("""
        {
          "nodes": {
            "shape": "dot",
            "size": 18,
            "font": {
              "size": 14,
              "color": "#2E2E2E"
            },
            "borderWidth": 1.5,
            "shadow": false
          },
          "edges": {
            "color": {
              "color": "#D1D5DB"
            },
            "smooth": true,
            "width": 1.2
          },
          "physics": {
            "enabled": true,
            "barnesHut": {
              "gravitationalConstant": -2500,
              "springLength": 140
            }
          }
        }
        """)

        nodes_added = set()

        for record in records:
            items = record.items() if hasattr(record, 'items') else record.items()

            for key, node in items:
                if isinstance(node, dict) or hasattr(node, 'labels'):

                    node_id = str(node.get('id') or node.get('name') or id(node))

                    if node_id not in nodes_added:

                        name = node.get('title') or node.get('name') or "Node"
                        label = (name[:25] + '...') if len(name) > 25 else name

                        # ---- Natural Color Palette ----
                        color = "#9CA3AF"  # default soft gray

                        node_labels = getattr(node, 'labels', [])

                        if "Brand" in node_labels:
                            color = "#C8A97E"  # warm sand

                        elif "Cluster" in node_labels or 'cluster_name' in node:
                            color = "#8FAADC"  # muted slate blue

                        elif "Post" in node_labels:
                            color = "#6B8E23"  # soft olive green

                        elif "Topic" in node_labels:
                            color = "#A3B18A"  # sage

                        net.add_node(
                            node_id,
                            label=label,
                            title=name,
                            color=color
                        )

                        nodes_added.add(node_id)

        # Softer edges
        for record in records:
            row_ids = []
            items = record.values() if hasattr(record, 'values') else record.values()

            for val in items:
                if isinstance(val, dict):
                    row_ids.append(str(val.get('id') or val.get('name')))

            if len(row_ids) >= 2:
                for i in range(len(row_ids) - 1):
                    try:
                        net.add_edge(
                            row_ids[i],
                            row_ids[i + 1],
                            color="#E5E7EB"
                        )
                    except:
                        pass

        temp_path = os.path.join(os.getcwd(), "temp_dynamic_graph.html")
        net.save_graph(temp_path)

        with open(temp_path, "r", encoding="utf-8") as f:
            return f.read()