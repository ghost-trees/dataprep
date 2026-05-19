"""Shared helpers for navigating the Atlanta ACA portal."""

import re

from playwright.sync_api import Frame, FrameLocator, Page, TimeoutError

PORTAL_URL = "https://aca-prod.accela.com/atlanta_ga/Default.aspx"
ACA_FRAME_NAME = "ACAFrame"
ACA_FRAME_SELECTOR = f'iframe[name="{ACA_FRAME_NAME}"]'
FIND_APPLICATION_TEXT_PATTERN = re.compile(r"Find an application or", re.IGNORECASE)


def click_find_application_link(frame_locator: FrameLocator) -> None:
    """Click the link that reveals the record search interface."""
    try:
        frame_locator.get_by_role("link", name=FIND_APPLICATION_TEXT_PATTERN).click(
            timeout=15_000
        )
    except TimeoutError:
        frame_locator.get_by_text(FIND_APPLICATION_TEXT_PATTERN).first.click(timeout=15_000)


def get_aca_frame(page: Page) -> Frame:
    """Resolve and return the ACA iframe as a frame object."""
    frame = page.frame(name=ACA_FRAME_NAME)
    if frame is None:
        raise RuntimeError("ACAFrame iframe not found.")
    return frame


def initialize_search(page: Page) -> None:
    """Open the portal and ensure the search box is available."""
    for attempt in range(3):
        try:
            page.goto(PORTAL_URL, wait_until="domcontentloaded")
            page.wait_for_selector(ACA_FRAME_SELECTOR, timeout=20_000)
            frame_locator = page.frame_locator(ACA_FRAME_SELECTOR)

            search_box = frame_locator.get_by_role(
                "textbox", name=re.compile(r"Search", re.IGNORECASE)
            )
            try:
                search_box.first.wait_for(timeout=4_000)
                return
            except TimeoutError:
                pass

            click_find_application_link(frame_locator)
            search_box.first.wait_for(timeout=10_000)
            return
        except TimeoutError:
            if attempt == 2:
                raise
