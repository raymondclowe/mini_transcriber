import io
import os
import tempfile

import pytest

from app import app, load_model, DEFAULT_MODEL


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_default_model_is_tiny():
    """Verify that the default model is 'tiny' for speed."""
    assert DEFAULT_MODEL == "tiny"


def test_load_model_auto_downloads(monkeypatch):
    """Verify that load_model calls whisper.load_model which auto-downloads models."""
    class FakeModel:
        pass
    
    def fake_whisper_load(model_name):
        return FakeModel()
    
    # Use monkeypatch to provide a clean model_cache dict for this test
    test_cache = {}
    monkeypatch.setattr('app.model_cache', test_cache)
    monkeypatch.setattr('app.whisper.load_model', fake_whisper_load)
    
    # Test default model
    model = load_model()
    assert "tiny" in test_cache
    
    # Test explicit model
    model = load_model("base")
    assert "base" in test_cache
    assert len(test_cache) == 2  # Both models should be cached


def test_transcribe_no_file(client):
    rv = client.post('/transcribe', data={})
    assert rv.status_code == 400
    assert rv.json.get('error') == 'no file provided'


def test_transcribe_success(client, monkeypatch, tmp_path):
    # monkeypatch the load_model function to return a fake model
    class FakeModel:
        def transcribe(self, path):
            assert os.path.exists(path)
            return {"text": "hello from fake model"}

    def fake_load_model(model_name="tiny"):
        return FakeModel()

    monkeypatch.setattr('app.load_model', fake_load_model)

    data = {
        'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav')
    }

    rv = client.post('/transcribe', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert 'text' in rv.json
    assert rv.json['text'] == 'hello from fake model'
    assert 'duration_s' in rv.json
    assert rv.json['duration_s'] >= 0
