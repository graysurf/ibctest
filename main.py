import configparser
import os
import random
import time
from datetime import datetime
import json
import re
from functional import seq
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.keys import Keys

import log
from driver import get_driver, handle_alert, interrupted
import db

parser = configparser.ConfigParser()
parser.read(os.path.realpath("config"))
default_parser = parser[configparser.DEFAULTSECT]
config = {
    "sleep_time": default_parser["sleep_time"],
    "url": default_parser["url"],
    "id": json.loads(default_parser["id"]),
    "pwd": default_parser["pwd"],
    "time": default_parser["time"],
    "bet_type": default_parser["bet_type"],
}

file_logger = log.get_file_logger("main")
logger = log.get_logger("main")

headers = {}


def is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()


def init_page(driver):
    logger.info("web driver init")
    base_url = config["url"]
    logger.info("loading URL...")
    driver.get(base_url)

    # go to login page
    driver.implicitly_wait(3)
    login_btn = driver.find_element_by_class_name("btn-highlight")
    login_btn.click()

    # login
    id_input = driver.find_element_by_id("txtID")
    id_input.send_keys(config["id"][random.randint(0, 2)])
    pwd_input = driver.find_element_by_id("txtPW")
    pwd_input.send_keys(config["pwd"])
    submit_btn = driver.find_element_by_class_name("login__item-btn")
    submit_btn.click()
    logger.info("login finished")

    # select time
    time_xpath = "//span[@class='text' and contains(text(),'{}')]".format(
        config["time"]
    )
    wait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, time_xpath)))
    time_btn = driver.find_element_by_xpath(time_xpath)
    logger.info("selected time: %s", config["time"])
    time_btn.click()

    # select bet type
    try:
        bettype_xpath = "//span[@class='betTypeName' and @title='{}']".format(
            config["bet_type"]
        )
        wait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, bettype_xpath)))
        bettype_btn = driver.find_element_by_xpath(bettype_xpath)
        logger.info("selected bet_type: %s", config["bet_type"])
        bettype_btn.click()
    except Exception as e:
        file_logger.warning(e)
        logger.warning(e)
    time.sleep(10)


def logws(driver):
    received = 0
    for wsData in driver.get_log("performance"):
        # print(wsData)
        wsJson = json.loads((wsData["message"]))
        if wsJson["message"]["method"] == "Network.webSocketFrameReceived":
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
                    headers[id] = header
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
                objs = list(
                    map(
                        lambda lst: {lst[i]: lst[i + 1] for i in range(0, len(lst), 2)},
                        records,
                    )
                )

                f_m = lambda o: o.get("type") == "m" or o.get("type") == "dm"
                f_m_infos = (
                    lambda o: o.get("matchid")
                    and o.get("leagueid")
                    and o.get("sporttype")
                    and o.get("awayid")
                    and o.get("homeid")
                )
                f_m_events = (
                    lambda o: o.get("matchid")
                    and not o.get("leagueid")
                    and not o.get("sporttype")
                    and not o.get("awayid")
                    and not o.get("homeid")
                )

                f_o = lambda o: o.get("type") == "o" or o.get("type") == "do"
                f_o_infos = (
                    lambda o: o.get("matchid") and o.get("oddsid") and o.get("bettype")
                )
                f_o_events = (
                    lambda o: o.get("oddsid")
                    and not o.get("matchid")
                    and not o.get("bettype")
                )

                # f_dm_events = lambda o: o.get("type") == "dm"
                # f_do_events = lambda o: o.get("type") == "do"

                received_timestamp = time.time()
                formated_time = datetime.fromtimestamp(received_timestamp).strftime(
                    "%Y%m%d%H%M%f"
                )

                def setTime(obj):
                    obj["receiveTimestamp"] = int(received_timestamp * 1000)
                    obj["dateTime"] = formated_time
                    return obj

                html = driver.page_source
                data_socket = {
                    "data": '42["m",["b{id}",{records}]'.format(
                        id=id, records=json.dumps(records, ensure_ascii=False)
                    ),
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

                data_match_data = list(
                    seq(objs).filter(f_m).filter(f_m_infos).map(setTime)
                )

                received += len(data_match_data)

                if len(data_match_data):
                    logger.info("get match_data %s rows", len(data_match_data))
                    db.save_matchid(data_match_data)
                    # db.col_odds.insert_many(data_odds)

                data_match_events = list(
                    seq(objs).filter(f_m).filter(f_m_events).map(setTime)
                )
                if len(data_match_events):
                    logger.info("write match_events %s rows", len(data_match_events))
                    db.col_match_events.insert_many(data_match_events)

                data_odds = list(seq(objs).filter(f_o).filter(f_o_infos).map(setTime))
                if len(data_odds):
                    logger.info("get odds_data %s rows", len(data_odds))
                    db.save_oddid(data_odds)

                data_odds_events = list(
                    seq(objs).filter(f_o).filter(f_o_events).map(setTime)
                )
                if len(data_odds_events):
                    logger.info("write odds_events %s rows", len(data_odds_events))
                    db.col_odds_events.insert_many(data_odds_events)

        if wsJson["message"]["method"] == "Network.webSocketFrameSent":
            # logger.info("webSocketFrameSent")
            logger.info("Tx :" + wsJson["message"]["params"]["response"]["payloadData"])
    return received


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
    for record in (
        record
        for record in rows
        if is_integer(record[0]) and record != [0, "reset"] and record != [0, "done"]
    ):
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
    sleep_time = config["sleep_time"]
    driver = get_driver()
    try:
        init_page(driver)
        logger.info("init finished")
        received = 0
        for i in range(3):
            received += logws(driver)
            if received > 0:
                break
            logger.info("refresh page...")
            driver.refresh()
            time.sleep(10)
        if received == 0:
            file_logger.info("no received data")
            logger.info("no received data")
            driver.quit()
            return
        body = driver.find_element_by_css_selector("body")
        body.click()
        for i in range(3600):
            driver = handle_alert(driver, init_page)
            logws(driver)
            time.sleep(int(sleep_time))
            if i % 200 < 100:
                body.send_keys(Keys.PAGE_DOWN)
            else:
                body.send_keys(Keys.PAGE_UP)
    except Exception as e:
        file_logger.error(e)
        logger.error(e)
        driver.quit()
        if interrupted():
            return
    driver.quit()


while not interrupted():
    try:
        main()
        logger.info("sleep 10 second....")
        time.sleep(10)
        logger.info("restart chrome...")
    except Exception as e:
        file_logger.error(e)
        logger.error(e)
