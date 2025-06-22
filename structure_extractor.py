import json
import os
import re
from typing import Optional

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


ATTRIBUTE_ORDER = ["id", "name", "placeholder", "aria-label"]


def _build_selector(element) -> Optional[str]:
    """Return a CSS selector for the given element according to attribute order."""
    for attr in ATTRIBUTE_ORDER:
        value = element.get(attr)
        if value:
            if re.search(r"[\s:#.]", value):
                return f"{element.name}[{attr}='{value}']"
            if attr == "id":
                return f"#{value}"
            return f"{element.name}[{attr}='{value}']"
    return None


def extract_structure(url: str, output_path: str = "page_structure.json") -> None:
    """Render URL with Playwright and extract login structure to JSON."""
    # Support local files without scheme
    if os.path.exists(url):
        url = f"file://{os.path.abspath(url)}"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_load_state("networkidle")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    id_input = soup.find("input", {"type": re.compile("text|email", re.I)})
    pw_input = soup.find("input", {"type": "password"})
    login_btn = soup.find("button") or soup.find("input", {"type": "submit"})

    structure = {
        "id": _build_selector(id_input) if id_input else "",
        "password": _build_selector(pw_input) if pw_input else "",
        "login_button": _build_selector(login_btn) if login_btn else "",
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)

    print(f"Saved structure to {output_path}")


if __name__ == "__main__":
    target_url = os.environ.get("LOGIN_URL", "sample_login_page.html")
    extract_structure(target_url)
