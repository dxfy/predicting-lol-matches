# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
import time
import sys
from collections import OrderedDict

# Takes a lol.gamepedia.com tournament match history page and returns match history url and team/player information.
def get_tournament_matches(url, tournament):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    history = soup.find('table', {'class': 'wikitable'})

    # Removes table and column header rows.
    rows = history.find_all('tr')
    for x in range(0, 3):
        rows[x].extract()

    # Removes images and unnecessary columns.
    [x.decompose() for x in history.find_all('img')]
    [x.decompose() for x in history.find_all('td', {'class': 'stats'})]
    rows = history.find_all('tr')

    # Order from least to most recent.
    rows.reverse()

    # Scrapes data and stores match data in array.
    matches = []
    for x in range(0, len(rows)):
        columns = rows[x].find_all('td')

        if columns[12].find('a') is None:
            continue

        # Gets game number if in a series.
        game = 1
        if len(matches) > 0:
            prev_blue = matches[len(matches)-1]['blue_team']
            prev_red = matches[len(matches)-1]['red_team']
            curr_blue = columns[3].find('a').get('title').strip()
            curr_red = columns[4].find('a').get('title').strip()

            if (prev_blue in (curr_red, curr_blue)) and (prev_red in (curr_red, curr_blue)):
                game = matches[len(matches)-1]['game'] + 1

        # Gets players.
        blue_players_tags = columns[9].find_all('a')
        red_players_tags = columns[10].find_all('a')
        blue_players = []
        red_players = []
        for y in range(0, len(blue_players_tags)):
            blue_players.append(blue_players_tags[y].contents[0].strip())
            red_players.append(red_players_tags[y].contents[0].strip())

        # # Get bans.
        # blue_bans = columns[6].contents[0].replace("\n", "").split(", ")
        # red_bans = columns[7].contents[0].replace("\n", "").split(", ")
        blue_bans_tags = columns[5].span.find_all('a')
        red_bans_tags = columns[6].span.find_all('a')
        blue_bans = []
        red_bans = []
        for y in range(0, len(blue_bans_tags)):
            blue_bans.insert(len(blue_bans), blue_bans_tags[y].get('title').strip())
            red_bans.insert(len(red_bans), red_bans_tags[y].get('title').strip())

        # # Get champions.
        # blue_champions = columns[8].contents[0].replace("\n", "").split(", ")
        # red_champions = columns[9].contents[0].replace("\n", "").split(", ")
        blue_champions_tags = columns[7].span.find_all('a')
        red_champions_tags = columns[8].span.find_all('a')
        blue_champions = []
        red_champions = []
        for y in range(0, len(blue_champions_tags)):
            blue_champions.insert(len(blue_champions), blue_champions_tags[y].get('title').strip())
            red_champions.insert(len(red_champions), red_champions_tags[y].get('title').strip())

        match = OrderedDict()
        match['date'] = columns[1].get_text().strip()
        match['patch'] = columns[2].get_text().strip()
        match['tournament'] = tournament
        match['game'] = game
        match['blue_team'] = columns[3].find('a').get('title').strip()
        match['red_team'] = columns[4].find('a').get('title').strip()
        match['blue_players'] = blue_players
        match['red_players'] = red_players
        match['blue_bans'] = blue_bans
        match['red_bans'] = red_bans
        match['blue_champions'] = blue_champions
        match['red_champions'] = red_champions
        match['url'] = columns[12].find('a').get('href').strip()

        matches.append(match)

    print tournament

    return matches

# Iterates over matches returned from get_tournament_matches and uses riot api to return match data for each match.
def get_matches_data(matches):
    progress = 0
    matches_data = []
    for match in matches:
        clean_url = match['url'].replace("&tab=overview", "")

        url_parts = clean_url.replace("?", "/").split("/")
        match_url = "https://acs.leagueoflegends.com/v1/stats/game/" + url_parts[5] + "/" + url_parts[6] + "?" + url_parts[7]
        timeline_url = "https://acs.leagueoflegends.com/v1/stats/game/" + url_parts[5] + "/" + url_parts[6] + "/timeline?" + url_parts[7]
        match_data = requests.get(match_url).json()
        timeline_data = requests.get(timeline_url).json()

        # For using local files instead of making api calls
        # with open('match_data.json') as match_json:
        #    match_data = json.load(match_json)
        # with open('timeline_data.json') as timeline_json:
        #    timeline_data = json.load(timeline_json)

        for player in range(0, 10):
            data = OrderedDict()

            ## General
            # url
            data['url'] = clean_url
            # game id
            data['game_id'] = match_data['gameId']
            # date
            data['date'] = time.strftime('%d/%m/%Y', time.localtime(match_data['gameCreation']/float(1000)))
            # patch
            data['patch'] = match['patch']
            # tournament
            data['tournament'] = match['tournament']
            # game in series
            data['game_in_series'] = match['game']

            ## Player
            # player id
            data['player_id'] = match_data['participants'][player]['participantId']
            # side
            data['side'] = "blue" if match_data['participants'][player]['teamId'] == 100 else "red"
            # team
            data['team'] = match['blue_team'] if player < 5 else match['red_team']
            # player
            data['player'] = (match['blue_players'] + match['red_players'])[player]
            # position
            positions = ["Top", "Jungle", "Mid", "ADC", "Support"]
            data['position'] = positions[player % 5]
            # champion
            data['champion'] = match['blue_champions'][player % 5] if player < 5 else match['red_champions'][player % 5]

            ## Game
            # bans
            bans_length = len(match['blue_bans']) if player < 5 else len(match['red_bans'])
            for i in range(0, bans_length):
                ban_num = 'ban{}'.format(i+1)
                data[ban_num] = match['blue_bans'][i] if player < 5 else match['red_bans'][i]
            # game length
            data['game_length'] = match_data['gameDuration']/float(60)
            # result
            team = 0 if match_data['participants'][player]['teamId'] == 100 else 1
            data['result'] = 1 if match_data['teams'][team]['win'] == "Win" else 0

            ## Combat
            # kills death assists
            data['kills'] = match_data['participants'][player]['stats']['kills']
            data['deaths'] = match_data['participants'][player]['stats']['deaths']
            data['assists'] = match_data['participants'][player]['stats']['assists']
            # opponent kills
            data['opp_kills'] = match_data['participants'][player+5]['stats']['kills'] if player < 5 else match_data['participants'][player-5]['stats']['kills']
            # kda
            data['kda'] = (data['kills'] + data['assists']) if data['deaths'] == 0 else (data['kills'] + data['assists'])/float(data['deaths'])
            # team kills & team deaths
            team_offset = 5 if player >= 5 else 0
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
            # first blood
            data['first_blood'] = 1 if match_data['participants'][player]['stats']['firstBloodKill'] else 0
            # first blood assist & first blood victim & first blood time
            first_blood_assist = 0
            first_blood_victim = 0
            first_blood_time = 0
            for frame in timeline_data['frames']:
                if first_blood_time != 0:
                    break
                for event in frame['events']:
                    if event['type'] == "CHAMPION_KILL":
                        if (event['victimId']-1) == player:
                            first_blood_victim = 1
                        else:
                            for assistingPlayer in event['assistingParticipantIds']:
                                if (assistingPlayer-1) == player:
                                    first_blood_assist = 1
                        first_blood_time = event['timestamp']
                        break
            data['first_blood_assist'] = first_blood_assist
            data['first_blood_victim'] = first_blood_victim
            data['first_blood_time'] = (first_blood_time/float(1000))/float(60)
            # kills per minute, opponent kills per minute, combined kills per minute
            data['kills_per_minute'] = data['kills']/float(data['game_length'])
            data['opp_kills_per_minute'] = data['opp_kills']/float(data['game_length'])
            data['combined_kills_per_minute'] = (data['kills'] + data['opp_kills'])/float(data['game_length'])

            ## Objectives
            # first tower
            team = 0 if match_data['participants'][player]['teamId'] == 100 else 1
            data['first_tower'] = int(match_data['teams'][team]['firstTower'])
            # first tower gained time & first tower conceded time
            data['first_tower_gained_time'] = None
            data['first_tower_conceded_time'] = None
            # first mid outer
            first_mid_outer = -1
            for frame in timeline_data['frames']:
                if first_mid_outer != -1:
                    break
                for event in frame['events']:
                    if event['type'] == "BUILDING_KILL" and event['laneType'] == "MID_LANE" and event['towerType'] == "OUTER_TURRET":
                        first_mid_outer = 0 if event['teamId'] == match_data['participants'][player]['teamId'] else 1
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
                    if blue_tower_kills == 3 or red_tower_kills == 3:
                        break
            first_to_three_towers = 0
            if match_data['participants'][player]['teamId'] == 100 and blue_tower_kills == 3:
                first_to_three_towers = 1
            elif match_data['participants'][player]['teamId'] == 200 and red_tower_kills == 3:
                first_to_three_towers = 1
            data['first_to_three_towers'] = first_to_three_towers
            # team tower kills & opponent tower kills
            team = 0 if match_data['participants'][player]['teamId'] == 100 else 1
            data['team_tower_kills'] = match_data['teams'][team]['towerKills']
            data['opp_tower_kills'] = match_data['teams'][1-team]['towerKills']
            # first dragon
            team = 0 if match_data['participants'][player]['teamId'] == 100 else 1
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
            # team dragons & opponent dragons
            team = 0 if match_data['participants'][player]['teamId'] == 100 else 1
            data['team_dragons'] = match_data['teams'][team]['dragonKills']
            data['opp_dragons'] = match_data['teams'][1-team]['dragonKills']
            # team elementals & opponent elementals
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
            # team elders & opponent elders
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
            team = 0 if match_data['participants'][player]['teamId'] == 100 else 1
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
            # team barons & opponent barons
            team = 0 if match_data['participants'][player]['teamId'] == 100 else 1
            data['team_barons'] = match_data['teams'][team]['baronKills']
            data['opp_barons'] = match_data['teams'][1-team]['baronKills']
            # herald
            team = 0 if match_data['participants'][player]['teamId'] == 100 else 1
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

            ## Damage
            # storing total damage values
            team_offset = 5 if player >= 5 else 0
            team_damage = 0
            team_physical_damage = 0
            team_magic_damage = 0
            for x in range(0+team_offset, 5+team_offset):
                team_damage += match_data['participants'][x]['stats']['totalDamageDealtToChampions']
                team_physical_damage += match_data['participants'][x]['stats']['physicalDamageDealtToChampions']
                team_magic_damage += match_data['participants'][x]['stats']['magicDamageDealtToChampions']

            # damage, damage per minute, damage share of team damage
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

            ## Gold
            # gold earned, gold earned per minute (minus starting gold)
            data['gold_earned'] = match_data['participants'][player]['stats']['goldEarned']-500
            data['gold_earned_per_minute'] = data['gold_earned']/float(data['game_length'])
            # share of team total gold (minus starting gold)
            team_offset = 5 if player >= 5 else 0
            team_gold_earned = 0
            for x in range(0+team_offset, 5+team_offset):
                team_gold_earned += match_data['participants'][x]['stats']['goldEarned']-500
            data['gold_earned_share'] = data['gold_earned']/float(team_gold_earned)
            # total gold spent & opponent gold spent
            data['gold_spent'] = match_data['participants'][player]['stats']['goldSpent']
            data['opp_gold_spent'] = match_data['participants'][player+5]['stats']['goldSpent'] if player < 5 else match_data['participants'][player-5]['stats']['goldSpent']
            # gold at 15
            data['gold_at_15'] = timeline_data['frames'][15]['participantFrames'][str(player+1)]['totalGold']
            # gold at 25
            gold_at_25 = 0
            if len(timeline_data['frames'])-1 < 25:
                gold_at_25 = timeline_data['frames'][-1]['participantFrames'][str(player+1)]['totalGold']
            else:
                gold_at_25 = timeline_data['frames'][25]['participantFrames'][str(player+1)]['totalGold']
            data['gold_at_25'] = gold_at_25

            ## Minions/Monsters
            # creep score, creep score per minute
            data['creep_score'] = match_data['participants'][player]['stats']['totalMinionsKilled'] + match_data['participants'][player]['stats']['neutralMinionsKilled']
            data['creep_score_per_minute'] = data['creep_score']/float(data['game_length'])
            # monsters killed, monsters killed in team jungle, monsters killed in oppponent jungle
            data['monster_kills'] = match_data['participants'][player]['stats']['neutralMinionsKilled']
            data['monster_kills_team_jungle'] = match_data['participants'][player]['stats']['neutralMinionsKilledTeamJungle']
            data['monster_kills_opp_jungle'] = match_data['participants'][player]['stats']['neutralMinionsKilledEnemyJungle']

            ## Vision
            # wards placed, wards placed per minute
            data['wards_placed'] = match_data['participants'][player]['stats']['wardsPlaced']
            data['wards_placed_per_minute'] = data['wards_placed']/float(data['game_length'])
            # share of team wards placed
            team_offset = 5 if player >= 5 else 0
            team_wards_placed = 0
            for x in range(0+team_offset, 5+team_offset):
                team_wards_placed += match_data['participants'][x]['stats']['wardsPlaced']
            data['wards_placed_share'] = data['wards_placed']/float(team_wards_placed)
            # wards cleared, wards cleared per minute
            data['wards_cleared'] = match_data['participants'][player]['stats']['wardsKilled']
            data['wards_cleared_per_minute'] = data['wards_cleared']/float(data['game_length'])
            # vision/control wards placed, vision/control wards placed per minute
            control_wards_placed = 0
            for frame in timeline_data['frames']:
                for event in frame['events']:
                    if event['type'] == "WARD_PLACED" and (event['wardType'] == "CONTROL_WARD" or event['wardType'] == "VISION_WARD"):
                        if (event['creatorId']-1) == player:
                            control_wards_placed += 1
            data['control_wards_placed'] = control_wards_placed
            data['control_wards_placed_per_minute'] = control_wards_placed/float(data['game_length'])
            # opponent visible wards cleared %, opponent invisible wards cleared %
            data['visible_wards_cleared_percent'] = None
            data['invisible_wards_cleared_percent'] = None

            matches_data.append(data)

        for team in range(0, 2):
            data = OrderedDict()

            player_index = (len(matches_data)-10)+(team*4)

            ## General
            # url
            data['url'] = clean_url
            # game id
            data['game_id'] = match_data['gameId']
            # date
            data['date'] = time.strftime('%d/%m/%Y', time.localtime(match_data['gameCreation']/float(1000)))
            # patch
            data['patch'] = match['patch']
            # tournament
            data['tournament'] = match['tournament']
            # game in series
            data['game_in_series'] = match['game']

            ## Team
            # team id
            data['player_id'] = match_data['teams'][team]['teamId']
            # side
            data['side'] = "blue" if team == 0 else "red"
            # team
            data['team'] = match['blue_team'] if team == 0 else match['red_team']

            ## Game
            # bans
            bans_length = len(match['blue_bans']) if team == 0 else len(match['red_bans'])
            for i in range(0, bans_length):
                ban_num = 'ban{}'.format(i+1)
                data[ban_num] = match['blue_bans'][i] if team == 0 else match['red_bans'][i]
            # game length
            data['game_length'] = match_data['gameDuration']/float(60)
            # result
            data['result'] = 1 if match_data['teams'][team]['win'] == "Win" else 0

            ## Combat
            # kills death assists
            assists = 0
            for i in range(0, 5):
                assists += matches_data[player_index+i]['assists']
            data['kills'] = matches_data[player_index]['team_kills']
            data['deaths'] = matches_data[player_index]['team_deaths']
            data['assists'] = assists
            # kda
            data['kda'] = (data['kills'] + data['assists']) if data['deaths'] == 0 else (data['kills'] + data['assists'])/float(data['deaths'])
            # team kills & team deaths
            data['team_kills'] = matches_data[player_index]['team_kills']
            data['team_deaths'] = matches_data[player_index]['team_deaths']
            # multi kills
            double_kills = 0
            triple_kills = 0
            quadra_kills = 0
            penta_kills = 0
            for i in range(0, 5):
                double_kills += matches_data[player_index+i]['double_kills']
                triple_kills += matches_data[player_index+i]['triple_kills']
                quadra_kills += matches_data[player_index+i]['quadra_kills']
                penta_kills += matches_data[player_index+i]['penta_kills']
            data['double_kills'] = double_kills
            data['triple_kills'] = triple_kills
            data['quadra_kills'] = quadra_kills
            data['penta_kills'] = penta_kills
            # first blood & first blood victim & first blood time
            first_blood = 0
            for i in range(0, 5):
                if matches_data[player_index+i]['first_blood']:
                    first_blood = 1
            data['first_blood'] = first_blood
            data['first_blood_victim'] = 1-first_blood
            data['first_blood_time'] = matches_data[player_index]['first_blood_time']
            # kills per minute, opponent kills per minute, combined kills per minute
            data['kills_per_minute'] = data['kills']/float(data['game_length'])
            data['opp_kills_per_minute'] = data['deaths']/float(data['game_length'])
            data['combined_kills_per_minute'] = (data['kills'] + data['deaths'])/float(data['game_length'])

            ## Objectives
            # first tower
            data['first_tower'] = matches_data[player_index]['first_tower']
            # first tower gained time & first tower conceded time
            first_tower_gained_time = 0
            first_tower_conceded_time = 0
            for frame in timeline_data['frames']:
                if first_tower_gained_time != 0 and first_tower_conceded_time != 0:
                    break
                for event in frame['events']:
                    if team == 0:
                        if first_tower_gained_time == 0 and event['type'] == "BUILDING_KILL" and event['teamId'] == 200 :
                            first_tower_gained_time = event['timestamp']
                        if first_tower_conceded_time == 0 and event['type'] == "BUILDING_KILL" and event['teamId'] == 100 :
                            first_tower_conceded_time = event['timestamp']
                    if team == 1:
                        if first_tower_gained_time == 0 and event['type'] == "BUILDING_KILL" and team == 1 and event['teamId'] == 100 :
                            first_tower_gained_time = event['timestamp']
                        if first_tower_conceded_time == 0 and event['type'] == "BUILDING_KILL" and team == 1 and event['teamId'] == 200 :
                            first_tower_conceded_time = event['timestamp']
            data['first_tower_gained_time'] = (first_tower_gained_time/float(1000))/float(60)
            data['first_tower_conceded_time'] = (first_tower_conceded_time/float(1000))/float(60)
            # first mid outer & first to three towers
            data['first_mid_outer'] = matches_data[player_index]['first_mid_outer']
            data['first_to_three_towers'] = matches_data[player_index]['first_to_three_towers']
            # team tower kills & opponent tower kills
            data['team_tower_kills'] = matches_data[player_index]['team_tower_kills']
            data['opp_tower_kills'] = matches_data[player_index]['opp_tower_kills']
            # first dragon & first dragon time
            data['first_dragon'] = matches_data[player_index]['first_dragon']
            data['first_dragon_time'] = matches_data[player_index]['first_dragon_time']
            # team dragons & opponent dragons
            data['team_dragons'] = matches_data[player_index]['team_dragons']
            data['opp_dragons'] = matches_data[player_index]['opp_dragons']
            # team elementals & opponent elementals
            data['team_elementals'] = matches_data[player_index]['team_elementals']
            data['opp_elementals'] = matches_data[player_index]['opp_elementals']
            # team dragon types
            data['fire_dragons'] = matches_data[player_index]['fire_dragons']
            data['water_dragons'] = matches_data[player_index]['water_dragons']
            data['earth_dragons'] = matches_data[player_index]['earth_dragons']
            data['air_dragons'] = matches_data[player_index]['air_dragons']
            # team elders & opponent elders
            data['team_elders'] = matches_data[player_index]['team_elders']
            data['opp_elders'] = matches_data[player_index]['opp_elders']
            # first baron & first baron time
            data['first_baron'] = matches_data[player_index]['first_baron']
            data['first_baron_time'] = matches_data[player_index]['first_baron_time']
            # team barons & opponent barons
            data['team_barons'] = matches_data[player_index]['team_barons']
            data['opp_barons'] = matches_data[player_index]['opp_barons']
            # herald & herald time
            data['herald'] = matches_data[player_index]['herald']
            data['herald_time'] = matches_data[player_index]['herald_time']

            ## Damage
            damage = 0
            physical_damage = 0
            magic_damage = 0
            for i in range(0, 5):
                damage += matches_data[player_index+i]['damage']
                physical_damage += matches_data[player_index+i]['physical_damage']
                magic_damage += matches_data[player_index+i]['magic_damage']
            # damage, damage per minute
            data['damage'] = damage
            data['damage_per_minute'] = damage/float(data['game_length'])
            # physical damage, physical damage share of team physical damage, physical damage share of player damage
            data['physical_damage'] = physical_damage
            data['physical_damage_share_of_damage'] = physical_damage/float(data['damage'])
            # magic damage, magic damage share of team magic damage, magic damage share of player damage
            data['magic_damage'] = magic_damage
            data['magic_damage_share_of_damage'] = magic_damage/float(data['damage'])

            ## Gold
            # gold earned & gold earned per minute (minus starting gold and gold generation)
            gold_earned = 0
            for i in range(0, 5):
                gold_earned += matches_data[player_index+i]['gold_earned']
            data['gold_earned'] = gold_earned
            data['gold_earned_per_minute'] = gold_earned/float(data['game_length'])
            # total gold spent & opponent gold spent
            gold_spent = 0
            opp_gold_spent = 0
            for i in range(0, 5):
                gold_spent += matches_data[player_index+i]['gold_spent']
                opp_gold_spent += matches_data[player_index+i]['opp_gold_spent']
            data['gold_spent'] = gold_spent
            data['opp_gold_spent'] = opp_gold_spent
            # gold at 15
            gold_at_15 = 0
            for i in range(0, 5):
                gold_at_15 += matches_data[player_index+i]['gold_at_15']
            data['gold_at_15'] = gold_at_15
            # gold at 25
            gold_at_25 = 0
            for i in range(0, 5):
                gold_at_25 += matches_data[player_index+i]['gold_at_25']
            data['gold_at_25'] = gold_at_25

            ## Minions/Monsters
            # creep score, creep score per minute
            creep_score = 0
            for i in range(0, 5):
                creep_score += matches_data[player_index+i]['creep_score']
            data['creep_score'] = creep_score
            data['creep_score_per_minute'] = creep_score/float(data['game_length'])
            # monsters killed, monsters killed in team jungle, monsters killed in oppponent jungle
            creep_score = 0
            monster_kills = 0
            monster_kills_team_jungle = 0
            monster_kills_opp_jungle = 0
            for i in range(0, 5):
                monster_kills += matches_data[player_index+i]['monster_kills']
                monster_kills_team_jungle += matches_data[player_index+i]['monster_kills_team_jungle']
                monster_kills_opp_jungle += matches_data[player_index+i]['monster_kills_opp_jungle']
            data['monster_kills'] = monster_kills
            data['monster_kills_team_jungle'] = monster_kills_team_jungle
            data['monster_kills_opp_jungle'] = monster_kills_opp_jungle

            ## Vision
            # wards placed, wards placed per minute
            wards_placed = 0
            for i in range(0, 5):
                wards_placed += matches_data[player_index+i]['wards_placed']
            data['wards_placed'] = wards_placed
            data['wards_placed_per_minute'] = wards_placed/float(data['game_length'])
            # wards cleared, wards cleared per minute
            wards_cleared = 0
            for i in range(0, 5):
                wards_cleared += matches_data[player_index+i]['wards_cleared']
            data['wards_cleared'] = wards_cleared
            data['wards_cleared_per_minute'] = wards_cleared/float(data['game_length'])
            # vision/control wards placed, vision/control wards placed per minute
            control_wards_placed = 0
            for i in range(0, 5):
                control_wards_placed += matches_data[player_index+i]['control_wards_placed']
            data['control_wards_placed'] = control_wards_placed
            data['control_wards_placed_per_minute'] = control_wards_placed/float(data['game_length'])
            # visible wards cleared %, invisible wards cleared %
            opp_visible_wards_placed = 0
            visible_wards_cleared = 0
            opp_invisible_wards_placed = 0
            invisible_wards_cleared = 0
            for frame in timeline_data['frames']:
                for event in frame['events']:
                    # invisible wards cleared/placed
                    if event['type'] == "WARD_PLACED" and event['wardType'] != "CONTROL_WARD" and event['wardType'] != "BLUE_TRINKET" and event['wardType'] != "VISION_WARD" and event['wardType'] != "UNDEFINED":
                        if team == 0 and ((event['creatorId']-1) >= 5):
                            opp_invisible_wards_placed += 1
                        elif team == 1 and ((event['creatorId']-1) < 5):
                            opp_invisible_wards_placed += 1
                    elif event['type'] == "WARD_KILL" and event['wardType'] != "CONTROL_WARD" and event['wardType'] != "BLUE_TRINKET" and event['wardType'] != "VISION_WARD" and event['wardType'] != "UNDEFINED":
                        if team == 0 and ((event['killerId']-1) < 5):
                            invisible_wards_cleared += 1
                        elif team == 1 and ((event['killerId']-1) >= 5):
                            invisible_wards_cleared += 1
                    # visible wards cleared/placed
                    elif event['type'] == "WARD_PLACED" and (event['wardType'] == "CONTROL_WARD" or event['wardType'] == "BLUE_TRINKET" or event['wardType'] == "VISION_WARD"):
                        if team == 0 and ((event['creatorId']-1) >= 5):
                            opp_visible_wards_placed += 1
                        elif team == 1 and ((event['creatorId']-1) < 5):
                            opp_visible_wards_placed += 1
                    elif event['type'] == "WARD_KILL" and (event['wardType'] == "CONTROL_WARD" or event['wardType'] == "BLUE_TRINKET" or event['wardType'] == "VISION_WARD"):
                        if team == 0 and ((event['killerId']-1) < 5):
                            visible_wards_cleared += 1
                        elif team == 1 and ((event['killerId']-1) >= 5):
                            visible_wards_cleared += 1
            data['visible_wards_cleared_percent'] = visible_wards_cleared/float(opp_visible_wards_placed)
            data['invisible_wards_cleared_percent'] = invisible_wards_cleared/float(opp_invisible_wards_placed)

            matches_data.append(data)

        progress += 1
        sys.stdout.write("\r{0}/{1} matches scraped.".format(progress, len(matches)))
        sys.stdout.flush()

    print "\n"

    return matches_data

def write_matches_data_to_csv(matches, name):
    file_name = name + ".csv"

    if os.path.isfile(file_name):
        os.remove(file_name)

    with open(file_name, mode='w') as csv_file:
        fieldnames = []
        for key in matches[0]:
            fieldnames.append(key)

        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

    with open(file_name, mode='a') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        for match in matches:
            writer.writerow(match)

matches = []
# matches.extend(get_tournament_matches("https://lol.gamepedia.com/NA_LCS/2018_Season/Spring_Season/Match_History", "NALCS 2018 Spring"))
# matches.extend(get_tournament_matches("https://lol.gamepedia.com/NA_LCS/2018_Season/Spring_Playoffs/Match_History", "NALCS 2018 Spring Playoffs"))
# matches.extend(get_tournament_matches("https://lol.gamepedia.com/NA_LCS/2018_Season/Summer_Season/Match_History", "NALCS 2018 Summer"))
# matches.extend(get_tournament_matches("https://lol.gamepedia.com/NA_LCS/2018_Season/Summer_Playoffs/Match_History", "NALCS 2018 Summer Playoffs"))
matches.extend(get_tournament_matches("https://lol.gamepedia.com/NA_LCS/2018_Season/Regional_Finals/Match_History", "NALCS 2018 Regionals"))

matches_data = get_matches_data(matches)

write_matches_data_to_csv(matches_data, "test")
