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
    language = request.args.get('language') or request.form.get('language') or 'en'
    model_name = request.args.get('model') or request.form.get('model')
    # Also support JSON body with 'model' field
    if not model_name and request.is_json:
        payload = request.get_json(silent=True) or {}
        model_name = payload.get('model')
    if not model_name:
        model_name = request.form.get('model') or DEFAULT_MODEL

    language = request.args.get('language') or request.form.get('language')
    initial_prompt = request.form.get('initial_prompt')  # ADD THIS LINE

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
        initial_prompt = None
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            # Also support JSON body with 'language' field
            if not language or language == 'en':
                json_lang = payload.get('language')
                if json_lang:
                    language = json_lang
            b64 = payload.get('b64') or payload.get('audio')
            mimetype = payload.get('mimetype')
            filename = payload.get('filename')
<<<<<<< HEAD
=======
            initial_prompt = payload.get('initial_prompt')
            if not language:
                language = payload.get('language')
>>>>>>> 3c99b3b (Enhance transcribe function: support initial prompt and improve model selection logic)
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
                initial_prompt = None

    # Load requested model (cache in memory)
    try:
        model = load_model(model_name)
    except Exception as e:
        return jsonify({"error": f"failed to load model '{model_name}': {e}"}), 500

    start = time.time()
<<<<<<< HEAD
    result = model.transcribe(file_path, language=language)
                    initial_prompt = payload.get('initial_prompt')
        'language': language if language else 'en',
        'fp16': False,  # CPU doesn't support fp16
        'best_of': 1,    # Default 5, reduces candidates
        'condition_on_previous_text': False  # Faster for short clips
    }
    if initial_prompt:
        transcribe_kwargs['initial_prompt'] = initial_prompt
    result = model.transcribe(file_path, **transcribe_kwargs)
>>>>>>> 3c99b3b (Enhance transcribe function: support initial prompt and improve model selection logic)
    start = time.time()
        "duration_s": end - start,
        "model": model_name,
        "language": language
    })


def format_timestamp(seconds):
    """Format seconds as HH:MM:SS,mmm for SRT or HH:MM:SS.mmm for VTT."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    millis = int((seconds % 1) * 1000)
    return hours, minutes, secs, millis


def generate_srt(segments):
    """Generate SRT formatted subtitles from whisper segments."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = seg.get('start', 0)
        end = seg.get('end', 0)
        text = seg.get('text', '').strip()
        h1, m1, s1, ms1 = format_timestamp(start)
        h2, m2, s2, ms2 = format_timestamp(end)
        lines.append(str(i))
        lines.append(f"{h1:02d}:{m1:02d}:{s1:02d},{ms1:03d} --> {h2:02d}:{m2:02d}:{s2:02d},{ms2:03d}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def generate_vtt(segments):
    """Generate WebVTT formatted subtitles from whisper segments."""
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = seg.get('start', 0)
        end = seg.get('end', 0)
        text = seg.get('text', '').strip()
        h1, m1, s1, ms1 = format_timestamp(start)
        h2, m2, s2, ms2 = format_timestamp(end)
        lines.append(f"{h1:02d}:{m1:02d}:{s1:02d}.{ms1:03d} --> {h2:02d}:{m2:02d}:{s2:02d}.{ms2:03d}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


@app.route('/v1/audio/transcriptions', methods=['POST'])
def openai_transcribe():
    """OpenAI compatible whisper transcription endpoint.
    
    Accepts multipart/form-data with:
    - file: audio file (required)
    - model: whisper model name (optional, default: tiny)
    - response_format: json|text|verbose_json|srt|vtt (optional, default: json)
    - language: language code (optional, default: en)
    - prompt: optional prompt to guide transcription
    - temperature: sampling temperature (optional)
    """
    file_path = None
    
    # Extract parameters from form data
    model_name = request.form.get('model', DEFAULT_MODEL)
    response_format = request.form.get('response_format', 'json')
    language = request.form.get('language')
    prompt = request.form.get('prompt')
    temperature = request.form.get('temperature')
    
    # Parse temperature if provided
    if temperature:
        try:
            temperature = float(temperature)
        except ValueError:
            return jsonify({"error": {"message": f"Invalid temperature value: '{temperature}'. Must be a number between 0 and 1.", "type": "invalid_request_error"}}), 400
    
    # Handle file upload
    if 'file' not in request.files:
        return jsonify({"error": {"message": "No file provided", "type": "invalid_request_error"}}), 400
    
    f = request.files['file']
    if f.filename == '':
        return jsonify({"error": {"message": "No file selected", "type": "invalid_request_error"}}), 400
    
    # Get file extension from uploaded filename
    ext = Path(f.filename).suffix or '.wav'
    
    # Save uploaded file
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix='openai_upload_')
    f.save(tf.name)
    tf.close()
    file_path = tf.name
    
    # Load requested model
    try:
        model = load_model(model_name)
    except Exception as e:
        return jsonify({"error": {"message": f"Failed to load model '{model_name}': {e}", "type": "server_error"}}), 500
    
    # Build transcription options
    transcribe_opts = {}
    if language:
        transcribe_opts['language'] = language
    if prompt:
        transcribe_opts['initial_prompt'] = prompt
    if temperature is not None:
        transcribe_opts['temperature'] = temperature
    
    # Perform transcription
    try:
        result = model.transcribe(file_path, **transcribe_opts)
    except Exception as e:
        return jsonify({"error": {"message": f"Transcription failed: {e}", "type": "server_error"}}), 500
    finally:
        # Clean up temp file
        try:
            Path(file_path).unlink()
        except Exception:
            pass
    
    text = result.get('text', '').strip()
    segments = result.get('segments', [])
    detected_language = result.get('language', language or 'en')
    duration = result.get('duration', 0)
    
    # Format response based on response_format
    if response_format == 'text':
        return text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    elif response_format == 'srt':
        srt_content = generate_srt(segments)
        return srt_content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    elif response_format == 'vtt':
        vtt_content = generate_vtt(segments)
        return vtt_content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    elif response_format == 'verbose_json':
        return jsonify({
            "task": "transcribe",
            "language": detected_language,
            "duration": duration,
            "text": text,
            "segments": segments
        })
    
    else:  # default: json
        return jsonify({"text": text})


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
            "/v1/audio/transcriptions": {
                "post": {
                    "summary": "OpenAI compatible transcription endpoint",
                    "description": "Transcribes audio following the OpenAI Whisper API format",
                    "requestBody": {
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "file": {"type": "string", "format": "binary", "description": "The audio file to transcribe"},
                                        "model": {"type": "string", "description": "Whisper model name (tiny, base, small, medium, large)", "default": "tiny"},
                                        "response_format": {"type": "string", "enum": ["json", "text", "srt", "vtt", "verbose_json"], "default": "json"},
                                        "language": {"type": "string", "description": "Language code (e.g., en, es, fr)"},
                                        "prompt": {"type": "string", "description": "Optional prompt to guide transcription"},
                                        "temperature": {"type": "number", "description": "Sampling temperature (0-1)"}
                                    },
                                    "required": ["file"]
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
                                            "text": {"type": "string"}
                                        }
                                    }
                                },
                                "text/plain": {
                                    "schema": {"type": "string"}
                                }
                            }
                        },
                        "400": {"description": "Bad request (no file provided)"},
                        "500": {"description": "Server error (model load or transcription failure)"}
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


def run_server():
    """Entry point for the server, used by uvx."""
    import os
    port = int(os.environ.get('PORT', '8080'))
    host = os.environ.get('HOST', '0.0.0.0')
    print(f"Starting app on {host}:{port}")
    app.run(host=host, port=port)


if __name__ == '__main__':
    run_server()
