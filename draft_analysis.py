import pandas as pd
import numpy as np
from ff_espn_api import League
from config import USERNAME, PASSWORD
import seaborn as sns
from scipy.optimize import curve_fit


# initializing settings
year = 2019
league_id = 291048

# connecting to league
league = League(league_id=league_id, year=year, username=USERNAME, password=PASSWORD)
weeks_completed = league.nfl_week

# initializing players dict
players = {}

pick = 1
for player in league.draft:
    name = player.playerName
    players[name] = [pick, 'POSITION_PLACEHOLDER']
    pick += 1

def update_players(player, week):
    if player.name not in players.keys():
        players[player.name] = [np.NaN]*(4*(week-1)+2)
        players[player.name][0] = np.NaN
        players[player.name][1] = player.position

    players[player.name].extend([
        player.points, player.pro_pos_rank, \
        player.projected_points, player.slot_position
        ])
    players[player.name][1] = player.position


# iterating through weeks, matchups, and players to 
# append weekly points for each player
for week in range(1, weeks_completed):
    for matchup in league.box_scores(week):
        for player in matchup.home_lineup:
            update_players(player, week)
        for player in matchup.away_lineup:
            update_players(player, week)
    
    # adding NaN entries for players not in lineups
    for player in players.keys():
        if len(players[player]) < (week*4+2):
            players[player].extend([np.NaN]*4)
        
        assert len(players[player]) == (week*4+2), \
            "Player, {} doesn't match after week {}".format(player, week)
    

# converting to pandas DataFrame
players = pd.DataFrame(players)
players = players.T

# naming columns and getting lists 
column_names = ['Pick', 'Position']

points_list = []
proj_pos_rank_list = []
proj_points_list = []
slot_position_list = []

for week in range(1, weeks_completed):

    points = 'Week_{}_points'.format(week)
    proj_pos_rank = 'Week_{}_proj_pos_rank'.format(week)
    proj_points = 'Week_{}_proj_points'.format(week)
    slot_position = 'Week_{}_slot_position'.format(week)
    
    column_names.extend([points, proj_pos_rank, proj_points, slot_position])
    points_list.append(points)
    proj_pos_rank_list.append(proj_pos_rank)
    proj_points_list.append(proj_points)
    slot_position_list.append(slot_position)

players.columns = column_names

# manually setting Adam Humphries' position to  WR, error in db
players.loc[['Adam Humphries'], ['Position']] = 'WR'

# summing total points
players['Total'] = players[points_list].sum(axis=1)


def get_replacement_levels():
    replacement_ranks = {
    'QB' : 12,
    'RB' : 30,
    'WR' : 30,
    'TE' : 12,
    'D/ST' : 12,
    'K' : 12,
    }

    replacement_levels = {
    'QB' : [],
    'RB' : [],
    'WR' : [],
    'TE' : [],
    'D/ST' : [],
    'K' : [],
    }

    for week in range(1, weeks_completed):
        for position in replacement_ranks.keys():
            position_players = players[players['Position']==position].sort_values(by=['Week_{}_proj_points'.format(week)], ascending=False)

            # get the replacement rank (ie, 12 for QBs, 30 for RBs)
            replacement_rank = replacement_ranks[position]

            baseline_player = position_players.iloc[replacement_rank]
            proj_points = baseline_player['Week_{}_proj_points'.format(week)]

            # if proj points is null for nth best projection, just take the lowest projected value that isn't 0 
            # this really only effects kickers
            if pd.isna(proj_points):
                proj_points = 0
                count = 1
                while proj_points == 0:
                    proj_points = position_players['Week_{}_proj_points'.format(week)].dropna()[-count]
                    count+=1
            replacement_levels[position].append(proj_points)
    
    return replacement_levels

def get_PAR(points, week, position):
    replacement_level = replacement_levels[position][week-1]
    PAR = points - replacement_level
    return PAR

def get_ADJ_PAR(points, week, position, projection):
    replacement_level = replacement_levels[position][week-1]

    # Not penalizing players for being bad/injured when we 
    # know they're going to be bad/injured
    if projection < replacement_level:
        return 0
    
    PAR = points - replacement_level
    return PAR

replacement_levels = get_replacement_levels()

for week in range(1, weeks_completed):
    points_col = 'Week_{}_points'.format(week)
    projection_col = 'Week_{}_proj_points'.format(week)
    players['Week_{}_PAR'.format(week)] = players.apply(lambda x: get_PAR(x[points_col], week, x['Position']), axis=1)
    players['Week_{}_ADJ_PAR'.format(week)] = players.apply(lambda x: get_ADJ_PAR(x[points_col], week, x['Position'], x[projection_col]), axis=1)

# Getting names of PAR columns to sum them
PAR_cols = []
ADJ_PAR_cols = []

for week in range(1, weeks_completed):
    PAR_cols.append('Week_{}_PAR'.format(week))
    ADJ_PAR_cols.append('Week_{}_ADJ_PAR'.format(week))

# summing PAR
players['PAR_total'] = players[PAR_cols].sum(axis=1)
players['ADJ_PAR_total'] = players[ADJ_PAR_cols].sum(axis=1)

# slicing off the first 2 rounds because keepers make it different
non_keepers = players[players.Pick > 24]


# graphing total points and pick number
sns.relplot(x = 'Pick', y = 'Total', data=non_keepers)
sns.relplot(x = 'Pick', y = 'ADJ_PAR_total', data=players)


# Unfinished code to get regression curve for pick value

def func(x, a, b, c):
    return a*np.exp(-b*x) + c

def pick_value(x, a, b):
    return a/(x*b)

popt, pcov = curve_fit(pick_value, players.Pick, players.ADJ_PAR_total)

# curve params
p1 = popt[0]
p2 = popt[1]

# plot curve
curvex=np.linspace(15,190,1000)
curvey=pick_value(curvex,p1,p2)
plt.plot(curvex,curvey,'r', linewidth=5)

# future TODO:
#   get data from prior years
#       I have the draft picks
#       might need to pull weekly player stats from another source
#   get better projections
#   WR/RB replacement level incorporating flex realities (not assuming 50% flex for each)


# messing with using API without the wrapper
week = 1
params ={
'scoringPeriodId': week
}
cookies = league.cookies

import requests
year = 2017
url = "https://fantasy.espn.com/apis/v3/games/ffl/leagueHistory/" + \
      str(league_id) + "?seasonId=" + str(year)

r = requests.get(url, params=params, cookies=cookies)
d = r.json()[0]



