import random
import time

MIN_PAUSE_SECONDS = 3
MAX_PAUSE_SECONDS = 15


def pause_between_actions() -> None:
    time.sleep(random.uniform(MIN_PAUSE_SECONDS, MAX_PAUSE_SECONDS))

MIN_APPLICATION_PAUSE_SECONDS = 60
MAX_APPLICATION_PAUSE_SECONDS = 180


def pause_between_applications() -> None:
    time.sleep(random.uniform(MIN_APPLICATION_PAUSE_SECONDS, MAX_APPLICATION_PAUSE_SECONDS))
