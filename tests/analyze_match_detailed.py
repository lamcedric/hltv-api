"""
Detailed analysis of HLTV match page with player stats.
"""
import cloudscraper
from bs4 import BeautifulSoup
from lxml import etree
import re


def fetch_page(url: str) -> tuple[BeautifulSoup, etree._Element]:
    """Fetch page using cloudscraper."""
    scraper = cloudscraper.create_scraper()
    response = scraper.get(
        url=url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    soup = BeautifulSoup(response.content, "html.parser")
    page = etree.HTML(str(soup))
    return soup, page


def analyze_match_with_stats():
    """Analyze a match page that has player stats."""
    # Use a recent BO3 match with stats
    url = "https://www.hltv.org/matches/2388127/furia-vs-natus-vincere-starladder-budapest-major-2025"
    print(f"Analyzing: {url}\n")

    soup, page = fetch_page(url)

    # Save raw HTML for debugging
    with open("tests/match_page.html", "w") as f:
        f.write(str(soup))
    print("Saved raw HTML to tests/match_page.html\n")

    print("="*80)
    print("MATCH PAGE STRUCTURE")
    print("="*80)

    # 1. Team box analysis
    print("\n1. TEAM STRUCTURE:")
    team_boxes = soup.find_all("div", class_="team")
    print(f"   Found {len(team_boxes)} team divs")

    # Look for team1-gradient and team2-gradient
    team1 = soup.find("div", class_=lambda x: x and "team1-gradient" in x)
    team2 = soup.find("div", class_=lambda x: x and "team2-gradient" in x)

    if team1:
        team_name = team1.find("div", class_="teamName")
        team_logo = team1.find("img", class_="logo")
        team_link = team1.find("a")
        print(f"   Team 1:")
        print(f"     Name: {team_name.get_text(strip=True) if team_name else 'N/A'}")
        print(f"     Logo: {team_logo.get('src') if team_logo else 'N/A'}")
        print(f"     Link: {team_link.get('href') if team_link else 'N/A'}")

        # Score
        won = team1.find("div", class_="won")
        lost = team1.find("div", class_="lost")
        print(f"     Score (won): {won.get_text(strip=True) if won else 'N/A'}")
        print(f"     Score (lost): {lost.get_text(strip=True) if lost else 'N/A'}")

    if team2:
        team_name = team2.find("div", class_="teamName")
        team_link = team2.find("a")
        print(f"   Team 2:")
        print(f"     Name: {team_name.get_text(strip=True) if team_name else 'N/A'}")
        print(f"     Link: {team_link.get('href') if team_link else 'N/A'}")

        won = team2.find("div", class_="won")
        lost = team2.find("div", class_="lost")
        print(f"     Score (won): {won.get_text(strip=True) if won else 'N/A'}")
        print(f"     Score (lost): {lost.get_text(strip=True) if lost else 'N/A'}")

    # 2. Map results
    print("\n2. MAP RESULTS:")
    maps_holder = soup.find_all("div", class_="mapholder")
    print(f"   Found {len(maps_holder)} map holders")

    for i, mh in enumerate(maps_holder):
        print(f"\n   Map {i+1}:")
        map_name = mh.find("div", class_="mapname")
        print(f"     Map: {map_name.get_text(strip=True) if map_name else 'N/A'}")

        # Results
        results_left = mh.find("div", class_="results-left")
        results_right = mh.find("div", class_="results-right")

        if results_left:
            score = results_left.find("span", class_=lambda x: x and ("won" in x or "lost" in x))
            print(f"     Team 1 score: {score.get_text(strip=True) if score else 'N/A'}")

        if results_right:
            score = results_right.find("span", class_=lambda x: x and ("won" in x or "lost" in x))
            print(f"     Team 2 score: {score.get_text(strip=True) if score else 'N/A'}")

        # Half scores (CT/T)
        spans = mh.find_all("span")
        ct_scores = [s for s in spans if s.get("class") and "ct" in s.get("class")]
        t_scores = [s for s in spans if s.get("class") and "t" in s.get("class")]
        if ct_scores:
            print(f"     CT scores: {[s.get_text(strip=True) for s in ct_scores]}")
        if t_scores:
            print(f"     T scores: {[s.get_text(strip=True) for s in t_scores]}")

    # 3. Player stats
    print("\n3. PLAYER STATISTICS:")

    # Look for stats-content div
    stats_content = soup.find_all("div", class_="stats-content")
    print(f"   Stats content divs: {len(stats_content)}")

    # Look for stats table
    stats_tables = soup.find_all("table", class_="stats-table")
    totalstats_tables = soup.find_all("table", class_="totalstats")

    print(f"   stats-table count: {len(stats_tables)}")
    print(f"   totalstats count: {len(totalstats_tables)}")

    # Try the totalstats table
    if totalstats_tables:
        table = totalstats_tables[0]
        print("\n   Analyzing totalstats table:")

        # Headers
        header_row = table.find("tr", class_="header-row")
        if header_row:
            headers = header_row.find_all("th")
            print(f"     Headers: {[h.get_text(strip=True) for h in headers]}")

        # Player rows
        tbody = table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            print(f"     Player rows: {len(rows)}")

            for row in rows[:2]:  # First 2 players
                tds = row.find_all("td")
                print(f"\n     Row with {len(tds)} cells:")

                # Player info (first cell)
                if tds:
                    player_cell = tds[0]
                    player_link = player_cell.find("a")
                    player_flag = player_cell.find("img", class_="flag")
                    player_name = player_cell.find("div", class_="player-nick")

                    print(f"       Player link: {player_link.get('href') if player_link else 'N/A'}")
                    print(f"       Player name: {player_name.get_text(strip=True) if player_name else 'N/A'}")
                    print(f"       Flag: {player_flag.get('title') if player_flag else 'N/A'}")

                # Stats (remaining cells)
                for j, td in enumerate(tds[1:], 1):
                    text = td.get_text(strip=True)
                    classes = td.get("class", [])
                    if text:
                        print(f"       Cell {j}: {text} (classes: {classes})")

    # 4. Event info
    print("\n4. EVENT INFO:")
    event_anchor = soup.find("a", class_="event")
    if event_anchor:
        print(f"   Event link: {event_anchor.get('href')}")
        event_name_div = event_anchor.find("div", class_="event-name")
        print(f"   Event name: {event_name_div.get_text(strip=True) if event_name_div else 'N/A'}")

    # 5. Match format and date
    print("\n5. MATCH META:")
    time_and_event = soup.find("div", class_="timeAndEvent")
    if time_and_event:
        date_div = time_and_event.find("div", class_="date")
        time_div = time_and_event.find("div", class_="time")
        print(f"   Date: {date_div.get_text(strip=True) if date_div else 'N/A'}")
        print(f"   Time data-unix: {time_div.get('data-unix') if time_div else 'N/A'}")

    # Format
    preformatted = soup.find("div", class_="preformatted-text")
    if preformatted:
        print(f"   Format: {preformatted.get_text(strip=True)}")

    # 6. Veto
    print("\n6. VETO/PICKS:")
    veto_box = soup.find("div", class_="veto-box")
    if veto_box:
        veto_divs = veto_box.find_all("div", recursive=False)
        for v in veto_divs[:8]:
            text = v.get_text(strip=True)
            if text and len(text) < 100:
                print(f"   {text}")

    # Generate XPath selectors
    print("\n" + "="*80)
    print("RECOMMENDED XPATH SELECTORS")
    print("="*80)

    print("""
class Matches:
    class ResultsPage:
        date_sections = "//div[@class='results-sublist']"
        date_headline = ".//div[contains(@class,'standard-headline')]/text()"
        match_containers = ".//div[contains(@class,'result-con')]"
        match_link = ".//a[@class='a-reset']/@href"
        team1_name = ".//div[@class='team'][1]//text()"
        team2_name = ".//div[@class='team'][2]//text()"
        team1_score = ".//td[contains(@class,'result-score')]//span[1]/text()"
        team2_score = ".//td[contains(@class,'result-score')]//span[2]/text()"
        event_name = ".//span[@class='event-name']/text()"
        match_format = ".//div[@class='map-text']/text()"
        pagination_next = "//a[contains(@class,'pagination-next')]/@href"

    class MatchPage:
        # Team info
        team1_name = "//div[contains(@class,'team1-gradient')]//div[@class='teamName']/text()"
        team2_name = "//div[contains(@class,'team2-gradient')]//div[@class='teamName']/text()"
        team1_link = "//div[contains(@class,'team1-gradient')]//a/@href"
        team2_link = "//div[contains(@class,'team2-gradient')]//a/@href"
        team1_logo = "//div[contains(@class,'team1-gradient')]//img[contains(@class,'logo')]/@src"
        team2_logo = "//div[contains(@class,'team2-gradient')]//img[contains(@class,'logo')]/@src"
        team1_score_won = "//div[contains(@class,'team1-gradient')]//div[@class='won']/text()"
        team1_score_lost = "//div[contains(@class,'team1-gradient')]//div[@class='lost']/text()"
        team2_score_won = "//div[contains(@class,'team2-gradient')]//div[@class='won']/text()"
        team2_score_lost = "//div[contains(@class,'team2-gradient')]//div[@class='lost']/text()"

        # Event info
        event_link = "//a[@class='event']/@href"
        event_name = "//a[@class='event']//div[contains(@class,'event-name')]/text()"

        # Date/time
        date = "//div[@class='timeAndEvent']//div[@class='date']/text()"
        time_unix = "//div[@class='timeAndEvent']//div[@class='time']/@data-unix"
        match_format = "//div[contains(@class,'preformatted-text')]/text()"

        # Map holders
        map_holders = "//div[@class='mapholder']"

    class MapResults:
        # Per map (use relative from map_holder)
        map_name = ".//div[@class='mapname']/text()"
        team1_score = ".//div[@class='results-left']//span[contains(@class,'won') or contains(@class,'lost')]/text()"
        team2_score = ".//div[@class='results-right']//span[contains(@class,'won') or contains(@class,'lost')]/text()"
        team1_ct_score = ".//div[@class='results-left']//span[@class='ct']/text()"
        team1_t_score = ".//div[@class='results-left']//span[@class='t']/text()"
        team2_ct_score = ".//div[@class='results-right']//span[@class='ct']/text()"
        team2_t_score = ".//div[@class='results-right']//span[@class='t']/text()"

    class PlayerStats:
        # Stats table (totalstats)
        stats_table = "//table[contains(@class,'totalstats')]"
        player_rows = ".//tbody/tr"

        # Per player row (relative)
        player_link = ".//td[1]//a/@href"
        player_name = ".//td[1]//div[contains(@class,'player-nick')]/text()"
        player_flag = ".//td[1]//img[contains(@class,'flag')]/@title"

        # Stats cells - positions vary by table type
        # Check actual cell classes: kd, adr, kast, rating
        kd = ".//td[contains(@class,'kd')]/text()"
        adr = ".//td[contains(@class,'adr')]/text()"
        kast = ".//td[contains(@class,'kast')]/text()"
        rating = ".//td[contains(@class,'rating')]/text()"

    class Veto:
        veto_box = "//div[@class='veto-box']"
        veto_lines = ".//div[contains(@class,'padding')]/text()"
""")


if __name__ == "__main__":
    analyze_match_with_stats()
