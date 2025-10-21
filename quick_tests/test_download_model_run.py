# Minimal run-test for importing download_model
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import download_model
print('download_model import OK')
