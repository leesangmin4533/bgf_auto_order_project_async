# Utility functions for popup handling
from playwright.sync_api import Page


def remove_overlay(page: Page) -> None:
    """Remove blocking overlay if present."""
    page.evaluate("document.getElementById('nexacontainer')?.remove()")

