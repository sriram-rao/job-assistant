def is_empty(string: str):
    return string is None or len(string) == 0


def get_default_if_blank(string: str, default: str = "result"):
    return string if not is_empty(string) else default


def pad(string: str, left_padding: str = "%%", right_padding: str = ""):
    return left_padding + string + (left_padding if is_empty(right_padding) else right_padding)
    
