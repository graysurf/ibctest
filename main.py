import configparser
import itertools
import os
import time
from datetime import datetime
import json
import re
from functional import seq
import numpy as np

import log
from driver import get_driver
import db


parser = configparser.ConfigParser()
parser.read(os.path.realpath('config'))
default_parser = parser[configparser.DEFAULTSECT]
config = {
    'sleep_time': default_parser["sleep_time"],
    'url': default_parser["url"],
    'id': default_parser["id"],
    'pwd': default_parser["pwd"],
    'time': default_parser["time"],
    'bet_type': default_parser["bet_type"]
}

logger = log.get_logger("main")
driver = get_driver()
headers = {}

def is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()

def init_page() :
    logger.info("Web driver Init")
    base_url = config["url"]
    logger.info('Loading URL ....')
    driver.get(base_url)

    # go to login page
    driver.implicitly_wait(3)
    login_btn = driver.find_element_by_class_name("btn-highlight")
    login_btn.click()

    # login
    id_input = driver.find_element_by_id("txtID")
    id_input.send_keys(config["id"])
    pwd_input = driver.find_element_by_id("txtPW")
    pwd_input.send_keys(config["pwd"])
    submit_btn = driver.find_element_by_class_name("login__item-btn")
    submit_btn.click()
    logger.info("login finished")

    # select time
    driver.implicitly_wait(5)
    logger.info(driver.page_source)
    time_btn = driver.find_element_by_xpath("//span[@class='text' and contains(text(),'{}')]".format(config["time"]))
    time_btn.click()
    logger.info("selected time: %s", config["time"])

    # # select bet type
    driver.implicitly_wait(5)
    bettype_btn = driver.find_element_by_xpath("//span[@class='betTypeName' and contains(text(),'{}')]".format(config["bet_type"]))
    bettype_btn.click()
    logger.info("selected bet_type: %s", config["bet_type"])

def logws():
    for wsData in driver.get_log('performance'):
        # print(wsData)
        wsJson = json.loads((wsData['message']))
        if wsJson["message"]["method"]== "Network.webSocketFrameReceived":
            # logger.info("webSocketFrameReceived")
            # print("Rx :", str(wsJson["message"]["params"]["timestamp"]), wsJson["message"]["params"]["response"]["payloadData"])
            # 96116.031204, 42["m","b1",[[0,"c",2,"m0",3,"L",4,2,5,"ALL",6,8],[0,"c",2,"m0",3,"L",4,2,5,"HDPOU1",6,8],[0,"c",1,"m0.L.164.ALL",2,"m0",3,"L",4,164,5,"ALL",6,0,7,false]],"DbirQ"]
            timestamp = str(wsJson["message"]["params"]["timestamp"])
            message = wsJson["message"]["params"]["response"]["payloadData"]
            p = re.compile('^42\["m","b(\d{1,2})",\[\[("c"|0)')
            find = p.findall(message)
            if len(find) == 0:
                continue
            id = find[0][0]
            format = find[0][1]
            records = []
            # update header
            if format == '"c"':
                raw = json.loads(message[2:])[2][1:]
                header = parse_header(raw)
                logger.info("updated header %s, %s", id, header)
                if header != []:
                    headers[id] =  header
                    records = parse_header_row(raw, header)

            # get record
            elif is_integer(format):
                raw = json.loads(message[2:])
                header = headers[id]
                records = parse_record(raw[2], header)

            else:
                logger.warn("not match: %s.....", message[:100])

            if len(records) > 0:
                 # ['type', 'o', 'oddsid', 321577036, 'odds1a', 0.67, 'odds2a', -0.97]
                objs = list(map(lambda lst: {lst[i]: lst[i + 1] for i in range(0, len(lst), 2)}, records))

                f_m = lambda o: o.get("type") == "m" or \
                    o.get("type") == "dm"
                f_m_infos = lambda o: o.get("matchid") and \
                    o.get("leagueid") and \
                    o.get("sporttype") and \
                    o.get("awayid") and \
                    o.get("homeid")
                f_m_events = lambda o: o.get("matchid") and \
                    not o.get("leagueid") and \
                    not o.get("sporttype") and \
                    not o.get("awayid") and \
                    not o.get("homeid")

                f_o = lambda o: o.get("type") == "o" or \
                    o.get("type") == "do"
                f_o_infos = lambda o: o.get("matchid") and \
                    o.get("oddsid") and \
                    o.get("bettype")
                f_o_events = lambda o: o.get("oddsid") and \
                    not o.get("matchid") and \
                    not o.get("bettype")

                # f_dm_events = lambda o: o.get("type") == "dm"
                # f_do_events = lambda o: o.get("type") == "do"

                received_timestamp = time.time()
                formated_time = datetime.fromtimestamp(received_timestamp).strftime("%Y%m%d%H%M%f")
                def setTime(obj):
                    obj["receiveTimestamp"] = int(received_timestamp * 1000)
                    obj["dateTime"] = formated_time
                    return obj

                html = driver.page_source
                data_socket = {
                    "data": '42["m",["b{id}",{records}]'.format(id = id, records = json.dumps(records, ensure_ascii=False)),
                    "originalData": message,
                    "timeStamp": int(received_timestamp * 1000),
                    "length": len(objs),
                    "time": received_timestamp,
                    "html": html,
                    # "events": objs,
                    "sportbettype": config["bet_type"],
                    "sportmenunavtype": config["time"],
                    "title": header,
                }
                db.col_socket.insert_one(data_socket)

                data_match_data = list(seq(objs).filter(f_m).filter(f_m_infos).map(setTime))
                if len(data_match_data):
                    logger.info("get match_data %s rows", len(data_match_data))
                    db.save_matchid(data_match_data)
                    # db.col_odds.insert_many(data_odds)

                data_match_events = list(seq(objs).filter(f_m).filter(f_m_events).map(setTime))
                if len(data_match_events):
                    logger.info("write match_events %s rows", len(data_match_events))
                    db.col_match_events.insert_many(data_match_events)

                data_odds = list(seq(objs).filter(f_o).filter(f_o_infos).map(setTime))
                if len(data_odds):
                    logger.info("get odds_data %s rows", len(data_odds))
                    db.save_oddid(data_odds)

                data_odds_events = list(seq(objs).filter(f_o).filter(f_o_events).map(setTime))
                if len(data_odds_events):
                    logger.info("write odds_events %s rows", len(data_odds_events))
                    db.col_odds_events.insert_many(data_odds_events)


        if wsJson["message"]["method"] =="Network.webSocketFrameSent":
            # logger.info("webSocketFrameSent")
            logger.info("Tx :"+ wsJson["message"]["params"]["response"]["payloadData"])

def parse_header(rows):
    header = []
    # 42["m","b9",[["c","c4","c3b8e2a1-r3","cdf55c8e34ee810b-b9"],["f",0,["type","oddsid",.....
    for raw in rows:
        if raw[0] != "f":
            break
        header.extend(raw[2])
    return header

def parse_header_row(rows, header):
    output = []
    for record in (record for record in rows if is_integer(record[0]) and record != [0, "reset"] and record != [0, "done"]):
        for idx in range(0, len(record), 2):
            record[idx] = header[record[idx]]
            output.append(record)
    return output

def parse_record(rows, header):
    # 42["m","b4",[[0,"o",3,318289758,1,41923191,.....
    for record in rows:
        for idx in range(0, len(record), 2):
            record[idx] = header[record[idx]]
    return rows


def main():
    init_page()
    time.sleep(30)
    logger.info("init finished...")
    sleep_time = config["sleep_time"]
    while True:
        # logger.info("sleeping {} seconds".format(sleep_time))
        time.sleep(int(sleep_time))
        logws()
    logger.info("done")


main()

