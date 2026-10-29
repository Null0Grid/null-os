#!/usr/bin/env python3
# Null OS installer marker: tell the slideshow which step is running.
# Writes globalstorage "nullStage" (the instance's stage id) and
# "nullStageStarted" (seconds since the epoch). Never fails.
import time

import libcalamares


def pretty_name():
    return libcalamares.job.configuration.get("label", "Null OS")


def run():
    try:
        gs = libcalamares.globalstorage
        gs.insert("nullStage", libcalamares.job.configuration.get("stage", ""))
        gs.insert("nullStageStarted", time.time())
    except Exception as e:  # the slideshow is cosmetic; the install goes on
        libcalamares.utils.warning(f"nullstage: {e}")
    return None
