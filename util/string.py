def is_empty(string: str):
    return string is None or len(string) == 0


def get_default_if_blank(string: str, default: str = "result"):
    return string if not is_empty(string) else default
