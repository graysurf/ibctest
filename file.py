import os
import configparser
from datetime import datetime


parser = configparser.ConfigParser()
parser.read(os.path.realpath("config"))
default_parser = parser[configparser.DEFAULTSECT]
base_path = default_parser["folder"]


def create_folder():
    dir = "{}/{}".format(base_path, datetime.now().strftime("%Y%m%d/%H"))
    if not os.path.exists(dir):
        os.makedirs(dir)
    return dir


def write_file(filename, file):
    dir = create_folder()
    with open("{}/{}".format(dir, filename), "w") as writer:
        writer.write(file)
        writer.flush()
        writer.close()
