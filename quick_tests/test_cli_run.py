# Minimal run-test for importing cli
import sys
import os
import types
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Provide a lightweight dummy for sounddevice to avoid requiring PortAudio at test time
if 'sounddevice' not in sys.modules:
	dummy_sd = types.SimpleNamespace(rec=None)
	# export a few attributes expected by the project if necessary
	sys.modules['sounddevice'] = dummy_sd

import importlib
import cli
print('cli import OK')
