"""Minimal CLI to transcribe an audio file or record from the microphone.

Usage:
  python cli.py path/to/audio.wav
  python cli.py --mic 5    # record 5 seconds from default microphone
"""
import argparse
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
from pathlib import Path


def record(seconds: int, out_path: Path):
    sr = 16000
    print(f"Recording {seconds}s at {sr}Hz... (Ctrl+C to cancel)")
    data = sd.rec(int(seconds * sr), samplerate=sr, channels=1, dtype='float32')
    sd.wait()
    data = np.squeeze(data)
    sf.write(out_path, data, sr)
    print(f"Saved recording to {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("audio", nargs="?", help="Path to audio file (wav/m4a). If omitted and --mic provided, use mic.)")
    p.add_argument("--mic", type=int, default=0, help="Record from mic for N seconds (0 to disable)")
    p.add_argument("--model", default="tiny", help="Which whisper model to use")
    args = p.parse_args()

    tmp = Path("tmp_audio.wav")

    if args.mic and args.mic > 0:
        record(args.mic, tmp)
        audio_path = tmp
    elif args.audio:
        audio_path = Path(args.audio)
        if not audio_path.exists():
            raise SystemExit(f"Audio file not found: {audio_path}")
    else:
        raise SystemExit("Either provide an audio file or use --mic N_seconds")

    print(f"Loading model {args.model}...")
    model = whisper.load_model(args.model)
    print("Transcribing...")
    result = model.transcribe(str(audio_path))
    print("--- TRANSCRIPT ---")
    print(result.get("text", ""))


if __name__ == "__main__":
    main()
