"""Browser interaction helpers for navigating fee pages in ACA portal."""

import re

from playwright.sync_api import Frame, Page, TimeoutError

from dataprep.shared.portal import get_aca_frame

from .constants import OUTSTANDING_LABEL, PAID_LABEL


def parse_amount(page_text: str, label: str) -> float:
    """Extract a currency amount that follows a labeled total."""
    pattern = rf"{re.escape(label)}\s*:\s*\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)"
    match = re.search(pattern, page_text, flags=re.IGNORECASE)
    if not match:
        return 0.0
    return float(match.group(1).replace(",", ""))


def open_fees_page(page: Page, record_number: str) -> Frame:
    """Search for a record and navigate to its Fees tab."""
    frame_locator = page.frame_locator('iframe[name="ACAFrame"]')
    search_box = frame_locator.get_by_role(
        "textbox", name=re.compile(r"Search", re.IGNORECASE)
    )
    search_box.click(timeout=10_000)
    search_box.fill(record_number)
    search_box.press("Enter")

    try:
        frame_locator.get_by_role("link", name=record_number, exact=True).click(timeout=3_000)
    except TimeoutError:
        pass

    frame_locator.get_by_role("link", name="Payments").click(timeout=10_000)
    frame_locator.get_by_role("link", name="Fees").click(timeout=10_000)
    return get_aca_frame(page)


def scrape_fee_totals(frame: Frame) -> tuple[float, float]:
    """Scrape paid and outstanding fee totals from the fees page."""
    try:
        frame.get_by_text(re.compile(r"Total (paid|outstanding) fees", re.IGNORECASE)).first.wait_for(
            timeout=15_000
        )
    except TimeoutError:
        pass

    fee_page_text = frame.locator("body").inner_text(timeout=10_000)
    paid = parse_amount(fee_page_text, PAID_LABEL)
    outstanding = parse_amount(fee_page_text, OUTSTANDING_LABEL)
    return paid, outstanding
