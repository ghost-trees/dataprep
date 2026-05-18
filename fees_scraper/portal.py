"""Browser interaction helpers for navigating the Atlanta ACA portal."""

import re

from playwright.sync_api import Frame, FrameLocator, Page, TimeoutError

from .constants import OUTSTANDING_LABEL, PAID_LABEL, PORTAL_URL


def parse_amount(page_text: str, label: str) -> float:
    """Extract a currency amount that follows a labeled total.

    Args:
        page_text: Full text content of the fees page.
        label: Label that precedes the desired currency value.

    Returns:
        Parsed amount as float, or `0.0` when the labeled value is absent.
    """

    pattern = rf"{re.escape(label)}\s*:\s*\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)"
    match = re.search(pattern, page_text, flags=re.IGNORECASE)
    if not match:
        return 0.0
    return float(match.group(1).replace(",", ""))


def click_find_application_link(frame_locator: FrameLocator) -> None:
    """Click the link that reveals the record search interface.

    Args:
        frame_locator: Locator for the ACA iframe context.
    """

    try:
        frame_locator.get_by_role(
            "link", name=re.compile(r"Find an application or", re.IGNORECASE)
        ).click(timeout=15_000)
    except TimeoutError:
        frame_locator.get_by_text(
            re.compile(r"Find an application or", re.IGNORECASE)
        ).first.click(timeout=15_000)


def get_aca_frame(page: Page) -> Frame:
    """Resolve and return the ACA iframe as a frame object.

    Args:
        page: Active Playwright page instance.

    Returns:
        The ACA frame used for portal interactions.

    Raises:
        RuntimeError: If the named ACA frame is not found.
    """

    frame = page.frame(name="ACAFrame")
    if frame is None:
        raise RuntimeError("ACAFrame iframe not found.")
    return frame


def initialize_search(page: Page) -> None:
    """Open the portal and ensure the search box is available.

    Args:
        page: Active Playwright page instance.

    Raises:
        TimeoutError: If search initialization fails across retry attempts.
    """

    for attempt in range(3):
        try:
            page.goto(PORTAL_URL, wait_until="domcontentloaded")
            page.wait_for_selector('iframe[name="ACAFrame"]', timeout=20_000)
            frame_locator = page.frame_locator('iframe[name="ACAFrame"]')

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


def open_fees_page(page: Page, record_number: str) -> Frame:
    """Search for a record and navigate to its Fees tab.

    Args:
        page: Active Playwright page instance.
        record_number: Record identifier to search.

    Returns:
        ACA frame scoped to the fees view for the selected record.
    """

    frame_locator = page.frame_locator('iframe[name="ACAFrame"]')
    search_box = frame_locator.get_by_role(
        "textbox", name=re.compile(r"Search", re.IGNORECASE)
    )
    search_box.click(timeout=10_000)
    search_box.fill(record_number)
    search_box.press("Enter")

    # Some results flow requires clicking the exact record before tabs appear.
    try:
        frame_locator.get_by_role("link", name=record_number, exact=True).click(
            timeout=3_000
        )
    except TimeoutError:
        pass

    frame_locator.get_by_role("link", name="Payments").click(timeout=10_000)
    frame_locator.get_by_role("link", name="Fees").click(timeout=10_000)
    return get_aca_frame(page)


def scrape_fee_totals(frame: Frame) -> tuple[float, float]:
    """Scrape paid and outstanding fee totals from the fees page.

    Args:
        frame: ACA frame currently displaying a record fees page.

    Returns:
        Tuple of `(paid, outstanding)` fee totals.
    """

    # Wait for the fee summary if present, but continue if it is absent.
    try:
        frame.get_by_text(
            re.compile(r"Total (paid|outstanding) fees", re.IGNORECASE)
        ).first.wait_for(timeout=15_000)
    except TimeoutError:
        pass
    fee_page_text = frame.locator("body").inner_text(timeout=10_000)
    paid = parse_amount(fee_page_text, PAID_LABEL)
    outstanding = parse_amount(fee_page_text, OUTSTANDING_LABEL)
    return paid, outstanding
