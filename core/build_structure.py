import json
import os
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
INPUT_HTML = os.path.join(ROOT_DIR, "sample_login_page.html")
OUTPUT_JSON = os.path.join(ROOT_DIR, "config", "page_structure.json")


def build_structure(html_path: str = INPUT_HTML, output_path: str = OUTPUT_JSON) -> None:
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    id_input = soup.find("input", {"type": "text"})
    pw_input = soup.find("input", {"type": "password"})
    login_btn = soup.find("button")

    structure = {
        "id": id_input.get("id") if id_input else "",
        "password": pw_input.get("id") if pw_input else "",
        "login_button": login_btn.get("id") if login_btn else "",
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    build_structure()
