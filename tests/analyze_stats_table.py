"""
Analyze player stats table structure from HLTV match page.
"""
import cloudscraper
from bs4 import BeautifulSoup
from lxml import etree


def fetch_page(url: str) -> tuple[BeautifulSoup, etree._Element]:
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.content, "html.parser")
    page = etree.HTML(str(soup))
    return soup, page


def analyze_stats():
    """Analyze player stats from a completed match."""
    # Try a completed match from results
    url = "https://www.hltv.org/matches/2388088/gamerlegion-vs-faze-starladder-budapest-major-2025"
    print(f"Analyzing: {url}\n")

    soup, page = fetch_page(url)

    # Look for all stats tables
    print("="*80)
    print("STATS TABLE ANALYSIS")
    print("="*80)

    # Find stats-content containers
    stats_contents = soup.find_all("div", class_="stats-content")
    print(f"\nFound {len(stats_contents)} stats-content containers")

    for idx, sc in enumerate(stats_contents):
        print(f"\n--- Stats Content {idx+1} ---")
        # Get ID or class info
        sc_id = sc.get("id", "no-id")
        print(f"ID: {sc_id}")

        # Find tables inside
        tables = sc.find_all("table")
        print(f"Tables found: {len(tables)}")

        for t_idx, table in enumerate(tables):
            table_class = table.get("class", [])
            print(f"\n  Table {t_idx+1} class: {table_class}")

            # Get headers
            thead = table.find("thead")
            if thead:
                ths = thead.find_all("th")
                headers = []
                for th in ths:
                    text = th.get_text(strip=True)
                    title = th.get("title", "")
                    header_info = text if text else title
                    headers.append(header_info)
                print(f"  Headers: {headers}")

            # Get first player row
            tbody = table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
                print(f"  Player rows: {len(rows)}")

                if rows:
                    row = rows[0]
                    tds = row.find_all("td")
                    print(f"\n  First player row ({len(tds)} cells):")

                    for td_idx, td in enumerate(tds):
                        td_class = td.get("class", [])
                        text = td.get_text(strip=True)

                        # Check for nested elements
                        links = td.find_all("a")
                        link_info = [a.get("href") for a in links] if links else []

                        print(f"    Cell {td_idx}: class={td_class}, text='{text[:40]}', links={link_info}")

    # Look specifically for match-info-row stats
    print("\n" + "="*80)
    print("MATCH INFO BOX STATS")
    print("="*80)

    match_info = soup.find("div", class_="match-info-box")
    if match_info:
        print("Found match-info-box")
        rows = match_info.find_all("div", class_="match-info-row")
        for row in rows:
            text = row.get_text(strip=True)
            print(f"  Row: {text}")

    # Try to find per-map stats
    print("\n" + "="*80)
    print("MAP-SPECIFIC STATS")
    print("="*80)

    # Look for map stats tabs
    map_stats_links = soup.find_all("div", class_="stats-menu-link")
    print(f"Found {len(map_stats_links)} stats menu links:")
    for link in map_stats_links:
        print(f"  - {link.get_text(strip=True)}")

    # Check for alternative stats containers
    print("\n" + "="*80)
    print("ALTERNATIVE STAT STRUCTURES")
    print("="*80)

    # Look for standard-box with stats
    standard_boxes = soup.find_all("div", class_="standard-box")
    print(f"Standard boxes: {len(standard_boxes)}")

    # Look for stats-wrapper
    stats_wrapper = soup.find("div", id="stats-wrapper")
    if stats_wrapper:
        print("Found #stats-wrapper div")

    # Look for totalstats by different method
    all_tables = soup.find_all("table")
    print(f"\nAll tables on page: {len(all_tables)}")

    for t in all_tables:
        classes = t.get("class", [])
        if classes:
            print(f"  Table class: {classes}")

            # Sample first row
            first_row = t.find("tr")
            if first_row:
                cells = first_row.find_all(["th", "td"])
                sample = [c.get_text(strip=True)[:15] for c in cells[:5]]
                print(f"    Sample cells: {sample}")


if __name__ == "__main__":
    analyze_stats()
