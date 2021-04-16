import os
from datetime import datetime

import config


def create_folder():
    dir = "{}/{}".format(config.html_folder, datetime.now().strftime("%Y%m%d/%H"))
    if not os.path.exists(dir):
        os.makedirs(dir)
    return dir


def write_file(filename, file):
    if config.enable_log_html:
        dir = create_folder()
        with open("{}/{}".format(dir, filename), "w") as writer:
            writer.write(file)
            writer.flush()
            writer.close()
