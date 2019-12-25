"""
This uses an API for ESPN fantasy football to
format data to put into the web service Flourish

Final product is here: https://public.flourish.studio/visualisation/985627/
"""

import pandas as pd
from ff_espn_api import League
from config import USERNAME, PASSWORD
from names import names # dictionary to convert ESPN owner names to displayed names

# Initializing settings
year = 2019
league_id = 291048

# Connecting to league
league = League(league_id=league_id, year=year, username=USERNAME, password=PASSWORD)
weeks_completed = league.nfl_week

# Initializing scores dict
scores = {}

for team in league.teams:
    team_name = team.team_name
    logo = team.logo_url
    week_0 = 0
    name = names.get(team.owner)
    scores[name] = [team_name, logo, week_0]

# Function takes previous total and adds
# entry for previous total + weekly score
def append_score(name, score):
    current_total = scores[name][-1]
    new_total = current_total+score
    scores[name].append(new_total)

# Adding this week's scores if week hasn't ended
for week in range(1, weeks_completed+1):
    for score in league.box_scores(week):
        home_name = names.get(score.home_team.owner)
        home_score = score.home_score
        append_score(home_name, home_score)

        # checking if there is an away team
        # there is no away team for bye weeks
        if score.away_team:
            away_name = names.get(score.away_team.owner)
            away_score = score.away_score
            append_score(away_name, away_score)
        
# Converting dict to pandas
df = pd.DataFrame(scores)
df = df.T

# Renaming columns
column_names = ['Team Name', 'Logo']
for week in range(weeks_completed+1):
    week = week
    column_names.append('Week {}'.format(week))

df.columns = column_names
df.index.name = 'Owner'

# Saving to csv
path = 'FF_{}_week_{}.csv'.format(year, weeks_completed)
df.to_csv(path)








    





    