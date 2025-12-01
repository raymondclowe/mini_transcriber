import io
import os
import tempfile

import pytest

from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_transcribe_no_file(client):
    rv = client.post('/transcribe', data={})
    assert rv.status_code == 400
    assert rv.json.get('error') == 'no file provided'


def test_transcribe_success(client, monkeypatch, tmp_path):
    # monkeypatch the global model in app to control transcribe output
    class FakeModel:
        def transcribe(self, path):
            assert os.path.exists(path)
            return {"text": "hello from fake model"}

    monkeypatch.setattr('app.model', FakeModel())

    data = {
        'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav')
    }

    rv = client.post('/transcribe', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert 'text' in rv.json
    assert rv.json['text'] == 'hello from fake model'
    assert 'duration_s' in rv.json
    assert rv.json['duration_s'] >= 0


# Tests for OpenAI compatible endpoint /v1/audio/transcriptions

def test_openai_transcribe_no_file(client):
    """Test OpenAI endpoint returns error when no file is provided."""
    rv = client.post('/v1/audio/transcriptions', data={})
    assert rv.status_code == 400
    assert rv.json.get('error', {}).get('message') == 'No file provided'


def test_openai_transcribe_json_format(client, monkeypatch):
    """Test OpenAI endpoint with default json response format."""
    class FakeModel:
        def transcribe(self, path, **kwargs):
            assert os.path.exists(path)
            return {"text": "hello openai", "segments": [], "language": "en", "duration": 1.5}
    
    monkeypatch.setattr('app.load_model', lambda name: FakeModel())
    
    data = {
        'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav'),
        'model': 'tiny'
    }
    rv = client.post('/v1/audio/transcriptions', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert rv.json.get('text') == 'hello openai'


def test_openai_transcribe_text_format(client, monkeypatch):
    """Test OpenAI endpoint with text response format."""
    class FakeModel:
        def transcribe(self, path, **kwargs):
            return {"text": "plain text result", "segments": [], "language": "en", "duration": 1.0}
    
    monkeypatch.setattr('app.load_model', lambda name: FakeModel())
    
    data = {
        'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav'),
        'response_format': 'text'
    }
    rv = client.post('/v1/audio/transcriptions', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert rv.content_type.startswith('text/plain')
    assert rv.data.decode('utf-8') == 'plain text result'


def test_openai_transcribe_verbose_json_format(client, monkeypatch):
    """Test OpenAI endpoint with verbose_json response format."""
    class FakeModel:
        def transcribe(self, path, **kwargs):
            return {
                "text": "verbose result",
                "segments": [{"start": 0, "end": 1, "text": "verbose result"}],
                "language": "en",
                "duration": 1.0
            }
    
    monkeypatch.setattr('app.load_model', lambda name: FakeModel())
    
    data = {
        'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav'),
        'response_format': 'verbose_json'
    }
    rv = client.post('/v1/audio/transcriptions', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert rv.json.get('task') == 'transcribe'
    assert rv.json.get('language') == 'en'
    assert rv.json.get('text') == 'verbose result'
    assert 'segments' in rv.json
    assert 'duration' in rv.json


def test_openai_transcribe_srt_format(client, monkeypatch):
    """Test OpenAI endpoint with srt response format."""
    class FakeModel:
        def transcribe(self, path, **kwargs):
            return {
                "text": "subtitle text",
                "segments": [{"start": 0.0, "end": 2.5, "text": "subtitle text"}],
                "language": "en",
                "duration": 2.5
            }
    
    monkeypatch.setattr('app.load_model', lambda name: FakeModel())
    
    data = {
        'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav'),
        'response_format': 'srt'
    }
    rv = client.post('/v1/audio/transcriptions', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert rv.content_type.startswith('text/plain')
    srt_content = rv.data.decode('utf-8')
    assert '1' in srt_content
    assert '-->' in srt_content
    assert 'subtitle text' in srt_content


def test_openai_transcribe_vtt_format(client, monkeypatch):
    """Test OpenAI endpoint with vtt response format."""
    class FakeModel:
        def transcribe(self, path, **kwargs):
            return {
                "text": "vtt text",
                "segments": [{"start": 0.0, "end": 1.5, "text": "vtt text"}],
                "language": "en",
                "duration": 1.5
            }
    
    monkeypatch.setattr('app.load_model', lambda name: FakeModel())
    
    data = {
        'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav'),
        'response_format': 'vtt'
    }
    rv = client.post('/v1/audio/transcriptions', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert rv.content_type.startswith('text/plain')
    vtt_content = rv.data.decode('utf-8')
    assert 'WEBVTT' in vtt_content
    assert '-->' in vtt_content
    assert 'vtt text' in vtt_content


def test_openai_transcribe_with_language_and_prompt(client, monkeypatch):
    """Test OpenAI endpoint passes language and prompt parameters."""
    captured_kwargs = {}
    
    class FakeModel:
        def transcribe(self, path, **kwargs):
            captured_kwargs.update(kwargs)
            return {"text": "with params", "segments": [], "language": "es", "duration": 1.0}
    
    monkeypatch.setattr('app.load_model', lambda name: FakeModel())
    
    data = {
        'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav'),
        'language': 'es',
        'prompt': 'This is a test prompt'
    }
    rv = client.post('/v1/audio/transcriptions', data=data, content_type='multipart/form-data')
    assert rv.status_code == 200
    assert captured_kwargs.get('language') == 'es'
    assert captured_kwargs.get('initial_prompt') == 'This is a test prompt'
