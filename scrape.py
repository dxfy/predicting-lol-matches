# -*- coding: utf-8 -*-

# import libraries
import requests
from bs4 import BeautifulSoup
import json
import csv
import time
from collections import OrderedDict

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

            if (prev_blue in (curr_red, curr_blue)) and (prev_red in (curr_red, curr_blue)):
                game = matches[len(matches)-1]['game'] + 1

        # get players
        blue_players_tags = columns[9].find_all('a')
        red_players_tags = columns[10].find_all('a')
        blue_players = []
        red_players = []
        for y in range(0, len(blue_players_tags)):
            blue_players.insert(len(blue_players), blue_players_tags[y].contents[0].strip())
            red_players.insert(len(red_players), red_players_tags[y].contents[0].strip())

        data = OrderedDict()
        data['date'] = columns[0].get_text().strip()
        data['tournament'] = tournament
        data['game'] = game
        data['blue_team'] = columns[2].find('a').get('title').strip()
        data['red_team'] = columns[3].find('a').get('title').strip()
        data['blue_players'] = blue_players
        data['red_players'] = red_players
        data['url'] = "Riot Match History Page could not be found." if columns[12].find('a') is None else columns[12].find('a').get('href').strip()

        matches.insert(len(matches), data)

    return matches

def scrape_matches(matches):
    for match in matches:
        if match['url'] == "Riot Match History Page could not be found.":
            continue

        clean_url = match['url'].replace("&tab=overview", "")
        match_data = requests.get("https://acs.leagueoflegends.com/v1/stats/game" + clean_url[61:]).json()
        timeline_data = requests.get("https://acs.leagueoflegends.com/v1/stats/game" + clean_url[61:-26] + "/timeline" + clean_url[82:]).json()

        # with open('match_data.json') as match_json:
        #    match_data = json.load(match_json)
        # with open('timeline_data.json') as timeline_json:
        #    timeline_data = json.load(timeline_json)

        for player in range(0, 10):
            data = OrderedDict()

            ## general details
            # url
            data['url'] = match['url']
            # game id
            data['game_id'] = match_data['gameId']
            # date
            data['date'] = time.strftime('%d/%m/%Y',  time.localtime(match_data['gameCreation']/float(1000)))
            # patch
            data['patch'] = match_data['gameVersion']
            # tournament
            data['tournament'] = match['tournament']
            # game in series
            data['game_in_series'] = match['game']

            ## player details
            # player id
            data['player_id'] = match_data['participants'][player]['participantId']
            # side
            if match_data['participants'][player]['teamId'] == 100:
                data['side'] = "blue"
            else:
                data['side'] = "red"
            # team
            if player < 5:
                data['team'] = match['blue_team']
            else:
                data['team'] = match['red_team']
            # player
            data['player'] = (match['blue_players'] + match['red_players'])[player]
            # position
            position = player % 5
            if position == 0:
                data['position'] = "Top"
            elif position == 1:
                data['position'] = "Jungle"
            elif position == 2:
                data['position'] = "Mid"
            elif position == 3:
                data['position'] = "Adc"
            elif position == 4:
                data['position'] = "Support"
            # champion

            ## game details
            # bans
            # game length
            data['game_length'] = match_data['gameDuration']/float(60)
            # result
            if match_data['participants'][player]['teamId'] == 100:
                team = 0
            else:
                team = 1
            if match_data['teams'][team]['win'] == "Win":
                data['result'] = 1
            else:
                data['result'] = 0

            ## combat
            # kills death assists
            data['kills'] = match_data['participants'][player]['stats']['kills']
            data['deaths'] = match_data['participants'][player]['stats']['deaths']
            data['assists'] = match_data['participants'][player]['stats']['assists']
            # opponent kills
            if player < 5:
                data['opp_kills'] = match_data['participants'][player+5]['stats']['kills']
            else:
                data['opp_kills'] = match_data['participants'][player-5]['stats']['kills']
            # kda
            if data['deaths'] == 0:
                data['kda'] = (data['kills'] + data['assists'])
            else:
                data['kda'] = (data['kills'] + data['assists'])/float(data['deaths'])
            # team kills & team deaths
            team_offset = 0
            if player >= 5:
                team_offset = 5
            team_kills = 0
            team_deaths = 0
            for x in range(0+team_offset, 5+team_offset):
                team_kills += match_data['participants'][x]['stats']['kills']
                team_deaths += match_data['participants'][x]['stats']['deaths']
            data['team_kills'] = team_kills
            data['team_deaths'] = team_deaths
            # multi kills
            data['double_kills'] = match_data['participants'][player]['stats']['doubleKills']
            data['triple_kills'] = match_data['participants'][player]['stats']['tripleKills']
            data['quadra_kills'] = match_data['participants'][player]['stats']['quadraKills']
            data['penta_kills'] = match_data['participants'][player]['stats']['pentaKills']
            # first blood & assist
            if match_data['participants'][player]['stats']['firstBloodKill']:
                data['first_blood'] = 1
            else:
                data['first_blood'] = 0
            if match_data['participants'][player]['stats']['firstBloodAssist']:
                data['first_blood_assist'] = 1
            else:
                data['first_blood_assist'] = 0
            # first blood time
            first_blood_time = 0
            for frame in timeline_data['frames']:
                if first_blood_time != 0:
                    break
                for event in frame['events']:
                    if event['type'] == "CHAMPION_KILL":
                        first_blood_time = event['timestamp']
                        break
            data['first_blood_time'] = (first_blood_time/float(1000))/float(60)
            # kills per minute
            data['kills_per_minute'] = data['kills']/float(data['game_length'])
            # opponent kills per minute
            data['opp_kills_per_minute'] = data['opp_kills']/float(data['game_length'])
            # combined kills per minute
            data['combined_kills_per_minute'] = (data['kills'] + data['opp_kills'])/float(data['game_length'])

            ## objectives
            # first tower
            if match_data['participants'][player]['teamId'] == 100:
                team = 0
            else:
                team = 1
            data['first_tower'] = int(match_data['teams'][team]['firstTower'])
            # first tower time & lane
            first_tower_time = 0
            for frame in timeline_data['frames']:
                if first_tower_time != 0:
                    break
                for event in frame['events']:
                    if event['type'] == "BUILDING_KILL":
                        first_tower_time = event['timestamp']
                        first_tower_lane = event['laneType']
                        break
            data['first_tower_time'] = (first_tower_time/float(1000))/float(60)
            data['first_tower_lane'] = first_tower_lane
            # first mid outer
            first_mid_outer = -1
            for frame in timeline_data['frames']:
                if first_mid_outer != -1:
                    break
                for event in frame['events']:
                    if event['type'] == "BUILDING_KILL" and event['laneType'] == "MID_LANE" and event['towerType'] == "OUTER_TURRET":
                        if event['teamId'] == match_data['participants'][player]['teamId']:
                            first_mid_outer = 0
                        else:
                            first_mid_outer = 1
                        break
            data['first_mid_outer'] = first_mid_outer
            # first to three towers
            blue_tower_kills = 0
            red_tower_kills = 0
            for frame in timeline_data['frames']:
                if blue_tower_kills == 3 or red_tower_kills == 3:
                    break
                for event in frame['events']:
                    if event['type'] == "BUILDING_KILL" and event['buildingType'] == "TOWER_BUILDING":
                        if event['teamId'] == 200:
                            blue_tower_kills += 1
                        else:
                            red_tower_kills += 1
            first_to_three_towers = 0
            if match_data['participants'][player]['teamId'] == 100:
                if blue_tower_kills == 3:
                    first_to_three_towers = 1
            else:
                if red_tower_kills == 3:
                    first_to_three_towers = 1
            data['first_to_three_towers'] = first_to_three_towers
            # team & opponent tower kills
            if match_data['participants'][player]['teamId'] == 100:
                team = 0
            else:
                team = 1
            data['team_tower_kills'] = match_data['teams'][team]['towerKills']
            data['opp_tower_kills'] = match_data['teams'][1-team]['towerKills']
            # first dragon
            if match_data['participants'][player]['teamId'] == 100:
                team = 0
            else:
                team = 1
            data['first_dragon'] = int(match_data['teams'][team]['firstDragon'])
            # first dragon time
            first_dragon_time = 0
            for frame in timeline_data['frames']:
                if first_dragon_time != 0:
                    break
                for event in frame['events']:
                    if event['type'] == "ELITE_MONSTER_KILL" and event['monsterType'] == "DRAGON":
                        first_dragon_time = event['timestamp']
                        break
            data['first_dragon_time'] = (first_dragon_time/float(1000))/float(60)
            # team & opponent dragons
            if match_data['participants'][player]['teamId'] == 100:
                team = 0
            else:
                team = 1
            data['team_dragons'] = match_data['teams'][team]['dragonKills']
            data['opp_dragons'] = match_data['teams'][1-team]['dragonKills']
            # team & opponent elementals
            team_elementals = 0
            opp_elementals = 0
            for frame in timeline_data['frames']:
                for event in frame['events']:
                    if event['type'] == "ELITE_MONSTER_KILL" and 'monsterSubType' in event:
                        if event['monsterSubType'] != "ELDER_DRAGON":
                            if match_data['participants'][event['killerId']-1]['teamId'] == match_data['participants'][player]['teamId']:
                                team_elementals += 1
                            else:
                                opp_elementals += 1
            data['team_elementals'] = team_elementals
            data['opp_elementals'] = opp_elementals
            # team dragon types
            fire_dragons = 0
            water_dragons = 0
            earth_dragons = 0
            air_dragons = 0
            for frame in timeline_data['frames']:
                for event in frame['events']:
                    if event['type'] == "ELITE_MONSTER_KILL" and 'monsterSubType' in event:
                        if match_data['participants'][event['killerId']-1]['teamId'] == match_data['participants'][player]['teamId']:
                            dragon_type = event['monsterSubType']
                            if dragon_type == "FIRE_DRAGON":
                                fire_dragons += 1
                            if dragon_type == "WATER_DRAGON":
                                water_dragons += 1
                            if dragon_type == "EARTH_DRAGON":
                                earth_dragons += 1
                            if dragon_type == "AIR_DRAGON":
                                air_dragons += 1
            data['fire_dragons'] = fire_dragons
            data['water_dragons'] = water_dragons
            data['earth_dragons'] = earth_dragons
            data['air_dragons'] = air_dragons
            # team & opponent elders
            team_elders = 0
            opp_elders = 0
            for frame in timeline_data['frames']:
                for event in frame['events']:
                    if event['type'] == "ELITE_MONSTER_KILL" and 'monsterSubType' in event:
                        if event['monsterSubType'] == "ELDER_DRAGON":
                            if match_data['participants'][event['killerId']-1]['teamId'] == match_data['participants'][player]['teamId']:
                                team_elders += 1
                            else:
                                opp_elders += 1
            data['team_elders'] = team_elders
            data['opp_elders'] = opp_elders
            # first baron
            if match_data['participants'][player]['teamId'] == 100:
                team = 0
            else:
                team = 1
            data['first_baron'] = int(match_data['teams'][team]['firstBaron'])
            # first baron time
            first_baron_time = 0
            for frame in timeline_data['frames']:
                if first_baron_time != 0:
                    break
                for event in frame['events']:
                    if event['type'] == "ELITE_MONSTER_KILL" and event['monsterType'] == "BARON_NASHOR":
                        first_baron_time = event['timestamp']
                        break
            data['first_baron_time'] = (first_baron_time/float(1000))/float(60)
            # team & opponent barons
            if match_data['participants'][player]['teamId'] == 100:
                team = 0
            else:
                team = 1
            data['team_barons'] = match_data['teams'][team]['baronKills']
            data['opp_barons'] = match_data['teams'][1-team]['baronKills']
            # herald
            if match_data['participants'][player]['teamId'] == 100:
                team = 0
            else:
                team = 1
            data['herald'] = int(match_data['teams'][team]['firstRiftHerald'])
            # herald time
            herald_time = 0
            for frame in timeline_data['frames']:
                if herald_time != 0:
                    break
                for event in frame['events']:
                    if event['type'] == "ELITE_MONSTER_KILL" and event['monsterType'] == "RIFTHERALD":
                        herald_time = event['timestamp']
                        break
            data['herald_time'] = (herald_time/float(1000))/float(60)

            ## damage to champions
            # storing total damage values
            team_offset = 0
            if player >= 5:
                team_offset = 5
            team_damage = 0
            team_physical_damage = 0
            team_magic_damage = 0
            for x in range(0+team_offset, 5+team_offset):
                team_damage += match_data['participants'][x]['stats']['totalDamageDealtToChampions']
                team_physical_damage += match_data['participants'][x]['stats']['physicalDamageDealtToChampions']
                team_magic_damage += match_data['participants'][x]['stats']['magicDamageDealtToChampions']

            # damage, per minute, damage share of team damage
            data['damage'] = match_data['participants'][player]['stats']['totalDamageDealtToChampions']
            data['damage_per_minute'] = match_data['participants'][player]['stats']['totalDamageDealtToChampions']/float(data['game_length'])
            data['damage_share_of_team_damage'] = data['damage']/float(team_damage)
            # physical damage, physical damage share of team physical damage, physical damage share of player damage
            data['physical_damage'] = match_data['participants'][player]['stats']['physicalDamageDealtToChampions']
            data['physical_damage_share_of_team_physical_damage'] = data['physical_damage']/float(team_physical_damage)
            data['physical_damage_share_of_damage'] = data['physical_damage']/float(data['damage'])
            # magic damage, magic damage share of team magic damage, magic damage share of player damage
            data['magic_damage'] = match_data['participants'][player]['stats']['magicDamageDealtToChampions']
            data['magic_damage_share_of_team_magic_damage'] = data['magic_damage']/float(team_magic_damage)
            data['magic_damage_share_of_damage'] = data['magic_damage']/float(data['damage'])

            ## gold
            # total gold earned (minus starting gold and gold generation)
            data['gold_earned'] = match_data['participants'][player]['stats']['goldEarned']
            # gold per minute (minus gold generation)
            data['gold_earned_per_minute'] = data['gold_earned']/float(data['game_length'])
            # share of team total gold (minus starting gold and gold generation)
            team_offset = 0
            if player >= 5:
                team_offset = 5
            team_gold_earned = 0
            for x in range(0+team_offset, 5+team_offset):
                team_gold_earned += match_data['participants'][x]['stats']['goldEarned']
            data['gold_earned_share'] = data['gold_earned']/float(team_gold_earned)
            # total gold spent
            data['gold_spent'] = match_data['participants'][player]['stats']['goldSpent']
            # total gold spent % difference

            ## minions/monsters
            # creep score, creep score per minute
            data['creep_score'] = match_data['participants'][player]['stats']['totalMinionsKilled'] + match_data['participants'][player]['stats']['neutralMinionsKilled']
            data['creep_score_per_minute'] = data['creep_score']/float(data['game_length'])
            # monsters killed, monsters killed in team jungle, monsters killed in oppponent jungle
            data['monster_kills'] = match_data['participants'][player]['stats']['neutralMinionsKilled']
            data['monster_kills_team_jungle'] = match_data['participants'][player]['stats']['neutralMinionsKilledTeamJungle']
            data['monster_kills_opp_jungle'] = match_data['participants'][player]['stats']['neutralMinionsKilledEnemyJungle']



            ## vision
            # wards placed, wards placed per minute
            data['wards_placed'] = match_data['participants'][player]['stats']['wardsPlaced']
            data['wards_placed_per_minute'] = data['wards_placed']/float(data['game_length'])
            # share of team wards placed
            team_offset = 0
            if player >= 5:
                team_offset = 5
            team_wards_placed = 0
            for x in range(0+team_offset, 5+team_offset):
                team_wards_placed += match_data['participants'][x]['stats']['wardsPlaced']
            data['wards_placed_share'] = data['wards_placed']/float(team_wards_placed)
            # wards cleared, wards cleared per minute
            data['wards_cleared'] = match_data['participants'][player]['stats']['wardsKilled']
            data['wards_cleared_per_minute'] = data['wards_cleared']/float(data['game_length'])
            # control wards placed, control wards placed per minute
            control_wards_placed = 0
            for frame in timeline_data['frames']:
                for event in frame['events']:
                    if event['type'] == "WARD_PLACED" and event['wardType'] == "CONTROL_WARD":
                        if (event['creatorId']-1) == player:
                            control_wards_placed += 1
            data['control_wards_placed'] = control_wards_placed
            data['control_wards_placed_per_minute'] = control_wards_placed/float(data['game_length'])
            # opponent visible wards cleared %, opponent invisible wards cleared %
            opp_visible_wards_placed = 0
            visible_wards_cleared = 0
            opp_invisible_wards_placed = 0
            invisible_wards_cleared = 0
            for frame in timeline_data['frames']:
                for event in frame['events']:
                    # opponent visible wards cleared/placed
                    if event['type'] == "WARD_PLACED" and event['wardType'] != "CONTROL_WARD" and event['wardType'] != "BLUE_TRINKET":
                        if player < 5 and ((event['creatorId']-1) >= 5):
                            opp_visible_wards_placed += 1
                        elif player >= 5 and ((event['creatorId']-1) < 5):
                            opp_visible_wards_placed += 1
                    if event['type'] == "WARD_KILL" and event['wardType'] != "CONTROL_WARD" and event['wardType'] != "BLUE_TRINKET":
                        if player < 5 and ((event['killerId']-1) >= 5):
                            visible_wards_cleared += 1
                        elif player >= 5 and ((event['killerId']-1) < 5):
                            visible_wards_cleared += 1
                    # opponent invisible wards cleared/placed
                    if event['type'] == "WARD_PLACED" and (event['wardType'] == "CONTROL_WARD" or event['wardType'] == "BLUE_TRINKET"):
                        if player < 5 and ((event['creatorId']-1) >= 5):
                            opp_invisible_wards_placed += 1
                        elif player >= 5 and ((event['creatorId']-1) < 5):
                            opp_invisible_wards_placed += 1
                    if event['type'] == "WARD_KILL" and (event['wardType'] == "CONTROL_WARD" or event['wardType'] == "BLUE_TRINKET"):
                        if player < 5 and ((event['killerId']-1) >= 5):
                            invisible_wards_cleared += 1
                        elif player >= 5 and ((event['killerId']-1) < 5):
                            invisible_wards_cleared += 1
            data['visible_wards_cleared_percent'] = visible_wards_cleared/float(opp_visible_wards_placed)
            data['invisible_wards_cleared_percent'] = invisible_wards_cleared/float(opp_invisible_wards_placed)

            with open('matches.csv', mode='a') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writerow(data)

fieldnames = ['url', 'game_id', 'date', 'patch', 'tournament', 'game_in_series', 'player_id', 'side', 'team', 'player', 'position', 'game_length', 'result', 'kills', 'deaths', 'assists', 'opp_kills', 'kda', 'team_kills', 'team_deaths', 'double_kills', 'triple_kills', 'quadra_kills', 'penta_kills', 'first_blood', 'first_blood_assist', 'first_blood_time', 'kills_per_minute', 'opp_kills_per_minute', 'combined_kills_per_minute', 'first_tower', 'first_tower_time', 'first_tower_lane', 'first_mid_outer', 'first_to_three_towers', 'team_tower_kills', 'opp_tower_kills', 'first_dragon', 'first_dragon_time', 'team_dragons', 'opp_dragons', 'team_elementals', 'opp_elementals', 'fire_dragons', 'water_dragons', 'earth_dragons', 'air_dragons', 'team_elders', 'opp_elders', 'first_baron', 'first_baron_time', 'team_barons', 'opp_barons', 'herald', 'herald_time', 'damage', 'damage_per_minute', 'damage_share_of_team_damage', 'physical_damage', 'physical_damage_share_of_team_physical_damage', 'physical_damage_share_of_damage', 'magic_damage', 'magic_damage_share_of_team_magic_damage', 'magic_damage_share_of_damage', 'gold_earned', 'gold_earned_per_minute', 'gold_earned_share', 'gold_spent', 'creep_score', 'creep_score_per_minute', 'monster_kills', 'monster_kills_team_jungle', 'monster_kills_opp_jungle', 'wards_placed', 'wards_placed_per_minute', 'wards_placed_share', 'wards_cleared', 'wards_cleared_per_minute', 'control_wards_placed', 'control_wards_placed_per_minute', 'visible_wards_cleared_percent', 'invisible_wards_cleared_percent']

with open('matches.csv', mode='w') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()

matches = scrape_tournament_history("https://lol.gamepedia.com/Special:RunQuery/MatchHistoryTournament?MHT%5Btournament%5D=Concept:NA%20Regional%20Finals%202018&MHT%5Btext%5D=Yes&pfRunQueryFormName=MatchHistoryTournament", "NALCS Regionals 2018")

scrape_matches(matches)
