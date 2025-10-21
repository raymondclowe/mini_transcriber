from flask import Flask, request, jsonify
import whisper
import time
from pathlib import Path

app = Flask(__name__)
model = None


@app.before_first_request
def load_model():
    global model
    if model is None:
        print("Loading whisper tiny model (this may take a while)...")
        model = whisper.load_model("tiny")
        print("Model loaded.")


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
