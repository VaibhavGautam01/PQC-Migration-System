import os
import unittest

slow = unittest.skipUnless(os.environ.get("RUN_SLOW") == "1",
                           "slow quantum test, set RUN_SLOW=1")
