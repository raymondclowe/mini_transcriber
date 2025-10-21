from flask import Flask, request, jsonify, send_from_directory
import whisper
import time
from pathlib import Path
import base64
import re
import tempfile
import mimetypes

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
    # Support three input modes:
    # 1) Multipart file upload (form-data) with key 'file' (existing behavior)
    # 2) JSON body with {'b64': '<base64 or data:<mime>;base64,...>'}
    # 3) Form-encoded field 'b64' with base64 string
    file_path = None

    if 'file' in request.files:
        f = request.files['file']
        tmp = Path('tmp_upload.wav')
        f.save(tmp)
        file_path = str(tmp)
    else:
        # try JSON payload or form field containing base64 audio
        b64 = None
        mimetype = None
        filename = None
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            b64 = payload.get('b64') or payload.get('audio')
            mimetype = payload.get('mimetype')
            filename = payload.get('filename')
        if not b64:
            b64 = request.form.get('b64') or request.form.get('audio')
            mimetype = mimetype or request.form.get('mimetype')
            filename = filename or request.form.get('filename')

        if b64:
            # If it's a data URI like: data:audio/wav;base64,AAAA...
            m = re.match(r'^data:([^;]+);base64,(.*)$', b64, flags=re.I)
            if m:
                mimetype = mimetype or m.group(1)
                b64 = m.group(2)

            try:
                raw = base64.b64decode(b64)
            except Exception:
                return jsonify({"error": "invalid base64 payload"}), 400

            # Determine extension from mimetype or filename
            ext = '.wav'
            if filename:
                ext = Path(filename).suffix or ext
            elif mimetype:
                guessed = mimetypes.guess_extension(mimetype)
                if guessed:
                    ext = guessed

            # write to a temp file with extension
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix='tmp_upload_')
            tf.write(raw)
            tf.flush()
            tf.close()
            file_path = tf.name

    if not file_path:
        return jsonify({"error": "no file provided"}), 400

    # Ensure model is loaded lazily if the pre-loading hook didn't run
    try:
        if model is None:
            load_model()
    except Exception:
        # If model loading fails, return an informative error instead of 500
        return jsonify({"error": "failed to load model"}), 500

    start = time.time()
    result = model.transcribe(file_path)
    end = time.time()

    return jsonify({
        "text": result.get('text',''),
        "duration_s": end - start
    })


@app.route('/health', methods=['GET'])
def health():
    """Health endpoint reporting model status and basic process info."""
    loaded = model is not None
    return jsonify({
        'status': 'ok' if loaded else 'loading',
        'model_loaded': loaded
    })


@app.route('/')
def index():
    # Serve a simple frontend app from the static folder
    return send_from_directory('static', 'index.html')


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', '8080'))
    host = os.environ.get('HOST', '127.0.0.1')
    print(f"Starting app on {host}:{port}")
    app.run(host=host, port=port)
