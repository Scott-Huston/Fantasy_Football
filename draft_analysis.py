import pandas as pd
import numpy as np
from ff_espn_api import League
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from config import USERNAME, PASSWORD
from names import names

# initializing settings
year = 2019
league_id = 291048

# connecting to league
league = League(league_id=league_id, year=year, username=USERNAME, password=PASSWORD)
weeks_completed = league.nfl_week

# initializing players dict
players = {}

##########################################
######### Loading data from ESPN #########
##########################################

# adding all drafted players to players dict
pick = 1
for player in league.draft:
    name = player.playerName
    owner = names[player.team.owner]
    keeper = player.keeper_status
    players[name] = [pick, owner, keeper, 'POSITION_PLACEHOLDER']
    pick += 1

def update_players(player, week):
    if player.name not in players.keys():
        players[player.name] = [np.NaN]*(4*(week-1)+4)
        players[player.name][0] = np.NaN
        players[player.name][3] = player.position

    players[player.name].extend([
        player.points, player.pro_pos_rank, \
        player.projected_points, player.slot_position
        ])
    players[player.name][3] = player.position


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
        
        assert len(players[player]) == (week*4+4), \
            "Player, {} doesn't match after week {}".format(player, week)


##########################
### Cleaning dataframe ###
##########################

# converting to pandas DataFrame
players = pd.DataFrame(players)
players = players.T

# naming columns and getting lists 
column_names = ['Pick', 'Owner', 'Keeper', 'Position']

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

##############################
##### Evaluating Players #####
##############################

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
            position_players = players[players['Position']==position]
            position_players = position_players.sort_values( \
                                    by=['Week_{}_proj_points'.format(week)], \
                                    ascending=False)

            # get the replacement rank (ie, 12 for QBs, 30 for RBs)
            # Note: because dataframes are zero-indexed, the code sets the 
            # rank+1 best projected player as replacement level
            replacement_rank = replacement_ranks[position]

            baseline_player = position_players.iloc[replacement_rank]
            proj_points = baseline_player['Week_{}_proj_points'.format(week)]

            # if proj points is null or 0 for nth best projection, just take the lowest projected value that isn't 0 
            # this really only effects kickers
            if pd.isna(proj_points) or proj_points==0:
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
    """
    Not penalizing players for being bad/injured when we 
    know they're going to be bad/injured

    That shouldn't count as below replacement level because we know
    to replace them
    """

    replacement_level = replacement_levels[position][week-1]

    top_replacement = replacement_level*1.1
    bottom_replacement = replacement_level*.9

    # estimating probability player is started in a lineup
    # probability linearly increases from 0 at a projection 10% lower than replacement level
    # to 1 at a projection 10% higher than replacement level
    start_prob = (1/(top_replacement-bottom_replacement))*(projection-bottom_replacement)

    # if projection is not within +-10% of replacement level, assume they are definitely playing
    # or definitely not playing
    if projection < bottom_replacement:
        start_prob = 0
    
    if projection > top_replacement:
        start_prob = 1
    
    # getting PAR and adjusting for start probability
    PAR = points - replacement_level
    ADJ_PAR = PAR*start_prob
    
    return ADJ_PAR

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

# getting df with only drafted players
draft = players.dropna(subset=['Pick'])

############################################################
#### Getting adjusted pick numbers for first two rounds ####
############################################################

# getting names of players in first 2 rounds
first_2_rounds_players = set(players.iloc[:24].index)

# dict for fixing naming issues between ecr list and ESPN data
rename = {
    'Todd Gurley II' : 'Todd Gurley',
    'Le\'Veon Bell' : 'LeVeon Bell',
    'Odell Beckham Jr.' : 'Odell Beckham'
}

for key in rename.keys():
    first_2_rounds_players.remove(key)
    first_2_rounds_players.add(rename[key])

# reading in pre-draft expert consensus draft rankings
ecr = pd.read_csv('Beersheets_ECR.csv')

# filtering to only players taken in first 2 rounds
filtered_ecr = ecr[ecr['NAME'].isin(first_2_rounds_players)]
assert len(filtered_ecr) == 24, 'filtered_ecr length is not equal to 24'

def get_overall_ECR(ECR):
    # returns overall pick number implied by ECR
    ECR = str(ECR)
    round, pick_in_round = ECR.split('.')
    overall = (int(round)-1)*12 + int(pick_in_round)
    return overall

filtered_ecr['OVR'] = filtered_ecr.ECR.apply(get_overall_ECR)

# ordering by ECR (ascending), then VAL (descending)
filtered_ecr = filtered_ecr.sort_values(by=['OVR', 'VAL'], ascending=[True, False])
# reset index
filtered_ecr.reset_index(drop=True, inplace=True)
# getting ADJ_Pick values
filtered_ecr['ADJ_PICK'] = filtered_ecr.index+1
# set name to index
filtered_ecr.set_index('NAME', inplace=True)

# creating ADJ_Pick column
def get_adj_pick(player_name):
    """
    Since keepers throw off the draft order for the first two rounds,
    I'm creating an adj_pick column with the order the players taken in
    the first two rounds were projected to get taken in. Both keeper and
    non-keeper players are effected because non-keeper picks would likely
    have been different players if keeper players had been available
    """

    # renames certain players to fix naming discrepancies
    # between datasources
    if player_name in rename.keys():
        ecr_player_name = rename[player_name]
    else:
        ecr_player_name = player_name

    pick = draft.loc[player_name].Pick

    # if not in the first two rounds, just return the actual pick number
    if pick > 24:
        return pick

    adj_pick = filtered_ecr.loc[ecr_player_name].ADJ_PICK
    return adj_pick

draft['ADJ_Pick'] = draft.index.map(get_adj_pick)

#######################################################################
# Getting regression curve to estimate ADJ_PAR_total by pick position #
#######################################################################

def exp_decay(x, a, r, c):
    return a*np.power(1-r, x)+c

# fitting curve to the data
guess = [10, .05, 0] # initial parameters for curve_fit
popt, pcov = curve_fit(exp_decay, draft.ADJ_Pick, draft.ADJ_PAR_total, p0=guess)

# curve params
a = popt[0]
r = popt[1]
c = popt[2]

# returns estimated ADJ_PAR for a given overall pick number
def pick_value(pick):
    return a*np.power(1-r, pick)+c

# creates scatterplot with picks and best fit curve
def plot_pick_values():
    curve_x=np.linspace(1,190,190)
    curve_y=pick_value(curve_x)

    sns.relplot(x = 'ADJ_Pick', y = 'ADJ_PAR_total', data=draft)
    plt.plot(curve_x,curve_y,'r', linewidth=5)
    plt.plot()

# calculating player value compared to where they were drafted (adjusted for keepers)
draft['Pick_value'] = draft.ADJ_Pick.apply(pick_value)
draft['ADJ_PAR_over_pick_pos'] = draft.ADJ_PAR_total - draft.Pick_value

# TODO add total points
best_picks = draft.sort_values(by='ADJ_PAR_over_pick_pos', ascending=False).head(10)
best_picks = best_picks[['Pick', 'Owner', 'Position', 'ADJ_PAR_over_pick_pos', 'ADJ_PAR_total']+points_list]

worst_picks = draft.sort_values(by='ADJ_PAR_over_pick_pos').head(10)
worst_picks = worst_picks[['Pick', 'Owner', 'Position','ADJ_PAR_over_pick_pos', 'ADJ_PAR_total']+points_list]

# future TODO:
#   get data from prior years
#       I have the draft picks
#       might need to pull weekly player stats from another source
#   get better projections
#   WR/RB replacement level incorporating flex realities (not assuming 50% flex for each)
#   break apart code to pull espn info and just read from df
