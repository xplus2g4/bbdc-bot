import logging
import os
import sys
from functools import lru_cache

import yaml

CONFIG_PATH = os.getenv("CONFIG_PATH", "config/example.yaml")


@lru_cache(maxsize=1)
def load_config():
    data = None
    with open(CONFIG_PATH, "r") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logging.error(exc)
            sys.exit(1)
    return data


if __name__ == "__main__":
    print(load_config())
