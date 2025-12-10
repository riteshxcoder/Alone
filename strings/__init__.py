#
# Copyright (C) 2021-2022 by TheAloneteam@Github, < https://github.com/TheAloneTeam >.
#
# This file is part of < https://github.com/TheAloneTeam/AloneMusic > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TheAloneTeam/AloneMusic/blob/master/LICENSE >
#
# All rights reserved.

import os
import sys

import yaml

languages: dict = {}
languages_present: dict = {}


def get_string(lang: str):
    return languages[lang]


LANG_PATH = "./strings/langs/"

for filename in os.listdir(LANG_PATH):
    if "en" not in languages:
        languages["en"] = yaml.safe_load(
            open(os.path.join(LANG_PATH, "en.yml"), encoding="utf8")
        )
        languages_present["en"] = languages["en"]["name"]

    if not filename.endswith(".yml"):
        continue

    language_name = filename[:-4]

    if language_name == "en":
        continue

    languages[language_name] = yaml.safe_load(
        open(os.path.join(LANG_PATH, filename), encoding="utf8")
    )

    for item in languages["en"]:
        if item not in languages[language_name]:
            languages[language_name][item] = languages["en"][item]

    # ✅ FIXED: No bare except
    try:
        languages_present[language_name] = languages[language_name]["name"]
    except KeyError:
        print(
            f"Language file '{filename}' is missing required key: 'name'",
            file=sys.stderr,
        )
        sys.exit(1)
