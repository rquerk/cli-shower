#!/usr/bin/env python3
"""
Gibt Name und Erscheinungsdatum der letzten Folgen einer ZDF-Show aus.

Verwendung:
    python zdf_scraper.py                        # Interaktives Menü
    python zdf_scraper.py "Die Anstalt"          # Showname als Argument
    python zdf_scraper.py "ZDF Magazin Royale"   # Showname als Argument
    python zdf_scraper.py https://www.zdf.de/... # Direkte URL

Installation:
    pip install playwright
    playwright install chromium
"""

import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ── Show-Verzeichnis ────────────────────────────────────────────────────────────
SHOWS = {
    "Die Anstalt":        "https://www.zdf.de/shows/die-anstalt-104",
    "ZDF Magazin Royale": "https://www.zdf.de/shows/zdf-magazin-royale-102",
}

SHOW_NAMES = list(SHOWS.keys())


# ── Auswahl-Logik ───────────────────────────────────────────────────────────────
def resolve_target() -> tuple[str, str]:
    """Gibt (show_title, url) zurück – entweder per Argument oder Menü."""

    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()

        # Argument ist eine URL
        if arg.startswith("http://") or arg.startswith("https://"):
            # Versuche einen passenden Shownamen zu finden, sonst URL als Titel
            title = next((name for name, url in SHOWS.items() if url == arg), arg)
            return title, arg

        # Argument ist ein bekannter Showname
        if arg in SHOWS:
            return arg, SHOWS[arg]

        # Unbekannter Showname
        print(f"Fehler: Unbekannte Show \"{arg}\".", file=sys.stderr)
        print(f"Bekannte Shows: {', '.join(SHOW_NAMES)}", file=sys.stderr)
        sys.exit(1)

    # Kein Argument → interaktives Menü
    return interactive_menu()


def interactive_menu() -> tuple[str, str]:
    """Zeigt ein nummeriertes Menü und gibt (show_title, url) zurück."""

    print("=== ZDF-Folgen-Scraper ===\n")
    for i, name in enumerate(SHOW_NAMES, start=1):
        print(f"  {i}. {name}")
    print(f"  {len(SHOW_NAMES) + 1}. Eigene URL eingeben")
    print()

    while True:
        try:
            choice = input("Auswahl (Zahl eingeben): ").strip()
            n = int(choice)
        except (ValueError, EOFError):
            print("Bitte eine gültige Zahl eingeben.")
            continue

        if 1 <= n <= len(SHOW_NAMES):
            name = SHOW_NAMES[n - 1]
            return name, SHOWS[name]

        if n == len(SHOW_NAMES) + 1:
            url = input("URL eingeben: ").strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                print("Ungültige URL.")
                continue
            title = next((name for name, u in SHOWS.items() if u == url), url)
            return title, url

        print(f"Bitte eine Zahl zwischen 1 und {len(SHOW_NAMES) + 1} eingeben.")


# ── Scraping-Logik ──────────────────────────────────────────────────────────────
def scrape_episodes(show_title: str, url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Öffne {url} ...", file=sys.stderr)
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        try:
            page.wait_for_selector("#EPISODES h3", timeout=20_000)
        except PlaywrightTimeout:
            print("Timeout: #EPISODES wurde nicht gefunden.", file=sys.stderr)
            print("Aktueller Seiteninhalt (Auszug):", file=sys.stderr)
            print(page.content()[:2000], file=sys.stderr)
            browser.close()
            sys.exit(1)

        articles = page.query_selector_all("#EPISODES article")
        if not articles:
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

    # Passende Folgen filtern (Titelabgleich), sonst alle ausgeben
    filtered = [(t, d) for t, d in episodes if show_title.lower() in t.lower()]
    result = filtered if filtered else episodes

    if not result:
        print("Keine Episoden gefunden.", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== {show_title} – neueste Folgen ===\n")
    for i, (title, date) in enumerate(result):
        marker = "→ NEUESTE" if i == 0 else f"     {i+1}."
        print(f"{marker}  {title}  [{date}]")


# ── Einstiegspunkt ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    show_title, url = resolve_target()
    scrape_episodes(show_title, url)
