import json
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://peapix.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
}
HOME_DIR = Path.home()
WALLPAPER_DIR = HOME_DIR / "Pictures" / "wallpapers"
BING_META_FILE = WALLPAPER_DIR / "bing_data.json"
SPOTLIGHT_META_FILE = WALLPAPER_DIR / "spotlight_data.json"


def load_json(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def get_existing_ids(data):
    return {item["id"] for item in data}


def scrape_bing_item(link):
    item_id = link.split("/")[-1]
    page_link = urljoin(BASE_URL, link)
    soup = BeautifulSoup(requests.get(page_link, headers=HEADERS).text, "html.parser")

    title = soup.select_one("h1.fs-4.fw-bold").text.strip()
    copyright_ = soup.select_one("p.text-body-secondary.fs-sm").text.strip()
    description = " ".join(p.text.strip() for p in soup.select("div.position-relative p")).strip()
    date = soup.select_one("time")["datetime"]
    tags = [tag.text.strip() for tag in soup.select("div.tag-list a.tag-list__item")]
    img = soup.select_one("div.position-relative.shadow-md.mb-4 img.img-fluid")
    thumb = img["src"]
    full_img = re.sub(r"_480\.jpg$", ".jpg", thumb)

    return {
        "id": item_id,
        "title": title,
        "copyright_owner": copyright_,
        "description": description,
        "tags": tags,
        "date": date,
        "download_link": full_img,
        "page_link": page_link,
        "thumbnail_url": thumb,
    }


def scrape_spotlight_item(link):
    item_id = "+".join(link.split("/")[-2:])
    page_link = urljoin(BASE_URL, link)
    soup = BeautifulSoup(requests.get(page_link, headers=HEADERS).text, "html.parser")

    title = soup.select_one("h1.fs-4.fw-bold").text.strip()
    copyright_ = soup.select_one("p.text-body-secondary.fs-sm").text.strip()
    desc_blocks = soup.select("div.position-relative.mb-4")
    description = desc_blocks[1].text.strip() if len(desc_blocks) > 1 else ""
    date = soup.select_one("time")["datetime"]
    tags = [tag.text.strip() for tag in soup.select("div.tag-list a.tag-list__item")]
    img = soup.select_one("div.position-relative.shadow-md.mb-4 img.img-fluid")
    thumb = img["src"]
    full_img = re.sub(r"_480\.jpg$", ".jpg", thumb)

    return {
        "id": item_id,
        "title": title,
        "copyright_owner": copyright_,
        "description": description,
        "tags": tags,
        "date": date,
        "download_link": full_img,
        "page_link": page_link,
        "thumbnail_url": thumb,
    }


def scrape_page(site, start_page, end_page):
    base_url = f"{BASE_URL}/{site}"
    meta_file = BING_META_FILE if site == "bing" else SPOTLIGHT_META_FILE
    existing = get_existing_ids(load_json(meta_file))
    all_data = load_json(meta_file)
    save_dir = WALLPAPER_DIR / site
    save_dir.mkdir(parents=True, exist_ok=True)

    for page in range(start_page, end_page + 1):
        url = base_url + (f"?page={page}" if page > 1 else "")
        soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")
        items = soup.select("div.row.gx-5.gy-9 > div.col-md-6.col-lg-4")

        for item in items:
            link = item.select_one("a.d-block")["href"]
            item_id = link.split("/")[-1] if site == "bing" else "+".join(link.split("/")[-2:])
            if item_id in existing:
                print(f"Skipping {item_id} (already exists)")
                continue

            print(f"Scraping {item_id}")
            data = scrape_bing_item(link) if site == "bing" else scrape_spotlight_item(link)
            all_data.append(data)

    if all_data:
        save_json(meta_file, all_data)


def download_images(site):
    meta_file = BING_META_FILE if site == "bing" else SPOTLIGHT_META_FILE
    data = load_json(meta_file)
    save_dir = WALLPAPER_DIR / site
    save_dir.mkdir(parents=True, exist_ok=True)

    for item in data:
        filename = save_dir / f"{item['id']}.jpg"
        if filename.exists():
            print(f"Exists: {filename}")
            continue

        try:
            print(f"Downloading: {item['title']} ({item['id']})")
            res = requests.get(item["download_link"], headers=HEADERS)
            res.raise_for_status()
            filename.write_bytes(res.content)
            print(f"Saved: {filename}")
        except Exception as e:
            print(f"Error downloading {item['id']}: {e}")


def prompt_bool(prompt, default=True):
    val = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if not val:
        return default
    return val in {"y", "yes"}


def prompt_range(name):
    start = int(input(f"Start page for {name}: ").strip())
    end = int(input(f"End page for {name}: ").strip())
    return start, end


def main():
    if prompt_bool("Do you want to scrape Bing?", True):
        start, end = prompt_range("Bing")
        scrape_page("bing", start, end)

    if prompt_bool("Do you want to scrape Spotlight?", True):
        start, end = prompt_range("Spotlight")
        scrape_page("spotlight", start, end)

    if prompt_bool("Do you want to download images?", True):
        if prompt_bool("Download Bing images?", True):
            download_images("bing")
        if prompt_bool("Download Spotlight images?", True):
            download_images("spotlight")


if __name__ == "__main__":
    main()
