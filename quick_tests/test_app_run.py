# Minimal run-test for importing app and exercising the transcribe route
import sys
import os
# Ensure the project root is on sys.path so imports like `import app` work when
# running this script from different environments (uv-run may not include the
# repo root on sys.path by default).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

print('app import OK')

# Ensure test client can be created
c = app.test_client()
print('test client OK')
