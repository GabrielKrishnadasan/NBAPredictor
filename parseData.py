import os
import pandas as pd
from bs4 import BeautifulSoup

SCORE_DIR = "data/scores"

#Links variable to directory
box_scores = os.listdir(SCORE_DIR)
box_scores = [os.path.join(SCORE_DIR, f) for f in box_scores if f.endswith(".html")]

def parse_html(box_score):
    with open(box_score) as f:
        html = f.read()

    soup =  BeautifulSoup(html, features="lxml")

    #removed useless html
    [s.decompose() for s in soup.select("tr.over_header")]
    [s.decompose() for s in soup.select("tr.thead")]
    return soup

#Gets the score of each game, as well as the score at the end of each quarter
def read_line_score(soup):
    line_score = pd.read_html(str(soup), attrs={"id": "line_score"})[0]
    cols = list(line_score.columns)
    cols[0] = "team"
    cols[-1] = "total"
    line_score.columns = cols
    line_score = line_score[["team", "total"]]
    return line_score

#gets the stats from a selected game, either basic or advanced stats
def read_stats(soup, team, stat):
    df = pd.read_html(str(soup), attrs={"id": f"box-{team}-game-{stat}"}, index_col = 0)[0]
    df = df.apply(pd.to_numeric, errors="coerce")
    return df

#Gets the season the game was played
def read_season_info(soup):
    nav = soup.select("#bottom_nav_container")[0]
    hrefs = [a["href"] for a in nav.find_all("a")]
    season = os.path.basename(hrefs[1]).split("_")[0]
    return season

base_cols = None
games = []

#Goes through every box score html and appends the relevent info to games
for box_score in box_scores:
    soup = parse_html(box_score)
    line_score = read_line_score(soup)
    teams = list(line_score["team"])

    summaries = []
    for team in teams:
        #Gets both basic and advanced stats
        basic = read_stats(soup, team, "basic")
        adv = read_stats(soup, team, "advanced")
        
        total = pd.concat([basic.iloc[-1,:], adv.iloc[-1,:]])
        total.index = total.index.str.lower()

        maxes = pd.concat([basic.iloc[:-1,:].max(), adv.iloc[:-1,:].max()])
        maxes.index = maxes.index.str.lower() + "_max"

        summary = pd.concat([total, maxes])

        if not base_cols:
            base_cols = list(summary.index.drop_duplicates(keep="first"))
            for b in base_cols:
                if "bpm" in b:
                    base_cols.remove(b)

        sumamry = summary[base_cols]

        summaries.append(sumamry)

    summary = pd.concat(summaries, axis=1).T

    game = pd.concat([summary, line_score], axis=1)

    game["home"] = [0, 1]
    game_opp = game.iloc[::-1].reset_index()
    game_opp.columns += "_opp"

    full_game = pd.concat([game, game_opp], axis=1)

    full_game["season"] = read_season_info(soup)
    full_game["date"] = os.path.basename(box_score)[:8]
    full_game["date"] = pd.to_datetime(full_game["date"], format="%Y%m%d")

    #Make a column to show who won the game
    full_game["won"] = full_game["total"] > full_game["total_opp"]
    games.append(full_game)

    #print statement to see progress
    if len(games) % 100 == 0:
        print(f"{len(games)} / {len(box_scores)}")

#Writes all info to a csv, later to be converted to a df in predict
games_df = pd.concat(games, ignore_index=True)
games_df.to_csv("nba_games.csv")
