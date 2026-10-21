from enum import StrEnum


class PageState(StrEnum):
    LOGGED_IN = "LOGGED_IN"
    LOGGED_OUT = "LOGGED_OUT"
    CHECKPOINT = "CHECKPOINT"
    UNKNOWN = "UNKNOWN"


class LoginTimeout(Exception):
    pass


class SessionExpired(Exception):
    pass


class CheckpointDetected(Exception):
    pass


class UnknownPageState(Exception):
    pass
