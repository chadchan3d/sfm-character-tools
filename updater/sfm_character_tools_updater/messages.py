# -*- coding: utf-8 -*-
"""Truthful outcome text (R2 C12, Amendment §2.1) and the backend's stop exception."""

MESSAGES = {
    "NOTHING": "Nothing was installed.",
    "INSTALLED": "Installation complete.",
    "RECOVERED": "Installation recovered.",
    "RESTORED": "Your previous files were restored.",
    "TXT_CHANGED": "Your TXT changed after the interruption. Choose which version to keep.",
    "MISSING": "Automatic recovery is unavailable; required files are missing.",
    "FOLDER_CHANGED": "The data folder changed. No files were overwritten.",
    "UNKNOWN_SCHEMA": "Use a compatible updater to recover this installation.",
    "NOOP": "Already installed; nothing changed.",
    # L-1 additions (Amendment §2.1 steps 4, 6 and 7; §2.3)
    "CLOSE_SFM": "Close SFM and try again. Nothing was changed.",
    "PREPARED": "Your data is prepared. Close SFM, then install.",
    "PREPARE_AGAIN": "The prepared data no longer matches this installation. Prepare it again. Nothing was changed.",
    "PATH_TOO_LONG": "This installation's folder path is too long for the SFM tools to read. Nothing was changed.",
    "UNVERIFIED": "The installation finished, but the installed files could not be verified. "
                  "Do not use the Character Tools until the data is rebuilt or recovered.",
    "RESTART_RUNNING": "SFM was started during installation. Close and reopen SFM before using the Character Tools.",
    "RESTART_UNKNOWN": "SFM's state could not be confirmed. If SFM is open, close and reopen it before using "
                       "the Character Tools.",
    "REOPEN": "You can now reopen SFM.",
    "NEEDS_REBUILD": "Your previous files were restored; the data still needs rebuilding.",
    "DEPENDENCY": "Updater components failed verification. Nothing was changed.",
    "STOPPED": "Stopped before completion; nothing reported as installed. Run recovery.",
    "RECOVERY_STOPPED": "Recovery stopped before completion; run recovery again.",
    "ERROR": "Unexpected error; state preserved, not reported as success.",
    # L-2 additions. Each answers: what does this do / what happened to my files / what to do next.
    "DESTINATION_CHANGED": "The animation-group TXT in this SFM installation changed after it was checked. "
                           "Nothing was changed. Check again before installing.",
    "NEEDS_CONSENT": "Nothing was changed. Installing this replaces the animation-group TXT in this SFM "
                     "installation. Confirm the replacement to continue.",
    "PREPARED_IMPORT": "The TXT you chose is checked and ready. Installing it replaces the animation-group TXT in "
                       "this SFM installation; your current TXT is kept as a backup. Close SFM, then install.",
    "PREPARED_OFFICIAL": "Official data %s is checked and ready. Close SFM, then install.",
    "PREPARED_OFFICIAL_REPLACES": "Official data %s is checked and ready. It replaces your current animation-group "
                                  "TXT, which doesn't match official data; your current TXT is kept as a backup. "
                                  "Close SFM, then install.",
    "PREPARED_OFFICIAL_OLDER": "Official data %s is checked and ready. It is older than official data already seen "
                               "here. Close SFM, then install.",
    "SFM_OPEN_NOTE": "SFM appears to be open. Close SFM before installing.",
    "SOURCE_CHANGED": "The TXT you chose changed after it was checked. Nothing was changed. Choose the file again.",
    "SOURCE_UNREADABLE": "The TXT you chose couldn't be read. Check that it still exists and isn't open in another "
                         "program. Nothing was changed.",
    "SOURCE_TOO_LARGE": "This file is too large to be an animation-group TXT. Nothing was changed.",
    "SOURCE_INVALID": "This file isn't a valid animation-group TXT, so it can't be used. Nothing was changed.",
    "REBUILD_INVALID": "The current animation-group TXT has errors, so its data can't be rebuilt. Nothing was "
                       "changed. Fix the TXT, or use another TXT.",
    "PACKAGE_INVALID": "This isn't a complete official data package, so it can't be installed. Nothing was "
                       "changed. Download the official data again.",
    "PACKAGE_UNREADABLE": "The official data package couldn't be read. Check that it still exists and isn't open "
                          "in another program. Nothing was changed.",
    "PACKAGE_UNTRUSTED": "This package isn't signed as official SFM Character Tools data, so it can't be "
                         "installed. Nothing was changed. Download official data again from the official source.",
    "PACKAGE_DAMAGED": "This official data package is damaged or was altered, so it can't be installed. Nothing "
                       "was changed. Download it again.",
    "PACKAGE_NEEDS_NEWER": "This official data needs a newer version of SFM Character Tools. Nothing was changed.",
    "PACKAGE_INCOMPATIBLE": "This official data isn't compatible with the SFM Character Tools installed here. "
                            "Nothing was changed.",
    "PACKAGE_OLDER": "This official data is older than official data already seen here. Nothing was changed. To "
                     "install it anyway, choose to install the older version.",
    "PACKAGE_CONFLICT": "This package doesn't match official data with the same release number seen before, so "
                        "it can't be trusted. Nothing was changed.",
    "RELEASE_RECORD_BUSY": "Another updater window is using this SFM installation. Close it, then try again. "
                           "Nothing was changed.",
    "RELEASE_RECORD_DAMAGED": "The updater's record of official releases is damaged, so official data can't be "
                              "checked. Nothing was changed.",
    "INSTALLED_REBUILD": "Your data was rebuilt from your current TXT and installed.",
    "INSTALLED_IMPORT": "The TXT you chose is installed. Your previous TXT was kept as a backup.",
    "INSTALLED_OFFICIAL": "Official data %s is installed.",
    "INSTALLED_OFFICIAL_REPLACED": "Official data %s is installed. Your previous TXT was kept as a backup.",
    # L-3 additions (explicit check / download; R2 D4). None of them claims "latest".
    "CHECK_FAILED": "Couldn't check for updates. Nothing was changed. Check your internet connection and try again.",
    "NONE_PUBLISHED": "No official data has been published yet. Nothing was changed.",
    "AVAILABLE": "Official data %s is available.",
    "INSTALLED_CURRENT": "Official data %s is already installed. Nothing was changed.",
    "OFFICIAL_OLDER_ONLY": "The official data found (%s) is older than official data already seen here, so it isn't "
                           "offered as an update. Nothing was changed.",
    "NEEDS_NEWER_UPDATER": "A newer release needs newer SFM Character Tools. Nothing was changed.",
    "NEWER_NEEDS_UPDATER_NOTE": "A newer release needs newer SFM Character Tools.",
    "OFFICIAL_INCOMPATIBLE": "Official data was found, but it isn't compatible with the SFM Character Tools "
                             "installed here. Nothing was changed.",
    "OFFICIAL_UNVERIFIED": "Official data was found, but it couldn't be verified as official SFM Character Tools "
                           "data, so it isn't offered. Nothing was changed.",
    "RELEASE_CONFLICT": "The official releases found don't match each other or official data seen before, so they "
                        "can't be trusted. Nothing was changed.",
    "DOWNLOAD_FAILED": "Couldn't download the official data. Nothing was changed. Try again.",
    "RELEASE_CHANGED": "The official release changed or was removed since it was checked. Nothing was changed. "
                       "Check for updates again.",
    # L-4 additions (GUI and bounded worker)
    "DISCARDED": "The prepared data was discarded. Nothing was installed.",
    "WORKER_MEMORY_LIMIT": "The updater needed more memory than it is allowed to use, so it stopped. Nothing was "
                           "reported as installed.",
    "WORKER_FAILED": "The updater stopped unexpectedly. Nothing was reported as installed.",
    "WORKER_STOPPED": "The operation was stopped. Nothing was reported as installed.",
    "INTERRUPTED": "The update was interrupted. Close SFM, then choose Recover.",
    "RECOVERY_NEEDED": "An earlier update was interrupted. Close SFM, then choose Recover. Other actions are "
                       "unavailable until it is recovered.",
    "CLOSE_NOTE": "Save your work and close SFM before installing data.",
}


class Stop(Exception):
    def __init__(self, outcome, message_key, **details):
        Exception.__init__(self, outcome)
        self.outcome = outcome
        self.message_key = message_key
        self.details = details
