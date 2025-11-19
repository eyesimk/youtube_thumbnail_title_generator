from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
from urllib.parse import quote_plus

QUERIES = [
    "ai", "tech", "coding", "productivity", "startups", "youtube tips", "devlog",'artificial intelligence', 'machine learning',
    'robotics ai','data science project',
    "ai tutorial", "ai tools", "ai explained",

    "coding tutorial", "python tutorial", "javascript beginners",

    "productivity tips", "study productivity", "deep work",

    "startup story", "startup advice", "founder vlog",

    "youtube thumbnail", "grow on youtube", "how to get views",

    "gamedev devlog", "indie devlog",
]

HEADLESS = False
SCROLL_TIMES = 25              # scroll times
SCROLL_PAUSE = 2               # scroll pause for cards to load
MAX_VIDEOS_PER_QUERY = 400     
OUT_CSV = "youtube_titles_thumbs_all_queries.csv"


def make_driver():
    options = webdriver.ChromeOptions()

    # incognito profile
    options.add_argument("--incognito")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")

    if HEADLESS:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def parse_views(text: str):
    """
    Converting numerical terms to int such as 12K, 20M
    """
    if not text:
        return None

    t = text.lower().replace("views", "").strip()
    t = t.replace(",", "")

    if "k" in t:
        try:
            return int(float(t.replace("k", "")) * 1_000)
        except ValueError:
            return None
    if "m" in t:
        try:
            return int(float(t.replace("m", "")) * 1_000_000)
        except ValueError:
            return None
    if "b" in t:
        try:
            return int(float(t.replace("b", "")) * 1_000_000_000)
        except ValueError:
            return None

    digits = "".join(ch for ch in t if ch.isdigit())
    return int(digits) if digits else None


def scrape_titles_and_thumbnails(query: str, max_videos: int):
    driver = make_driver()
    encoded = quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    print(f"\n=== Query: {query} ===")
    print(f"Opening: {url}")
    driver.get(url)
    time.sleep(3)

    body = driver.find_element(By.TAG_NAME, "body")

    # scroll to load
    for _ in range(SCROLL_TIMES):
        body.send_keys(Keys.END)
        time.sleep(SCROLL_PAUSE)

    # only long form videos
    video_cards = driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer")
    print(f"Found {len(video_cards)} video cards for '{query}'")

    rows = []

    for card in video_cards:
        if len(rows) >= max_videos:
            break

        try:

            title_el = card.find_element(By.CSS_SELECTOR, "a#video-title")
            title = title_el.get_attribute("title") or title_el.text
            video_url = title_el.get_attribute("href")


            if not video_url or "watch?v=" not in video_url:
                continue

            video_id = video_url.split("watch?v=")[-1].split("&")[0].strip()
            if not video_id:
                continue


            # scraping load date and view count
            meta_items = card.find_elements(By.CSS_SELECTOR, "span.inline-metadata-item")
            views_text = meta_items[0].text if len(meta_items) > 0 else ""
            age_text = meta_items[1].text if len(meta_items) > 1 else ""
            views_num = parse_views(views_text)

            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hq720.jpg"

            #printing to verify
            print('video url:' , video_url, 'view count:', views_num, 'load date:', age_text),

            rows.append({
                "search_query": query,
                "video_id": video_id,
                "title": title,
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "views_text": views_text,
                "views": views_num,
                "age_text": age_text,
            })

        except Exception:
            continue

    driver.quit()
    print(f"Collected {len(rows)} videos for query '{query}'")
    return rows


def save_csv(rows, path):
    if not rows:
        print("No rows scraped.")
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows to {path}")


if __name__ == "__main__":
    all_rows = []
    seen_ids = set()   

    for q in QUERIES:
        rows = scrape_titles_and_thumbnails(q, MAX_VIDEOS_PER_QUERY)
        for r in rows:
            vid = r["video_id"]
            if vid in seen_ids:
                continue
            seen_ids.add(vid)
            all_rows.append(r)

    print(f"\nTotal unique videos collected: {len(all_rows)}")
    save_csv(all_rows, OUT_CSV)
