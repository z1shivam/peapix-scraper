import os
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin
import re

peapix_bing_url = "https://peapix.com/bing"
peapix_spotlight_url = "https://peapix.com/spotlight"
home_dir = str(Path.home())

wallpaper_dir = os.path.join(home_dir, "Pictures", "wallpapers")
bing_meta_file = os.path.join(wallpaper_dir, "bing_data.json")
spotlight_meta_file = os.path.join(wallpaper_dir, "spotlight_data.json")


def load_json_metadata(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json_metadata(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_existing_ids(metadata_list):
    return {item["id"] for item in metadata_list}


def scrape_bing_item(item_soup, main_link, wallpapers_dir, headers):
    item_id = main_link.split("/")[-1]
    page_link = urljoin("https://peapix.com", main_link)

    item_response = requests.get(page_link, headers=headers)
    item_response.raise_for_status()
    item_soup = BeautifulSoup(item_response.text, "html.parser")

    title = item_soup.select_one("h1.fs-4.fw-bold").text.strip()
    copyright = item_soup.select_one("p.text-body-secondary.fs-sm").text.strip()
    description = " ".join(
        [p.text.strip() for p in item_soup.select("div.position-relative p")]
    ).strip()
    date = item_soup.select_one("time")["datetime"]
    tags = [
        tag.text.strip() for tag in item_soup.select("div.tag-list a.tag-list__item")
    ]

    img_tag = item_soup.select_one("div.position-relative.shadow-md.mb-4 img.img-fluid")
    thumbnail_url = img_tag["src"]
    full_image_url = re.sub(r"_480\.jpg$", ".jpg", thumbnail_url)

    return {
        "id": item_id,
        "title": title,
        "copyright_owner": copyright,
        "description": description,
        "tags": tags,
        "date": date,
        "download_link": full_image_url,
        "page_link": page_link,
        "thumbnail_url": thumbnail_url,
    }


def scrape_spotlight_item(item_soup, main_link):
    item_id = main_link.split("/")[-2] + "+" + main_link.split("/")[-1]
    page_link = urljoin("https://peapix.com", main_link)

    title = item_soup.select_one("h1.fs-4.fw-bold").text.strip()
    copyright = item_soup.select_one("p.text-body-secondary.fs-sm").text.strip()
    description_elements = item_soup.select("div.position-relative.mb-4")
    description = (
        description_elements[1].text.strip() if len(description_elements) > 1 else ""
    )
    date = item_soup.select_one("time")["datetime"]
    tags = [
        tag.text.strip() for tag in item_soup.select("div.tag-list a.tag-list__item")
    ]

    img_tag = item_soup.select_one("div.position-relative.shadow-md.mb-4 img.img-fluid")
    thumbnail_url = img_tag["src"]
    full_image_url = re.sub(r"_480\.jpg$", ".jpg", thumbnail_url)

    return {
        "id": item_id,
        "title": title,
        "copyright_owner": copyright,
        "description": description,
        "tags": tags,
        "date": date,
        "download_link": full_image_url,
        "page_link": page_link,
        "thumbnail_url": thumbnail_url,
    }


def scrape_spotlight_page(page):
    if page > 1:
        url += f"?page={page}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    metadata_list = load_json_metadata(spotlight_meta_file)
    existing_ids = get_existing_ids(metadata_list)

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    spotlight_items = soup.select("div.row.gx-5.gy-9 > div.col-md-6.col-lg-4")

    wallpapers_dir = os.path.join(home_dir, "Pictures", "wallpapers", "spotlight")
    os.makedirs(wallpapers_dir, exist_ok=True)

    for item in spotlight_items:
        main_link = item.select_one("a.d-block")["href"]
        item_id = main_link.split("/")[-2] + "+" + main_link.split("/")[-1]

        if item_id in existing_ids:
            print(f"item {item_id} already exist. skipping.")
            continue

        print(f"scraping {item_id}")
        page_link = urljoin("https://peapix.com", main_link)
        item_response = requests.get(page_link, headers=headers)
        item_response.raise_for_status()
        item_soup = BeautifulSoup(item_response.text, "html.parser")

        metadata = scrape_spotlight_item(item_soup, main_link, wallpapers_dir, headers)
        metadata_list.append(metadata)

    if metadata_list:
        save_json_metadata(spotlight_meta_file, metadata_list)

    return metadata_list


def scrape_bing_page(page):
    if page > 1:
        peapix_bing_url + f"?page={page}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    metadata_list = load_json_metadata(bing_meta_file)
    existing_ids = get_existing_ids(metadata_list)

    response = requests.get(peapix_bing_url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    bing_items = soup.select("div.row.gx-5.gy-9 > div.col-md-6.col-lg-4")

    wallpapers_dir = os.path.join(home_dir, "Pictures", "wallpapers", "bing")
    os.makedirs(wallpapers_dir, exist_ok=True)

    for item in bing_items:
        main_link = item.select_one("a.d-block")["href"]
        item_id = main_link.split("/")[-1]

        if item_id in existing_ids:
            print(f"Page ID {item_id} already scraped. Skipping!")
            continue

        print(f"scraping {item_id}")
        metadata = scrape_bing_item(soup, main_link, wallpapers_dir, headers)
        metadata_list.append(metadata)

    if metadata_list:
        save_json_metadata(bing_meta_file, metadata_list)

    return metadata_list


def download_image(url, local_path, headers):
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    with open(local_path, "wb") as f:
        f.write(response.content)


def download_all_walls(site_type):
    metadata_list, specific_dir
    
    if site_type == "bing":
        metadata_list = load_json_metadata(bing_meta_file)
        specific_dir = os.path.join(wallpaper_dir, "bing")
        os.makedirs(specific_dir, exist_ok=True)
    elif site_type =="spotlight":
        metadata_list = load_json_metadata(spotlight_meta_file)
        specific_dir = os.path.join(wallpaper_dir, "spotlight")
        os.makedirs(specific_dir, exist_ok=True)
        
    if not metadata_list:
        print("No metadata found in spotlight_data.json")
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for item in metadata_list:
        local_path = os.path.join(wallpaper_dir, site_type, f"{item["id"]}.jpg")
        download_url = item["download_link"]

        if os.path.exists(local_path):
            print(f"Image already exists: {local_path}")
            continue

        try:
            print(f"Downloading: {item['title']} ({item['id']})")
            download_image(download_url, local_path, headers)
            print(f"Saved to: {local_path}")
        except Exception as e:
            print(f"Failed to download {item['title']} ({item['id']}): {e}")


if __name__ == "__main__":
    print("starting scraping")
    scrape_bing_page(1)
