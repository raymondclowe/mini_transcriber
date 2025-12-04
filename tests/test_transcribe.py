import pytest
import sys
import os
import io
from app import app

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_transcribe_no_file(client):
    response = client.post('/transcribe')
    assert response.status_code == 400
    assert response.json['error'] == 'no file provided'

def test_transcribe_with_model_and_language(client, monkeypatch):
    class MockModel:
        def transcribe(self, file_path, language='en', **kwargs):
            return {'text': f'Transcribed in {language}'}

    monkeypatch.setattr('app.load_model', lambda model_name: MockModel())

    data = {
        'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav'),
        'model': 'tiny',
        'language': 'fr'
    }
    response = client.post('/transcribe', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert response.json['text'] == 'Transcribed in fr'

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert 'status' in response.json
    assert 'model_loaded' in response.json