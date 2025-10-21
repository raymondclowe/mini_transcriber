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
