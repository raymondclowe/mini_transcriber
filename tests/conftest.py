import sys
import types


# Create a minimal fake `whisper` module so tests don't need the real package or heavy models.
class DummyModel:
    def transcribe(self, path):
        return {"text": "dummy transcription from test"}


whisper_mod = types.ModuleType("whisper")

def _load_model(name):
    # Return a tiny dummy model object with a transcribe method.
    return DummyModel()

whisper_mod.load_model = _load_model
sys.modules.setdefault("whisper", whisper_mod)


# Create lightweight stand-ins for sounddevice and soundfile so importing `cli.py` is safe.
sd = types.ModuleType("sounddevice")

def sd_rec(frames, samplerate, channels, dtype):
    # return a zero array-like structure; cli.record only squeezes and writes via soundfile
    try:
        import numpy as _np
        return _np.zeros((frames, channels), dtype=_np.float32)
    except Exception:
        # If numpy unavailable in test env, return a simple nested list
        return [[0.0] * channels for _ in range(frames)]

def sd_wait():
    return None

sd.rec = sd_rec
sd.wait = sd_wait
sys.modules.setdefault("sounddevice", sd)

sf = types.ModuleType("soundfile")

def sf_write(path, data, sr):
    # no-op; tests won't verify written audio content
    return None

sf.write = sf_write
sys.modules.setdefault("soundfile", sf)
