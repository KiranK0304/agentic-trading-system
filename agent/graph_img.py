import sys
import os
from pathlib import Path

# Add parent directory to Python path so imports work cleanly
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.trading_agent import create_trading_agent
from agent.trading_agent import run_trading_agent   # optional, for testing
from data_loader import fetch_data                  # adjust path if needed

# ====================== CREATE & VISUALIZE GRAPH ======================
print("Creating trading agent graph...")

graph = create_trading_agent()

# Generate Mermaid diagram as PNG and display/save it
try:
    img_data = graph.get_graph().draw_mermaid_png()
    
    # Save the image to file (recommended)
    output_path = Path("trading_agent_graph.png")
    output_path.write_bytes(img_data)
    
    print(f"✅ Graph image saved as: {output_path.resolve()}")
    print("You can open 'trading_agent_graph.png' to see the agent workflow.")

    # Optional: Try to display if running in Jupyter/IPython
    try:
        from IPython.display import Image, display
        display(Image(img_data))
        print("Displayed in notebook/Jupyter.")
    except ImportError:
        print("IPython not available. Image saved to file instead.")

except Exception as e:
    print(f"❌ Failed to generate graph image: {e}")
    print("Make sure Graphviz is installed on your system:")
    print("   sudo apt install graphviz")

# ====================== OPTIONAL: Test the agent ======================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing the full agent with real data...")
    
    df = fetch_data("SBIN.NS", period="30d", interval="5m")
    
    if not df.empty:
        decision = run_trading_agent(df, symbol="SBIN.NS")
        print(f"\nFinal Decision: {decision.decision} (Confidence: {decision.confidence}%)")