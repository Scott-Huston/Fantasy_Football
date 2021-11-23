# This is a script to check if waivers have cleared and send an email when they have
# The email is devtest.scott@gmail.com

import smtplib, ssl # for email
from espn_api.football import League
from config import SWID, ESPN_S2
import time
from datetime import datetime
from getpass import getpass


# Email variables
port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = "devtest.scott@gmail.com"  # Enter sender address
receiver_email = "scottphuston@gmail.com"  # Enter receiver address
password = getpass("Type your email password and press enter: ")
message = """\
Subject: ESPN Waivers Cleared

There has been a new transaction.

--This message is sent from Python."""

# League variables
YEAR = 2021
LEAGUE_ID = 291048

# Connecting to league
league = League(swid=SWID, espn_s2=ESPN_S2, year=YEAR, league_id=LEAGUE_ID)

last_transaction = league.recent_activity()[0].actions
newest_transaction = last_transaction

# Checking every minute if there has been a new transaction
while str(newest_transaction) == str(last_transaction):
    
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    
    print(f'No new transactions as of {current_time}')
    time.sleep(60)

    league.refresh()
    newest_transaction = league.recent_activity()[0].actions
    

print('There has been a new transaction')

# Sending email 
context = ssl.create_default_context()
with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, message)
