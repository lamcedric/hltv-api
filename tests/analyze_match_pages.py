"""
Script to analyze HLTV match pages and document their structure.
Run with: python -m tests.analyze_match_pages
"""
import cloudscraper
from bs4 import BeautifulSoup
from lxml import etree
import json
import re


def fetch_page(url: str) -> tuple[BeautifulSoup, etree._Element]:
    """Fetch page using cloudscraper and return both BeautifulSoup and lxml objects."""
    scraper = cloudscraper.create_scraper()
    response = scraper.get(
        url=url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        },
    )
    soup = BeautifulSoup(response.content, "html.parser")
    page = etree.HTML(str(soup))
    return soup, page


def analyze_results_page():
    """Analyze the HLTV results listing page structure."""
    print("\n" + "="*80)
    print("ANALYZING HLTV RESULTS PAGE")
    print("="*80)

    url = "https://www.hltv.org/results"
    soup, page = fetch_page(url)

    # Find result containers
    results_holder = soup.find("div", class_="results-holder")
    if results_holder:
        print("\n✓ Found results-holder container")

        # Find all result sections (grouped by date)
        result_sublist = results_holder.find_all("div", class_="results-sublist")
        print(f"✓ Found {len(result_sublist)} date-grouped result sections")

        if result_sublist:
            # Analyze first section
            first_section = result_sublist[0]
            headline = first_section.find("div", class_="standard-headline")
            print(f"\n  Date headline class: 'standard-headline'")
            if headline:
                print(f"  Sample date: {headline.get_text(strip=True)}")

            # Find matches in section
            matches = first_section.find_all("div", class_="result-con")
            print(f"\n  Found {len(matches)} matches in first section")

            if matches:
                match = matches[0]
                print("\n  Match structure analysis:")

                # Match link
                match_link = match.find("a", class_="a-reset")
                if match_link:
                    href = match_link.get("href", "")
                    print(f"    - Match URL: {href}")
                    match_id = re.search(r'/matches/(\d+)/', href)
                    if match_id:
                        print(f"    - Match ID extraction: {match_id.group(1)}")

                # Teams
                teams = match.find_all("div", class_="team")
                print(f"    - Teams container class: 'team' (found {len(teams)})")
                for i, team in enumerate(teams):
                    team_name = team.get_text(strip=True)
                    print(f"      Team {i+1}: {team_name}")

                # Score
                result_score = match.find("td", class_="result-score")
                if result_score:
                    spans = result_score.find_all("span")
                    scores = [s.get_text(strip=True) for s in spans]
                    print(f"    - Score container: 'result-score' td")
                    print(f"    - Scores: {scores}")

                # Event
                event = match.find("span", class_="event-name")
                if event:
                    print(f"    - Event class: 'event-name'")
                    print(f"    - Event: {event.get_text(strip=True)}")

                # Map/format info
                map_text = match.find("div", class_="map-text")
                if map_text:
                    print(f"    - Map/format class: 'map-text'")
                    print(f"    - Format: {map_text.get_text(strip=True)}")

    # Check pagination
    print("\n  Pagination analysis:")
    pagination = soup.find("div", class_="pagination-component")
    if pagination:
        print("    - Pagination class: 'pagination-component'")
        next_link = pagination.find("a", class_="pagination-next")
        if next_link:
            print(f"    - Next page class: 'pagination-next'")
            print(f"    - Next URL: {next_link.get('href')}")

    # Check for offset parameter
    print("\n  URL patterns:")
    print("    - Base: /results")
    print("    - With offset: /results?offset=100")
    print("    - With date filter: /results?startDate=2024-01-01&endDate=2024-12-31")

    return soup, page


def analyze_match_page():
    """Analyze an individual HLTV match page structure."""
    print("\n" + "="*80)
    print("ANALYZING HLTV INDIVIDUAL MATCH PAGE")
    print("="*80)

    # Use a recent match with full stats
    url = "https://www.hltv.org/matches/2377541/natus-vincere-vs-spirit-pgl-cs2-major-copenhagen-2024"
    soup, page = fetch_page(url)

    print(f"\nURL: {url}")

    # Match header/metadata
    print("\n1. MATCH METADATA:")

    # Team names
    team_names = soup.find_all("div", class_="teamName")
    print(f"   Team names class: 'teamName'")
    for i, team in enumerate(team_names[:2]):
        print(f"     Team {i+1}: {team.get_text(strip=True)}")

    # Team logos and links
    team_boxes = soup.find_all("div", class_="team")
    print(f"   Team container class: 'team'")

    # Match score
    final_score = soup.find_all("div", class_="won") + soup.find_all("div", class_="lost")
    print(f"   Score classes: 'won', 'lost'")

    # Event info
    event_link = soup.find("a", class_="event")
    if event_link:
        print(f"   Event class: 'event' (a tag)")
        print(f"     Event URL: {event_link.get('href')}")
        event_name = event_link.find("div", class_="event-name")
        if event_name:
            print(f"     Event name: {event_name.get_text(strip=True)}")

    # Date
    date_elem = soup.find("div", class_="date")
    if date_elem:
        print(f"   Date class: 'date'")
        print(f"     Date: {date_elem.get_text(strip=True)}")

    # Time
    time_elem = soup.find("div", class_="time")
    if time_elem:
        data_unix = time_elem.get("data-unix")
        print(f"   Time class: 'time' with data-unix attribute: {data_unix}")

    # Format (BO1, BO3, BO5)
    format_elem = soup.find("div", class_="padding preformatted-text")
    if format_elem:
        print(f"   Format class: 'padding preformatted-text'")
        print(f"     Format: {format_elem.get_text(strip=True)}")

    print("\n2. MAP RESULTS:")

    # Maps container
    maps_holder = soup.find("div", class_="mapholder")
    if maps_holder:
        print("   Maps holder class: 'mapholder'")

    # Individual maps
    map_boxes = soup.find_all("div", class_="mapholder")
    print(f"   Found {len(map_boxes)} map holders")

    for i, map_box in enumerate(map_boxes[:3]):  # Limit to first 3
        print(f"\n   Map {i+1}:")

        # Map name
        map_name = map_box.find("div", class_="mapname")
        if map_name:
            print(f"     Map name class: 'mapname' -> {map_name.get_text(strip=True)}")

        # Results
        results = map_box.find("div", class_="results")
        if results:
            # Team scores
            team1_score = map_box.find("div", class_="results-left")
            team2_score = map_box.find("div", class_="results-right") or map_box.find("span", class_="results-right")
            if team1_score:
                print(f"     Team 1 score class: 'results-left' -> {team1_score.get_text(strip=True)}")

            result_spans = results.find_all("span")
            for span in result_spans:
                classes = span.get("class", [])
                text = span.get_text(strip=True)
                if text:
                    print(f"     Score span classes: {classes} -> {text}")

    # Pick/ban info (veto)
    print("\n3. VETO/PICK-BAN:")
    veto = soup.find("div", class_="veto-box")
    if veto:
        print("   Veto box class: 'veto-box'")
        veto_items = veto.find_all("div")
        for item in veto_items[:6]:
            text = item.get_text(strip=True)
            if text and len(text) < 100:
                print(f"     {text}")

    print("\n4. PLAYER STATISTICS:")

    # Stats table
    stats_tables = soup.find_all("table", class_="stats-table")
    print(f"   Stats table class: 'stats-table' (found {len(stats_tables)})")

    # Also check for totalstats
    total_stats = soup.find("table", class_="totalstats")
    if total_stats:
        print("   Also found: 'totalstats' table")

    if stats_tables:
        table = stats_tables[0]

        # Headers
        headers = table.find_all("th")
        header_texts = [h.get_text(strip=True) for h in headers]
        print(f"   Table headers: {header_texts}")

        # Player rows
        tbody = table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            print(f"   Player rows in tbody: {len(rows)}")

            if rows:
                row = rows[0]
                cells = row.find_all("td")
                print(f"\n   First player row analysis:")

                # Player info cell
                player_cell = cells[0] if cells else None
                if player_cell:
                    player_link = player_cell.find("a")
                    if player_link:
                        print(f"     Player link href: {player_link.get('href')}")
                        player_name = player_link.get_text(strip=True)
                        print(f"     Player name: {player_name}")

                # Stats cells
                for i, cell in enumerate(cells[1:], 1):
                    stat_val = cell.get_text(strip=True)
                    cell_class = cell.get("class", [])
                    if i <= 8:  # First 8 stat columns
                        print(f"     Cell {i}: '{stat_val}' (classes: {cell_class})")

    # Check for per-map stats
    print("\n5. PER-MAP STATS:")
    map_stats_containers = soup.find_all("div", class_="stats-content")
    print(f"   Stats content containers: {len(map_stats_containers)}")

    # Look for map tabs/selectors
    map_tabs = soup.find_all("div", class_="stats-menu-link")
    if map_tabs:
        print(f"   Map tab class: 'stats-menu-link'")
        for tab in map_tabs[:5]:
            print(f"     Tab: {tab.get_text(strip=True)}")

    return soup, page


def generate_xpath_selectors():
    """Generate XPath selectors based on analysis."""
    print("\n" + "="*80)
    print("GENERATED XPATH SELECTORS")
    print("="*80)

    selectors = {
        "Results Page": {
            "date_sections": "//div[@class='results-sublist']",
            "date_headline": ".//div[@class='standard-headline']/text()",
            "match_containers": ".//div[@class='result-con']",
            "match_link": ".//a[@class='a-reset']/@href",
            "team_names": ".//div[@class='team']/text()",
            "scores": ".//td[@class='result-score']//span/text()",
            "event_name": ".//span[@class='event-name']/text()",
            "map_format": ".//div[@class='map-text']/text()",
            "pagination_next": "//a[@class='pagination-next']/@href",
        },
        "Match Page": {
            "team1_name": "//div[@class='teamName'][1]/text()",
            "team2_name": "//div[@class='teamName'][2]/text()",
            "team1_link": "(//div[contains(@class,'team1-gradient')]//a)[1]/@href",
            "team2_link": "(//div[contains(@class,'team2-gradient')]//a)[1]/@href",
            "event_name": "//a[@class='event']//div[@class='event-name']/text()",
            "event_link": "//a[@class='event']/@href",
            "date": "//div[@class='date']/text()",
            "time_unix": "//div[@class='time']/@data-unix",
            "format": "//div[@class='padding preformatted-text']/text()",
            "final_scores": "//div[contains(@class,'won') or contains(@class,'lost')]/text()",
        },
        "Map Results": {
            "map_holders": "//div[@class='mapholder']",
            "map_name": ".//div[@class='mapname']/text()",
            "team1_map_score": ".//div[@class='results-left']//span[@class='won' or @class='lost']/text()",
            "team2_map_score": ".//div[@class='results-right']//span[@class='won' or @class='lost']/text()",
        },
        "Veto": {
            "veto_box": "//div[@class='veto-box']",
            "veto_entries": ".//div/text()",
        },
        "Player Stats": {
            "stats_tables": "//table[@class='stats-table']",
            "player_rows": ".//tbody/tr",
            "player_link": ".//td[1]//a/@href",
            "player_name": ".//td[1]//a/text()",
            "player_country_flag": ".//td[1]//img/@src",
            "kills_deaths": ".//td[@class='kd']/text()",
            "adr": ".//td[@class='adr']/text()",
            "kast": ".//td[@class='kast']/text()",
            "rating": ".//td[@class='rating']/text()",
        }
    }

    print("\n```python")
    print("# XPath selectors for match scraping")
    print("class Matches:")
    for section, paths in selectors.items():
        print(f"\n    class {section.replace(' ', '')}:")
        for name, xpath in paths.items():
            print(f'        {name} = "{xpath}"')
    print("```")

    return selectors


if __name__ == "__main__":
    print("HLTV Match Page Structure Analysis")
    print("="*80)

    try:
        analyze_results_page()
        analyze_match_page()
        generate_xpath_selectors()
        print("\n✓ Analysis complete!")
    except Exception as e:
        print(f"\n✗ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
