from flask import Flask, request, jsonify, send_from_directory
import whisper
import time
from pathlib import Path
import base64
import re
import tempfile
import mimetypes

app = Flask(__name__)
# Model cache: {model_name: model_obj}
model_cache = {}
DEFAULT_MODEL = "tiny"



def load_model(model_name=DEFAULT_MODEL):
    """Load and cache the whisper model by name."""
    global model_cache
    if model_name not in model_cache:
        print(f"Loading whisper model '{model_name}' (this may take a while)...")
        model_cache[model_name] = whisper.load_model(model_name)
        print(f"Model '{model_name}' loaded.")
    return model_cache[model_name]



# Preload default model before serving (optional, improves cold start)
try:
    app.before_serving(lambda: load_model(DEFAULT_MODEL))
except Exception:
    try:
        app.before_first_request(lambda: load_model(DEFAULT_MODEL))
    except Exception:
        pass


@app.route("/transcribe", methods=["POST"])
def transcribe():
    # Support three input modes:
    # 1) Multipart file upload (form-data) with key 'file' (existing behavior)
    # 2) JSON body with {'b64': '<base64 or data:<mime>;base64,...>'}
    # 3) Form-encoded field 'b64' with base64 string
    file_path = None
    model_name = request.args.get('model') or request.form.get('model')
    # Also support JSON body with 'model' field
    if not model_name and request.is_json:
        payload = request.get_json(silent=True) or {}
        model_name = payload.get('model')
    if not model_name:
        model_name = DEFAULT_MODEL

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
            language = request.args.get('language') or request.form.get('language')
            # Also support JSON body with 'model' and 'language' field
            b64 = payload.get('b64') or payload.get('audio')
            mimetype = payload.get('mimetype')
            filename = payload.get('filename')
            if not language:
                language = payload.get('language')
        if not b64:
            b64 = request.form.get('b64') or request.form.get('audio')
            if not language:
                language = 'en'
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

    # Load requested model (cache in memory)
    try:
        model = load_model(model_name)
    except Exception as e:
        return jsonify({"error": f"failed to load model '{model_name}': {e}"}), 500

    start = time.time()
    result = model.transcribe(file_path)
    end = time.time()

    return jsonify({
        "text": result.get('text',''),
        "duration_s": end - start,
        "model": model_name,
        "language": language
    })


@app.route('/health', methods=['GET'])
def health():
    """Health endpoint reporting model status and basic process info."""
    # Report which models are loaded
    loaded_models = list(model_cache.keys())
    return jsonify({
        'status': 'ok' if loaded_models else 'loading',
        'model_loaded': bool(loaded_models),
        'loaded_models': loaded_models
    })


@app.route('/openapi.json', methods=['GET'])
def openapi():
    """Return a minimal OpenAPI 3 spec describing the service for automated discovery.
    The spec intentionally focuses on the public endpoints used by clients: `/transcribe` and `/health`.
    """
    host = request.host_url.rstrip('/')
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "mini_transcriber API",
            "version": "1.0.0",
            "description": "Minimal CPU-first transcription service: POST audio to /transcribe or probe /health."
        },
        "servers": [{"url": host}],
        "paths": {
            "/transcribe": {
                "post": {
                    "summary": "Transcribe an audio file or base64 payload",
                    "requestBody": {
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "file": {"type": "string", "format": "binary"}
                                    },
                                    "required": ["file"]
                                }
                            },
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "b64": {"type": "string", "description": "Base64 or data: URI containing audio bytes"},
                                        "mimetype": {"type": "string"},
                                        "filename": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "required": True
                    },
                    "responses": {
                        "200": {
                            "description": "Transcription result",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "text": {"type": "string"},
                                            "duration_s": {"type": "number", "format": "float"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {"description": "Bad request (no file / invalid base64)"},
                        "500": {"description": "Server error (model load failure or other)"}
                    }
                }
            },
            "/health": {
                "get": {
                    "summary": "Health probe",
                    "responses": {
                        "200": {
                            "description": "Health status",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "model_loaded": {"type": "boolean"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return jsonify(spec)


@app.route('/')
def index():
    # Serve a simple frontend app from the static folder
    return send_from_directory('static', 'index.html')


@app.route('/favicon.ico')
def favicon():
    """Serve a favicon if present in the static directory, otherwise return no-content
    to avoid a 404 showing up in browser devtools.
    """
    fav = Path('static') / 'favicon.ico'
    if fav.exists():
        return send_from_directory('static', 'favicon.ico')
    return ('', 204)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', '8080'))
    host = os.environ.get('HOST', '0.0.0.0')
    print(f"Starting app on {host}:{port}")
    app.run(host=host, port=port)
