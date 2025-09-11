from datetime import datetime


def __str__(self):
    return self.strftime("%Y-%m-%d %H:%M:%S")


def get_file_suffix(date: datetime = datetime.now()):
    return date.strftime("%Y-%m-%d_%H-%M-%S")


def to_directory_suffix(date: datetime = datetime.now()):
    return date.strftime("%Y-%m-%d")


NOW = datetime.now()
TODAY = datetime.today()