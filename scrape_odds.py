from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import csv
import os
from collections import OrderedDict

chromedriver_path = ''
user_data_directory = '/Users/Hamza/Library/Application Support/Google/Chrome/Default'

def get_tournament_odds(url):
    # Scrape url
    options = webdriver.ChromeOptions()
    options.add_argument('--user-data-dir=' + user_data_directory)
    if chromedriver_path == '':
        driver = webdriver.Chrome(chrome_options=options)
    else:
        driver = webdriver.Chrome('chromedriver_path', chrome_options=options)
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
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        table = soup.find('table', {'id': 'tournamentTable'})

        a_tags = table.select('td.table-participant > a')
        match_links = [("https://www.oddsportal.com" + a.get('href').strip()) for a in a_tags]

        for match in match_links:
            driver.get(match)
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # handles oddsportal system error page
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

tournaments_2018 = [
        "https://www.oddsportal.com/esports/world/league-of-legends-championship-series-2018/results/",
        "https://www.oddsportal.com/esports/south-korea/league-of-legends-champions-korea-2018/results/",
        "https://www.oddsportal.com/esports/taiwan/league-of-legends-lol-master-series-2018/results/",
]

tournaments_2017 = [
        "https://www.oddsportal.com/esports/world/league-of-legends-championship-series-2017/results/",
        "https://www.oddsportal.com/esports/south-korea/league-of-legends-champions-korea-2017/results/",
        "https://www.oddsportal.com/esports/taiwan/league-of-legends-lol-master-series-2017/results/",
]

tournaments_2016 = [
        "https://www.oddsportal.com/esports/world/league-of-legends-championship-series-2016/results/",
        "https://www.oddsportal.com/esports/south-korea/league-of-legends-champions-korea-2016/results/",
]

start = time.time()

# This code scrapes and writes each year of odds to its own file
# Running this code will overwrite the csvs we already scraped/prepared
#
# matches_odds = []
# for tournament in tournaments_2018:
#    matches_odds.extend(get_tournament_odds(tournament))
#
# write_odds_data_to_csv(matches_odds, "odds/2018_odds")
#
# matches_odds = []
# for tournament in tournaments_2017:
#    matches_odds.extend(get_tournament_odds(tournament))
#
# write_odds_data_to_csv(matches_odds, "odds/2017_odds")
#
# matches_odds = []
# for tournament in tournaments_2016:
#    matches_odds.extend(get_tournament_odds(tournament))
#
# write_odds_data_to_csv(matches_odds, "odds/2016_odds")

# Use this code to test the scraper on 2018 without overwriting the data we already prepared in the matches folder
matches_odds = []
for tournament in tournaments_2018:
   matches_odds.extend(get_tournament_odds(tournament))

write_odds_data_to_csv(matches_odds, "odds/test_2018_odds")

end = time.time()
print(end - start)
