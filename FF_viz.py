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
# Have this week's scores been uploaded to team.scores?
uploaded = False

# Connecting to league
league = League(league_id=league_id, year=year, username=USERNAME, password=PASSWORD)

# Names dict translates between ESPN owners and names displayed
names = {
    'Trevor Baker':'Trevor',
    'Andrew Knauer':'Knauer',
    'Nick Pawker':'Nick',
    'Todd Matsuura':'Todd',
    'mark petrusich':'Mark',
    'Jeff Garavaglia':'Jeff',
    'Derek Tsukahira':'Derek',
    'Andrew Badroos':'Bad',
    'Scott Huston':'Scott',
    'chris grove':'Grove',
    'Pick Narker':'Matt',
    'Holden Tikkanen':'Holden'
    }

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

# Iterating through teams and weeks, appending
# weekly total points scored
for team in league.teams:
    for week in range(weeks_completed):
        name = names.get(team.owner)    
        week_score = team.scores[week]
        append_score(name, week_score)

# Getting this week's scores if week hasn't ended
if uploaded == False:
    for score in league.box_scores():
        home_name = names.get(score.home_team.owner)
        away_name = names.get(score.away_team.owner)
        home_score = score.home_score
        away_score = score.away_score

        append_score(home_name, home_score)
        append_score(away_name, away_score)

# Converting dict to pandas
df = pd.DataFrame(scores)
df = df.T

# Renaming columns
column_names = ['Team Name', 'Logo', ]
for week in range(weeks_completed+1):
    week = week
    column_names.append('Week {}'.format(week))

if uploaded == False:
    column_names.append('Week {}'.format(weeks_completed+1))

df.columns = column_names
df.index.name = 'Owner'

# Saving to csv
path = 'FF_{}_week_{}.csv'.format(year, weeks_completed)
df.to_csv(path)








    





    