"""
Script to generate graph visualizations
"""
from graph_with_tools import graph

# Generate and save visualization
try:
    # Generate PNG
    png_data = graph.get_graph().draw_mermaid_png()
    with open("chatbot_graph.png", "wb") as f:
        f.write(png_data)
    print("Graph saved as chatbot_graph.png")

    # Generate ASCII representation
    ascii_repr = graph.get_graph().draw_ascii()
    print("\nASCII Graph:")
    print(ascii_repr)

except Exception as e:
    print(f"Visualization error: {e}")
    print("Make sure you have the required dependencies installed:")
    print("pip install pygraphviz")  # or conda install pygraphviz