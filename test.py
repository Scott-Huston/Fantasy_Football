from espn_api.football import League
from config import SWID, ESPN_S2

# Initializing settings
YEAR = 2021
LEAGUE_ID = 291048

# Connecting to league

league = League(swid=SWID, espn_s2=ESPN_S2, year=YEAR, league_id=LEAGUE_ID)

print(dir(league))