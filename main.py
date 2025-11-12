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

    title_elem = soup.select_one("h1.fs-4.fw-bold")
    if not title_elem:
        raise ValueError(f"Title not found for {page_link}")
    title = title_elem.text.strip()

    copyright_elem = soup.select_one("p.text-body-secondary.fs-sm")
    copyright_ = copyright_elem.text.strip() if copyright_elem else ""

    description = " ".join(
        p.text.strip() for p in soup.select("div.position-relative p")
    ).strip()

    date_elem = soup.select_one("time")
    if not date_elem or "datetime" not in date_elem.attrs:
        raise ValueError(f"Date not found for {page_link}")
    date = str(date_elem["datetime"])

    tags = [tag.text.strip() for tag in soup.select("div.tag-list a.tag-list__item")]

    img = soup.select_one("div.position-relative.shadow-md.mb-4 img.img-fluid")
    if not img or "src" not in img.attrs:
        raise ValueError(f"Image not found for {page_link}")
    thumb = str(img["src"])
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

    title_elem = soup.select_one("h1.fs-4.fw-bold")
    if not title_elem:
        raise ValueError(f"Title not found for {page_link}")
    title = title_elem.text.strip()

    copyright_elem = soup.select_one("p.text-body-secondary.fs-sm")
    copyright_ = copyright_elem.text.strip() if copyright_elem else ""

    desc_blocks = soup.select("div.position-relative.mb-4")
    description = desc_blocks[1].text.strip() if len(desc_blocks) > 1 else ""

    date_elem = soup.select_one("time")
    if not date_elem or "datetime" not in date_elem.attrs:
        raise ValueError(f"Date not found for {page_link}")
    date = str(date_elem["datetime"])

    tags = [tag.text.strip() for tag in soup.select("div.tag-list a.tag-list__item")]

    img = soup.select_one("div.position-relative.shadow-md.mb-4 img.img-fluid")
    if not img or "src" not in img.attrs:
        raise ValueError(f"Image not found for {page_link}")
    thumb = str(img["src"])
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
            link_elem = item.select_one("a.d-block")
            if not link_elem or "href" not in link_elem.attrs:
                print(f"Warning: Link not found in item, skipping")
                continue
            link = str(link_elem["href"])

            item_id = (
                link.split("/")[-1]
                if site == "bing"
                else "+".join(link.split("/")[-2:])
            )
            if item_id in existing:
                print(f"Skipping {item_id} (already exists)")
                continue

            try:
                print(f"Scraping {item_id}")
                data = (
                    scrape_bing_item(link)
                    if site == "bing"
                    else scrape_spotlight_item(link)
                )
                all_data.append(data)
            except Exception as e:
                print(f"Error scraping {item_id}: {e}")

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
    while True:
        try:
            start = input(f"Start page for {name}: ").strip()
            start = int(start) if start else 1  # Default to 1 if empty
            if start < 1:
                raise ValueError("Start page must be 1 or greater")

            end = input(f"End page for {name}: ").strip()
            end = int(end) if end else start  # Default to start if empty
            if end < start:
                raise ValueError("End page must be greater than or equal to start page")

            return start, end
        except ValueError as e:
            if "must be" in str(e):
                print(f"Error: {e}")
            else:
                print("Error: Please enter valid integer numbers")
            print("Please try again.")


def main():
    scrape_page("bing", 1, 3)
    scrape_page("spotlight", 1, 3)
    download_images("bing")
    download_images("spotlight")


if __name__ == "__main__":
    main()
