import os
import asyncio
import tracemalloc
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time

tracemalloc.start()

SEASONS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]

DATA_DIR = "data"
STANDINGS_DIR = os.path.join(DATA_DIR, "standings")
SCORES_DIR = os.path.join(DATA_DIR, "scores")

def get_html(url, selector, sleep=5, retries=3):
    html = None
    for i in range(1,retries + 1):
        #Prevent scraping too quick, could get banned, sleep longer each retry
        time.sleep(sleep * i)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url)
                print(page.title())
                html = page.inner_html(selector)
        except PlaywrightTimeout:
            print(f"Timeout error on {url}")
            continue
        else:
            break
    return html

def main():   
    season = 2016
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_games.html"
    html = get_html(url, "#content .filter")
    print(html)
    
main()

