#!/usr/bin/env python3
"""
Simple helper: read an audio file, base64-encode it and POST to the /transcribe endpoint
Usage: bin/transcribe_b64.py <file> [--url http://127.0.0.1:8085/transcribe]
"""
import sys
import base64
import argparse
import requests

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('--url', default='http://127.0.0.1:8085/transcribe')
args = parser.parse_args()

with open(args.file, 'rb') as f:
    b = base64.b64encode(f.read()).decode('ascii')

payload = {'b64': b}
resp = requests.post(args.url, json=payload)
print(resp.status_code)
try:
    print(resp.json())
except Exception:
    print(resp.text)
