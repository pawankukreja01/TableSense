"""Run against a fresh, running local seeded demo: python qa/browser_demo.py"""

import os
from playwright.sync_api import sync_playwright, expect

BASE = os.getenv("TABLESENSE_URL", "http://127.0.0.1:8080")
with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path=os.environ.get("CHROMIUM") or None, args=["--no-sandbox"]
    )
    ctx = browser.new_context(viewport={"width": 1400, "height": 950})
    desk = ctx.new_page()
    desk.goto(BASE)
    desk.get_by_role("button", name="Enter manager demo").click()
    desk.get_by_role("button", name="Table 07").click()
    with ctx.expect_page() as window:
        desk.get_by_role("button", name="Open demo display").click()
    guest = window.value
    guest.set_viewport_size({"width": 800, "height": 1280})
    expect(guest.get_by_text("Make yourself comfortable.")).to_be_visible()
    desk.get_by_role("button", name="Open session").click()
    desk.get_by_role("button", name="Select Grilled Steak").click()
    desk.get_by_role("button", name="Send recommendation signal").click()
    expect(guest.get_by_role("heading", name="Garlic Mushrooms")).to_be_visible()
    expect(guest.get_by_text("£4.50")).to_be_visible()
    guest.set_viewport_size({"width": 1280, "height": 800})
    expect(guest.get_by_role("button", name="Not now")).to_be_in_viewport()
    ctx.set_offline(True)
    expect(guest.get_by_text("DISPLAY OFFLINE", exact=True)).to_be_visible()
    expect(guest.get_by_role("heading", name="Garlic Mushrooms")).to_have_count(0)
    ctx.set_offline(False)
    expect(guest.get_by_role("heading", name="Garlic Mushrooms")).to_be_visible()
    guest.get_by_role("button", name="Not now").click()
    expect(guest.get_by_text("Make yourself comfortable.")).to_be_visible()
    desk.get_by_role("button", name="requested", exact=True).first.click()
    desk.get_by_role("button", name="fulfilled", exact=True).first.click()
    desk.get_by_role("button", name="Close session & clear display").click()
    expect(desk.get_by_role("button", name="Open session")).to_be_visible()
    desk.get_by_role("button", name="Close panel").click()
    desk.get_by_role("link", name="Menu library").click()
    expect(desk.get_by_role("heading", name="Grilled Steak")).to_be_visible()
    desk.get_by_role("link", name="Pilot insights").click()
    expect(desk.get_by_text("staff marked fulfilled", exact=True)).to_be_visible()
    desk.set_viewport_size({"width": 390, "height": 844})
    desk.get_by_role("button", name="Toggle navigation").click()
    desk.get_by_role("link", name="Service floor").click()
    expect(desk.get_by_role("button", name="Table 07")).to_be_visible()
    assert desk.evaluate("document.documentElement.scrollWidth<=innerWidth")
    print(
        "PASS · Table 07 browser walkthrough, offline recovery, outcome reporting and responsive layouts"
    )
    browser.close()
