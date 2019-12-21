import pandas as pd
from ff_espn_api import League
from config import USERNAME, PASSWORD
import seaborn as sns

# Initializing settings
year = 2019
league_id = 291048

# Connecting to league
league = League(league_id=league_id, year=year, username=USERNAME, password=PASSWORD)
weeks_completed = league.nfl_week

# initializing all_players
all_players = {}

# initializing draft_picks dict
draft_picks = {}

pick = 1
for player in league.draft:
    name = player.playerName
    draft_picks[name] = [pick, 'POSITION_PLACEHOLDER']
    pick += 1

def update_all_players(player, week):
    if player.name not in all_players.keys():
        all_players[player.name] = [0]*week
        all_players[player.name][0] = player.position

    all_players[player.name].append(player.points)

def update_draft_picks(player, week):
    if player.name in draft_picks.keys():
        draft_picks[player.name].append(player.points)
        draft_picks[player.name][1] = player.position


# iterating through weeks, matchups, and players to 
# append weekly points for each player
for week in range(1, weeks_completed):
    for matchup in league.box_scores(week):
        for player in matchup.home_lineup:
            update_all_players(player, week)
            update_draft_picks(player, week)
        for player in matchup.away_lineup:
            update_all_players(player, week)
            update_draft_picks(player, week)
    
    # adding zero scores for players not in lineups
    for player in draft_picks.keys():
        if len(draft_picks[player]) == week+1:
            draft_picks[player].append(pd.np.NaN)
    
    for player in all_players.keys():
        if len(all_players[player]) == week:
            all_players[player].append(pd.np.NaN)

# converting to pandas DataFrame
draft = pd.DataFrame(draft_picks)
draft = draft.T

all = pd.DataFrame(all_players)
all = all.T

# naming columns
column_names = ['Pick', 'Position']
for week in range(1, weeks_completed):
    column_names.append('Week {}'.format(week))

draft.columns = column_names
all.columns = column_names[1:]

# slicing off the first 2 rounds because keepers make it different
non_keepers = draft.iloc[24:]

# summing to get season total
non_keepers['Total'] = non_keepers.loc[:,'Week 1' :].sum(axis=1)
draft['Total'] = draft.loc[:,'Week 1' :].sum(axis=1)

# graphing total points and pick number
sns.relplot(x = 'Pick', y = 'Total', data=non_keepers)
sns.relplot(x = 'Pick', y = 'Total', data=draft)





# TODO need positional baselines
# Use projected points?
# Looking into what FA adds do
activity = league.recent_activity(1000)
adds = 
for entry in activity:
    for action in entry.actions:
        if action[1] == 'FA ADDED':
            name = action[2]
            adds.append(name)



# TODO get data from prior years




