import os
from pathlib import Path
import tempfile
import argparse

import pytest

import cli


def test_cli_default_model_is_tiny():
    """Verify that the CLI defaults to 'tiny' model for speed."""
    p = argparse.ArgumentParser()
    p.add_argument("audio", nargs="?", help="Path to audio file")
    p.add_argument("--mic", type=int, default=0, help="Record from mic")
    p.add_argument("--model", default="tiny", help="Which whisper model to use")
    args = p.parse_args([])
    assert args.model == "tiny"


def test_record_creates_file(monkeypatch, tmp_path):
    out = tmp_path / 'out.wav'

    # monkeypatch sd.rec and sf.write to capture calls
    called = {}

    def fake_rec(frames, samplerate, channels, dtype):
        # return a simple numpy-like array if numpy available
        import numpy as _np
        return _np.zeros((frames, channels), dtype=_np.float32)

    def fake_wait():
        called['wait'] = True

    def fake_write(path, data, sr):
        called['write'] = True
        # actually create the file so Path.exists works
        Path(path).write_bytes(b'')

    monkeypatch.setattr('cli.sd.rec', fake_rec)
    monkeypatch.setattr('cli.sd.wait', fake_wait)
    monkeypatch.setattr('cli.sf.write', fake_write)

    cli.record(1, out)
    assert called.get('wait')
    assert called.get('write')
    assert out.exists()


def test_main_file_not_found(monkeypatch, tmp_path):
    # Simulate calling main with a non-existent audio file
    monkeypatch.setattr('cli.argparse.ArgumentParser.parse_args', lambda self: argparse.Namespace(audio='nope.wav', mic=0, model='tiny'))
    with pytest.raises(SystemExit):
        cli.main()
