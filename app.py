from flask import Flask, request, jsonify
import whisper
import time
from pathlib import Path

app = Flask(__name__)
model = None


def load_model():
    """Load the whisper model. Registered with the Flask app using
    `app.before_serving` for Flask 3 compatibility (replaces the removed
    `before_first_request` decorator).
    """
    global model
    if model is None:
        print("Loading whisper tiny model (this may take a while)...")
        model = whisper.load_model("tiny")
        print("Model loaded.")


# Register model loader to run before the server starts handling requests.
try:
    # Flask 3: before_first_request removed; use before_serving
    app.before_serving(load_model)
except Exception:
    # Fallback for older Flask versions that still support before_first_request
    try:
        app.before_first_request(load_model)
    except Exception:
        # If neither is available, the model will be loaded lazily in transcribe
        pass


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if 'file' not in request.files:
        return jsonify({"error": "no file provided"}), 400
    f = request.files['file']
    tmp = Path('tmp_upload.wav')
    f.save(tmp)

    start = time.time()
    result = model.transcribe(str(tmp))
    end = time.time()

    return jsonify({
        "text": result.get('text',''),
        "duration_s": end - start
    })


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', '8080'))
    host = os.environ.get('HOST', '127.0.0.1')
    print(f"Starting app on {host}:{port}")
    app.run(host=host, port=port)
