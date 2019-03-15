import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import csv
import os
from collections import OrderedDict

def get_tournament_odds(url):
    # Scrape url
    options = webdriver.ChromeOptions()
    options.add_argument("--user-data-dir=/Users/Hamza/library/application support/google/chrome/default")
    driver = webdriver.Chrome(chrome_options=options)
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Scrape local file
    #soup = BeautifulSoup(open(url), "html.parser")

    pagination = soup.find('div', {'id': 'pagination'})
    pages = [url]
    for item in pagination.select('a > span'):
        if item.text.isdigit():
            pages.append(url + "#/page/{}/".format(int(item.text)))

    matches_odds = []

    for page in pages:
        print page
        driver.get(page)
        soup = soup = BeautifulSoup(driver.page_source, 'html.parser')
        #soup = BeautifulSoup(open('oddsport_error.html'), 'html.parser')

        table = soup.find('table', {'id': 'tournamentTable'})

        a_tags = table.select('td.table-participant > a')
        match_links = [("https://www.oddsportal.com" + a.get('href').strip()) for a in a_tags]
        # match_teams = []
        # for a in a_tags:
        #     print a.contents
        #
        #     if (a.contents[0].name == 'span') or (a.contents[1].name == 'span'):
        #         if a.contents[0].name == 'span':
        #             team1 = a.contents[0].text
        #             team2 = a.contents[1][3:]
        #         elif a.contents[1].name == 'span':
        #             team1 = a.contents[0][3:]
        #             team2 = a.contents[1].text
        #     else:
        #         team1 = a.contents[0][]
        #
        #     print [team1, team2]
        #
        #     match_teams.append([team1, team2])

        for match in match_links:
            driver.get(match)
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            correct_page = 0
            while(not correct_page):
                if soup.select_one('div#col-content > h1').text == "System error":
                    driver.get(match)
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    time.sleep(5)
                else:
                    correct_page = 1

            details = soup.find('div', {'id': 'col-content'})
            date = details.select_one('p.date').text.strip()
            teams = details.select_one('h1').text.strip().split(" - ")

            match_odds = OrderedDict()
            match_odds['date'] = date
            match_odds['team1'] = teams[0].strip()
            match_odds['team2'] = teams[1].strip()

            #print match_odds

            #break

            table_rows = soup.select('table.table-main > tbody > tr.lo')
            for i, row in enumerate(table_rows):
                if row.select('td > div.l > a.name')[0].text == "Pinnacle":
                    for j, odds_element in enumerate(row.select('td.odds > div')):
                        odds_hover = driver.find_element_by_xpath('//div[@id="odds-data-table"]/div/table/tbody/tr[{}]/td[{}]'.format(i+1, j+2))

                        hover = ActionChains(driver).move_to_element(odds_hover)
                        hover.perform()

                        odds_pop_up = driver.find_element_by_xpath('//span[@id="tooltiptext"]').find_elements_by_tag_name('strong')

                        team_odds = []
                        for odds_value in odds_pop_up:
                            team_odds.append(odds_value.get_attribute('innerHTML'))

                        if j == 0:
                            match_odds['team1_odds'] = team_odds
                        elif j == 1:
                            match_odds['team2_odds'] = team_odds

            matches_odds.append(match_odds)

            print teams[0], teams[1]

            time.sleep(1)

            #break

        #break

        time.sleep(5)

    driver.close()

    return matches_odds

def write_odds_data_to_csv(matches, name):
    file_name = name + ".csv"

    if os.path.isfile(file_name):
        os.remove(file_name)

    with open(file_name, mode='w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=matches[0].keys())
        writer.writeheader()
        for match in matches:
            writer.writerow(match)

tournaments = [
        "https://www.oddsportal.com/esports/world/league-of-legends-championship-series-2018/results/",
        "https://www.oddsportal.com/esports/south-korea/league-of-legends-champions-korea-2018/results/",
        "https://www.oddsportal.com/esports/taiwan/league-of-legends-lol-master-series-2018/results/",
]

start = time.time()

matches_odds = []
for tournament in tournaments:
   matches_odds.extend(get_tournament_odds(tournament))

write_odds_data_to_csv(matches_odds, "complete2018_odds")

end = time.time()
print(end - start)
