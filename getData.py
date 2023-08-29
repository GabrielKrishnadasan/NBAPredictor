import os
import asyncio
import tracemalloc
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time

#Added to prevent error message
tracemalloc.start()

#Seasons that I wanted to test for
SEASONS = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]

#Linking directories to a variable
DATA_DIR = "data"
STANDINGS_DIR = os.path.join(DATA_DIR, "standings")
SCORES_DIR = os.path.join(DATA_DIR, "scores")

#Gets the html file of selected url
def get_html(url, selector, sleep=5):
    html = None
    i = 0
    while not html:
        #Prevent scraping too quick, could get banned, sleep longer each retry
        time.sleep(sleep * i)
        try:
            with sync_playwright() as p:
                #Alternate browser between firefox and chrome (Maybe will help with timeout errors?)
                if i % 2 == 0:
                    browser = p.firefox.launch()
                else:
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
        i += 1
    return html

#Calls get_html for a whole NBA season
def scrapeSeason(year):   
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_games.html"
    html = get_html(url, "#content .filter")

    soup = BeautifulSoup(html, features="lxml")
    links = soup.find_all("a")
    href = []
    for l in links:
        href.append(l["href"])

    standings_pages = []
    for l in href:
        standings_pages.append(f"https://www.basketball-reference.com{l}")

    for link in standings_pages:
        save_path = os.path.join(STANDINGS_DIR, link.split("/")[-1])
        if os.path.exists(save_path):
            continue

        html = get_html(link, "#all_schedule")
        with open(save_path, "w+") as f:
            f.write(html)

#Takes a selected game and scraped the html box score for that game
def scrape_game(standings_file):
    with open(standings_file, 'r') as f:
        html = f.read()

    soup = BeautifulSoup(html, features="lxml")
    links = soup.find_all("a")
    href = []
    for l in links:
        href.append(l.get("href"))
    box_scores = []

    for l in href:
        if l and "boxscore" in l and ".html" in l:
            box_scores.append(f"https://basketball-reference.com{l}")

    for l in box_scores:
        save_path = os.path.join(SCORES_DIR, l.split("/")[-1])
        if os.path.exists(save_path):
            continue

        html = get_html(l, "#content")
        if not html:
            continue
        with open(save_path, "w+") as f:
            f.write(html)
    
standings_files = os.listdir(STANDINGS_DIR)

#Loop to scrape all the games
for f in standings_files:
    filepath = os.path.join(STANDINGS_DIR, f)
    scrape_game(filepath)