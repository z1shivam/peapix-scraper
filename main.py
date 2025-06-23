import argparse

def main():
    parser = argparse.ArgumentParser(description="Arguments for scraping peapix website for images")
    parser.add_argument('-b', '--bing', action='store_true', help='Scrape Bing Enabled. (default: False)')
    parser.add_argument('-s', '--spotlight', action='store_true', help='Scrape Spotlight Enabled. (default: False)')
    parser.add_argument('-d', '--download-image', action='store_true', help='Downloading of image enabled. (default: False)')
    args = parser.parse_args()
        

if __name__=="__main__":
    main()