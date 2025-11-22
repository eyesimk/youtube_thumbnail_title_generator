import os
import time
import requests
import pandas as pd
from tqdm import tqdm

CSV_PATH = "youtube_titles_thumbs_all_queries.csv"
OUT_DIR = "thumbnails"
TIMEOUT = 10         # seconds per request
SLEEP = 0.05         # short pause between downloads 


def safe_filename(video_id: str) -> str:
    return "".join(c for c in video_id if c.isalnum() or c in ("-", "_"))


def download_image(url: str, out_path: str) -> bool:
    
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code != 200:
            return False

        with open(out_path, "wb") as f:
            f.write(resp.content)

        return True
    except Exception:
        return False


def main():
    # make sure output folder exists
    os.makedirs(OUT_DIR, exist_ok=True)

    # read CSV
    df = pd.read_csv(CSV_PATH)

    # basic column check
    if "video_id" not in df.columns or "thumbnail_url" not in df.columns:
        print("CSV must contain 'video_id' and 'thumbnail_url' columns.")
        return

    success, fail, skipped = 0, 0, 0

    # iterate with progress bar
    for row in tqdm(df.itertuples(), total=len(df), desc="Downloading thumbnails"):
        vid = str(row.video_id)
        url = str(row.thumbnail_url)

        if not url or not isinstance(url, str):
            fail += 1
            continue

        fname = safe_filename(vid) + ".jpg"
        out_path = os.path.join(OUT_DIR, fname)

        # skip if already exists
        if os.path.exists(out_path):
            skipped += 1
            continue

        if download_image(url, out_path):
            success += 1
        else:
            fail += 1

        time.sleep(SLEEP)

    print(f"\nDownloaded: {success}")
    print(f"Failed:     {fail}")
    print(f"Skipped:    {skipped} (already existed)")


if __name__ == "__main__":
    main()
