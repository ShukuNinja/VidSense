import os
import re


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def get_unique_filepath(title, folder, extension):
    os.makedirs(folder, exist_ok=True)

    base_name = sanitize_filename(title)
    filename = f"{base_name}{extension}"
    counter = 1

    while os.path.exists(os.path.join(folder, filename)):
        filename = f"{base_name}_{counter}{extension}"
        counter += 1

    return os.path.abspath(os.path.join(folder, filename))