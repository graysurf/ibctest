import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["cmd-spider"]

col_socket = db["socket-data"]

col_match_data = db["match-data"]
col_match_events = db["matchEvent-data"]

col_odds = db["odds-data"]
col_odds_events = db["oddsEvent-data"]


