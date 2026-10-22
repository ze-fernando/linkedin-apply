import random
import time

MIN_PAUSE_SECONDS = 3
MAX_PAUSE_SECONDS = 15
MIN_STEP_PAUSE_SECONDS = 2
MAX_STEP_PAUSE_SECONDS = 6
MIN_APPLICATION_PAUSE_SECONDS = 20
MAX_APPLICATION_PAUSE_SECONDS = 60


def pause_between_actions() -> None:
    time.sleep(random.uniform(MIN_PAUSE_SECONDS, MAX_PAUSE_SECONDS))


def pause_between_steps() -> None:
    time.sleep(random.uniform(MIN_STEP_PAUSE_SECONDS, MAX_STEP_PAUSE_SECONDS))


def pause_between_applications() -> None:
    time.sleep(random.uniform(MIN_APPLICATION_PAUSE_SECONDS, MAX_APPLICATION_PAUSE_SECONDS))
