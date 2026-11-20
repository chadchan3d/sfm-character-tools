# -*- coding: utf-8 -*-
"""SFM Character Tools v1.1.0 release candidate 3: RC2 with the structural rig adapter (Fox and Tails) enabled for
normal installations. Builds the UNSIGNED package and verifies its release readiness offline with RC1's tool unchanged
(release/v1.1.0-rc1/rc_tool.py), with this folder's SOFTWARE_SPEC.json and the RC3 package name substituted. Nothing
here installs, signs, publishes or touches an SFM installation.

usage: python -I rc3_tool.py RC.json package | verify
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v1.1.0-rc1"))
import rc_tool as R  # noqa: E402

R.SPEC = os.path.join(HERE, "SOFTWARE_SPEC.json")
R.P.ZIP_NAME = "SFM.Character.Tools.v1.1.0-rc3-UNSIGNED.zip"

if __name__ == "__main__":
    sys.exit(R.main(sys.argv))
