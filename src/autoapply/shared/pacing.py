import random
import time

MIN_PAUSE_SECONDS = 3
MAX_PAUSE_SECONDS = 15


def pause_between_actions() -> None:
    time.sleep(random.uniform(MIN_PAUSE_SECONDS, MAX_PAUSE_SECONDS))
