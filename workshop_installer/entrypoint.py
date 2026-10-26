import json
import os
import time

# Optional, local-only startup qualification. The one-file bootloader precedes this marker.
if os.environ.get("SCT_SETUP_TIMING_FILE"):
    try:
        with open(os.environ["SCT_SETUP_TIMING_FILE"], "a", encoding="utf-8") as output:
            output.write(json.dumps({"stage": "helper_entry", "time": time.time(),
                                     "monotonic": time.perf_counter()}) + "\n")
    except OSError:
        pass

from workshop_installer.app import main

raise SystemExit(main())
