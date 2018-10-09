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

        game = 1

        if len(matches) > 0:
            prev_blue = matches[len(matches)-1]['blue']
            prev_red = matches[len(matches)-1]['red']
            curr_blue = columns[2].find('a').get('title').strip()
            curr_red = columns[3].find('a').get('title').strip()

            if (prev_blue in (curr_red, curr_blue)) & (prev_red in (curr_red, curr_blue)):
                game = matches[len(matches)-1]['game'] + 1

        data = {
            'date': columns[0].get_text().replace('\n', '').strip(),
            'patch': columns[1].get_text().replace('\n', '').strip(),
            'tournament': tournament,
            'game': game,
            'blue': columns[2].find('a').get('title').strip(),
            'red': columns[3].find('a').get('title').strip(),
            'url': "Riot Match History Page could not be found." if columns[10].find('a') is None else columns[10].find('a').get('href').strip()
        }

        matches.insert(len(matches), data)

    for x in matches:
        print x['date'], x['patch'], x['tournament'], x['game'], x['blue'], x['red'], x['url']

    text_file = open('history.html', 'w')
    text_file.write(str(history))
    text_file.close()

scrape_tournament_history("https://lol.gamepedia.com/League_Championship_Series/North_America/2018_Season/Regional_Finals/Match_History", "NALCS Regionals 2018")
