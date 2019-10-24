import os


def create_path(*args):
    return os.path.normpath(os.path.join(*args)).replace('\\', '/')

