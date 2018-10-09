# -*- coding: utf-8 -*-

# import libraries
import requests
from bs4 import BeautifulSoup

def load_page(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    return soup

def scrape_tournament_history(url, tournament):
    soup = load_page(url)

    history = soup.find('table', {'class': 'wikitable'})

    # Removes table and column header rows
    rows = history.find_all('tr')
    for x in range(0, 3):
        rows[x].extract()

    # Removes images and unnecessary columns
    [x.decompose() for x in history.find_all('img')]
    [x.decompose() for x in history.find_all('td', {'class': 'stats'})]
    rows = history.find_all('tr')
    for x in range(0, len(rows)):
        columns = rows[x].find_all('td')
        columns[12].extract()
        columns[10].extract()

    # Order from least to most recent
    rows.reverse()

    # Scrapes data and stores match data in array
    matches = []
    for x in range(0, len(rows)):
        columns = rows[x].find_all('td')

        # gets game number if in a series
        game = 1
        if len(matches) > 0:
            prev_blue = matches[len(matches)-1]['blue_team']
            prev_red = matches[len(matches)-1]['red_team']
            curr_blue = columns[2].find('a').get('title').strip()
            curr_red = columns[3].find('a').get('title').strip()

            if (prev_blue in (curr_red, curr_blue)) & (prev_red in (curr_red, curr_blue)):
                game = matches[len(matches)-1]['game'] + 1

        # get bans
        blue_bans_tags = columns[4].span.find_all('a')
        red_bans_tags = columns[5].span.find_all('a')
        blue_bans = []
        red_bans = []
        for y in range(0, len(blue_bans_tags)):
            blue_bans.insert(len(blue_bans), blue_bans_tags[y].get('title').strip())
            red_bans.insert(len(red_bans), red_bans_tags[y].get('title').strip())

        # get picks
        blue_picks_tags = columns[6].span.find_all('a')
        red_picks_tags = columns[7].span.find_all('a')
        blue_picks = []
        red_picks = []
        for y in range(0, len(blue_picks_tags)):
            blue_picks.insert(len(blue_picks), blue_picks_tags[y].get('title').strip())
            red_picks.insert(len(red_picks), red_picks_tags[y].get('title').strip())

        # get players
        blue_players_tags = columns[8].span.find_all('a')
        red_players_tags = columns[9].span.find_all('a')
        blue_players = []
        red_players = []
        for y in range(0, len(blue_players_tags)):
            blue_players.insert(len(blue_players), blue_players_tags[y].contents[0].strip())
            red_players.insert(len(red_players), red_players_tags[y].contents[0].strip())

        data = {
            'date': columns[0].get_text().replace('\n', '').strip(),
            'patch': columns[1].get_text().replace('\n', '').strip(),
            'tournament': tournament,
            'game': game,
            'blue_team': columns[2].find('a').get('title').strip(),
            'red_team': columns[3].find('a').get('title').strip(),
            'blue_bans': blue_bans,
            'red_bans': red_bans,
            'blue_picks': blue_picks,
            'red_picks': red_picks,
            'blue_players': blue_players,
            'red_players': red_players,
            'url': "Riot Match History Page could not be found." if columns[10].find('a') is None else columns[10].find('a').get('href').strip()
        }

        matches.insert(len(matches), data)

    for x in matches:
        print x['date'], x['patch'], x['tournament'], x['game'], x['blue_team'], x['red_team'], x['url'],
        # for y in range(0, 5): print x['blue_bans'][y],
        # for y in range(0, 5): print x['red_bans'][y],
        # for y in range(0, 5): print x['blue_picks'][y],
        # for y in range(0, 5): print x['red_picks'][y],
        # for y in range(0, 5): print x['blue_players'][y],
        # for y in range(0, 5): print x['red_players'][y],
        # print ""

    text_file = open('history.html', 'w')
    text_file.write(str(history))
    text_file.close()

scrape_tournament_history("https://lol.gamepedia.com/League_Championship_Series/North_America/2018_Season/Regional_Finals/Match_History", "NALCS Regionals 2018")
