#!/usr/bin/env python3
"""
Bundle reference prototype into single-file reference/prawko.html.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REF_DIR = PROJECT_ROOT / "reference"
REF_DIR.mkdir(parents=True, exist_ok=True)

def build_reference():
    # Read index.html from prawko-main/src/index.html
    html_src = PROJECT_ROOT / "prawko-main" / "src" / "index.html"
    css_src = PROJECT_ROOT / "prawko-main" / "src" / "css" / "style.css"
    
    html_content = html_src.read_text(encoding="utf-8") if html_src.exists() else "<html><body><h1>Prawko B Reference</h1></body></html>"
    css_content = css_src.read_text(encoding="utf-8") if css_src.exists() else "body { font-family: sans-serif; }"

    # Inline CSS
    html_content = html_content.replace('<link rel="stylesheet" href="css/style.css">', f'<style>\n{css_content}\n</style>')

    # Embed data
    b_json = PROJECT_ROOT / "prawko-main" / "src" / "data" / "B.json"
    cat_b_data = b_json.read_text(encoding="utf-8") if b_json.exists() else '{"questions": []}'

    script_bundle = f"""
    <script>
    window.PRAWKO_CAT_B = {cat_b_data};
    console.log("Prawko B prototype loaded with", window.PRAWKO_CAT_B.questions ? window.PRAWKO_CAT_B.questions.length : 0, "cat-B questions.");
    </script>
    """
    html_content = html_content.replace("</body>", f"{script_bundle}\n</body>")

    out_file = REF_DIR / "prawko.html"
    out_file.write_text(html_content, encoding="utf-8")
    print(f"Created reference/prawko.html ({out_file.stat().st_size} bytes)")

if __name__ == "__main__":
    build_reference()
