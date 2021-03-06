import configparser
import os
import json

parser = configparser.ConfigParser()
parser.read(os.path.realpath("config"))
default_parser = parser[configparser.DEFAULTSECT]

sleep_time = default_parser["sleep_time"]
enable_log_html = default_parser.getboolean("enable_log_html")
html_folder = default_parser["html_folder"]
url = default_parser["url"]
id = json.loads(default_parser["id"])
pwd = default_parser["pwd"]
time = default_parser["time"]
bet_type = default_parser["bet_type"]
api_endpoint = default_parser["api_endpoint"]
db_endpoint = default_parser["db_endpoint"]
