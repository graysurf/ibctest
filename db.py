import pymongo

import log

logger = log.get_logger("db")

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["cmd-spider"]

col_socket = db["socket-data"]

col_match_data = db["match-data"]
col_match_events = db["matchEvent-data"]

col_odds_data = db["odds-data"]
col_odds_events = db["oddsEvent-data"]

matchset = set()


def save_matchid(matches):
    for match in matches:
        matchid = match["matchid"]
        if (
            matchid not in matchset
            and col_match_data.find_one({"matchid": matchid}) is None
        ):
            logger.info("write match: %s", matchid)
            matchset.add(matchid)
            col_match_data.insert_one(match)


oddsset = set()


def save_oddid(oddses):
    for odds in oddses:
        oddsid = odds["oddsid"]
        if oddsid not in oddsset and col_odds_data.find_one({"oddsid": oddsid}) is None:
            logger.info("write odds: %s", oddsid)
            oddsset.add(oddsid)
            col_odds_data.insert_one(odds)
