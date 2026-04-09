from pathlib import Path
import sys


# Ensure project-root imports work when running this file directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.trading_agent import build_trading_graph


def save_compiled_graph_image() -> Path:
    """
    Build (compile) the trading graph and save its rendered PNG
    into the project root folder.
    """
    compiled_graph = build_trading_graph()
    png_data = compiled_graph.get_graph().draw_mermaid_png()

    output_path = PROJECT_ROOT / "trading_compiled_graph.png"
    output_path.write_bytes(png_data)
    return output_path


if __name__ == "__main__":
    try:
        saved_file = save_compiled_graph_image()
        print(f"Compiled graph image saved at: {saved_file}")
    except Exception as exc:
        print(f"Failed to build/save compiled graph image: {exc}")