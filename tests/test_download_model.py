import os
from pathlib import Path
import argparse

import pytest

import download_model


def test_main_downloads_model(monkeypatch, tmp_path):
    # point cache-dir to tmp_path and model to tiny
    args = argparse.Namespace(model='tiny', cache_dir=str(tmp_path))
    monkeypatch.setattr('download_model.argparse.ArgumentParser.parse_args', lambda self: args)

    called = {}

    def fake_load_model(name):
        called['name'] = name
        class M:
            pass
        return M()

    monkeypatch.setattr('download_model.whisper.load_model', fake_load_model)

    download_model.main()

    assert called.get('name') == 'tiny'
    # cache dir should exist
    assert tmp_path.exists()
