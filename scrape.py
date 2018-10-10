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
    rows[0].decompose()
    rows[1].decompose()
    rows[len(rows)-1].decompose()

    # Removes unnecessary columns
    [x.decompose() for x in history.find_all('td', {'class': 'stats'})]
    rows = history.find_all('tr')

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
        blue_bans = columns[5].contents[0].replace("\n", "").split(", ")
        red_bans = columns[6].contents[0].replace("\n", "").split(", ")

        # get picks
        blue_picks = columns[7].contents[0].replace("\n", "").split(", ")
        red_picks = columns[8].contents[0].replace("\n", "").split(", ")

        # get players
        blue_players_tags = columns[9].find_all('a')
        red_players_tags = columns[10].find_all('a')
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
            'url': "Riot Match History Page could not be found." if columns[12].find('a') is None else columns[12].find('a').get('href').strip()
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

scrape_tournament_history("https://lol.gamepedia.com/Special:RunQuery/MatchHistoryTournament?MHT%5Btournament%5D=Concept:NA%20Regional%20Finals%202018&MHT%5Btext%5D=Yes&pfRunQueryFormName=MatchHistoryTournament", "NALCS Regionals 2018")
