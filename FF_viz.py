"""
This uses an API for ESPN fantasy football to
format data to put into the web service Flourish

Final product is here: https://public.flourish.studio/visualisation/985627/
"""

import pandas as pd
from ff_espn_api import League
from config import USERNAME, PASSWORD

# Initializing settings
weeks_completed = 11
year = 2019
league_id = 291048

# Connecting to league
league = League(league_id=league_id, year=year, username=USERNAME, password=PASSWORD)

# Creating scores dict
scores = {}

for team in league.teams:
    team_name = team.team_name
    logo = team.logo_url
    week_0 = 0
    scores[team.owner] = [team_name, logo, week_0]

# Iterating through teams and weeks
for team in league.teams:
    for week in range(weeks_completed):
        # Get most recent score, 
        # add weekly score, and append    
        current_total = scores[team.owner][-1]
        week_score = team.scores[week]
        new_total = current_total + week_score
        scores[team.owner].append(new_total)

# Converting dict to pandas
df = pd.DataFrame(scores)
df = df.T

# Renaming columns
column_names = ['Team Name', 'Logo', ]
for week in range(weeks_completed+1):
    week = week
    column_names.append('Week {}'.format(week))

df.columns = column_names
df.index.name = 'Owner'

# # Dropping placeholder column
# df.drop(['Placeholder'], axis = 'columns', inplace = True)

# Saving to csv
path = 'FF_{}_week_{}.csv'.format(year, weeks_completed)
df.to_csv(path)








    





    