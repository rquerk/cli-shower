#!/usr/bin/env python3
"""
Gibt Name und Erscheinungsdatum der letzten Folge(n) von "Die Anstalt" (ZDF) aus.

Strategie: Playwright wartet bis der #EPISODES-Bereich im DOM geladen ist,
dann wird direkt aus dem HTML gescrapt (h3 = Titel, ul > li:nth-child(2) = Datum).

Installation:
    pip install playwright
    playwright install chromium
"""

import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

SHOW_URL = "https://www.zdf.de/shows/die-anstalt-104"
SHOW_TITLE = "Die Anstalt"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Öffne {SHOW_URL} ...", file=sys.stderr)
        page.goto(SHOW_URL, wait_until="domcontentloaded", timeout=30_000)

        # Warten bis der Episoden-Bereich gerendert ist
        try:
            page.wait_for_selector("#EPISODES h3", timeout=20_000)
        except PlaywrightTimeout:
            print("Timeout: #EPISODES wurde nicht gefunden.", file=sys.stderr)
            print("Aktueller Seiteninhalt (Auszug):", file=sys.stderr)
            print(page.content()[:2000], file=sys.stderr)
            browser.close()
            sys.exit(1)

        # Alle Episoden-Artikel im #EPISODES-Container holen
        articles = page.query_selector_all("#EPISODES article")

        if not articles:
            # Fallback: direkt h3+ul ohne article-Wrapper suchen
            articles = page.query_selector_all("#EPISODES li")

        episodes = []
        for article in articles:
            h3 = article.query_selector("h3")
            ul = article.query_selector("ul")

            if not h3:
                continue

            title = (h3.inner_text() or "").strip()

            date = ""
            if ul:
                items = ul.query_selector_all("li")
                if len(items) >= 2:
                    date = (items[1].inner_text() or "").strip()
                elif len(items) == 1:
                    date = (items[0].inner_text() or "").strip()

            if title:
                episodes.append((title, date))

        browser.close()

    # Nur Folgen von "Die Anstalt" behalten
    anstalt = [
        (t, d) for t, d in episodes
        if SHOW_TITLE.lower() in t.lower()
    ]

    # Falls keine passenden gefunden: alle ausgeben (zur Diagnose)
    result = anstalt if anstalt else episodes

    if not result:
        print("Keine Episoden gefunden.", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== {SHOW_TITLE} – neueste Folgen ===\n")
    for i, (title, date) in enumerate(result):
        marker = "→ NEUESTE" if i == 0 else f"     {i+1}."
        print(f"{marker}  {title}  [{date}]")


if __name__ == "__main__":
    main()
