"""
Tests for concurrent transcription request handling.
"""
import io
import time
import threading

import pytest

from app import app, load_model, transcription_queue, TranscriptionQueue


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def fresh_queue(monkeypatch):
    """Create a fresh queue for testing."""
    test_queue = TranscriptionQueue(max_workers=1, max_queue_size=3)
    monkeypatch.setattr('app.transcription_queue', test_queue)
    yield test_queue
    test_queue.shutdown()


def test_queue_full_returns_503(client, monkeypatch, fresh_queue):
    """Test that when queue is full, server returns 503 with retry info."""
    # Set up a slow model that blocks
    class SlowFakeModel:
        def transcribe(self, path, **kwargs):
            time.sleep(2.0)  # Block for 2 seconds
            return {"text": "slow result"}
    
    def fake_load_model(model_name="tiny"):
        return SlowFakeModel()
    
    monkeypatch.setattr('app.load_model', fake_load_model)
    
    # Fill the queue and processing slot (1 processing + 3 queued = 4 total)
    # Since max_workers=1 and max_queue_size=3, the 5th request should fail
    
    # Submit requests sequentially to avoid Flask context issues
    results = []
    for i in range(5):
        data = {'file': (io.BytesIO(b'RIFF....WAVEfmt '), f'test{i}.wav')}
        rv = client.post('/transcribe?async=true', data=data, content_type='multipart/form-data')
        results.append(rv)
        if i == 0:
            time.sleep(0.05)  # Let first one start processing
    
    # Check that we got at least one 503 (queue full)
    status_codes = [r.status_code for r in results]
    has_503 = 503 in status_codes
    has_202 = 202 in status_codes
    
    assert has_503, f"Expected at least one 503 response, got: {status_codes}"
    assert has_202, f"Expected at least one 202 response, got: {status_codes}"
    
    # Check 503 response format
    for result in results:
        if result.status_code == 503:
            json_data = result.json
            assert 'error' in json_data
            assert json_data['error'] == 'service_busy'
            assert 'retry_after_seconds' in json_data
            assert 'queue_status' in json_data
            assert 'backoff_strategy' in json_data
            assert 'Retry-After' in result.headers


def test_async_transcription(client, monkeypatch, fresh_queue):
    """Test async transcription mode returns job_id and can be polled."""
    class FakeModel:
        def transcribe(self, path, **kwargs):
            time.sleep(0.1)  # Small delay
            return {"text": "async result"}
    
    def fake_load_model(model_name="tiny"):
        return FakeModel()
    
    monkeypatch.setattr('app.load_model', fake_load_model)
    
    # Submit async request
    data = {'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav')}
    rv = client.post('/transcribe?async=true', data=data, content_type='multipart/form-data')
    
    assert rv.status_code == 202
    json_data = rv.json
    assert 'job_id' in json_data
    assert json_data['status'] == 'queued'
    
    job_id = json_data['job_id']
    
    # Poll for completion
    max_polls = 30
    for _ in range(max_polls):
        status_rv = client.get(f'/transcribe/status/{job_id}')
        status_data = status_rv.json
        
        if status_data['status'] == 'complete':
            assert status_rv.status_code == 200
            assert 'result' in status_data
            assert status_data['result']['text'] == 'async result'
            break
        
        time.sleep(0.1)
    else:
        pytest.fail("Async job did not complete in time")


def test_sync_transcription_still_works(client, monkeypatch, fresh_queue):
    """Test that synchronous mode (default) still works."""
    class FakeModel:
        def transcribe(self, path, **kwargs):
            return {"text": "sync result"}
    
    def fake_load_model(model_name="tiny"):
        return FakeModel()
    
    monkeypatch.setattr('app.load_model', fake_load_model)
    
    data = {'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'test.wav')}
    rv = client.post('/transcribe', data=data, content_type='multipart/form-data')
    
    assert rv.status_code == 200
    assert rv.json['text'] == 'sync result'


def test_health_includes_queue_status(client, fresh_queue):
    """Test that /health endpoint includes queue status."""
    rv = client.get('/health')
    assert rv.status_code == 200
    
    json_data = rv.json
    assert 'queue' in json_data
    assert 'max_workers' in json_data['queue']
    assert 'active_workers' in json_data['queue']
    assert 'queued_jobs' in json_data['queue']
    assert 'concurrency' in json_data
    assert 'max_concurrent_transcriptions' in json_data['concurrency']


def test_job_status_not_found(client):
    """Test that querying non-existent job returns 404."""
    rv = client.get('/transcribe/status/nonexistent_job_123')
    assert rv.status_code == 404
    assert 'error' in rv.json


def test_concurrent_requests_controlled(client, monkeypatch, fresh_queue):
    """Test that concurrent requests are properly controlled by the queue."""
    processing_count = {'max': 0, 'current': 0}
    lock = threading.Lock()
    
    class TrackedModel:
        def transcribe(self, path, **kwargs):
            with lock:
                processing_count['current'] += 1
                processing_count['max'] = max(processing_count['max'], processing_count['current'])
            
            time.sleep(0.2)  # Simulate work
            
            with lock:
                processing_count['current'] -= 1
            
            return {"text": "result"}
    
    def fake_load_model(model_name="tiny"):
        return TrackedModel()
    
    monkeypatch.setattr('app.load_model', fake_load_model)
    
    # Submit multiple async requests sequentially to avoid Flask context issues
    results = []
    for i in range(3):
        data = {'file': (io.BytesIO(b'RIFF....WAVEfmt '), f'test{i}.wav')}
        rv = client.post('/transcribe?async=true', data=data, content_type='multipart/form-data')
        results.append(rv)
    
    # Wait for all to complete
    time.sleep(1.0)
    
    # With max_workers=1, we should never have more than 1 processing at once
    assert processing_count['max'] <= 1, f"Expected max 1 concurrent, got {processing_count['max']}"
    
    # All should have been accepted (202) or some rejected (503)
    for result in results:
        assert result.status_code in (202, 503)
