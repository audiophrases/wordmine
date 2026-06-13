"""
Downloads the offline speech-recognition model used for the speaking
challenges (Vosk small US-English, ~40 MB). Run once:

    python setup_models.py

The game runs fine without it -- speaking challenges simply fall back to a
"press Enter to continue" mode until the model is present.
"""
import sys
import urllib.request
import zipfile
from pathlib import Path

import config

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"


def _progress(block_num, block_size, total_size):
    if total_size > 0:
        pct = min(100, block_num * block_size * 100 // total_size)
        mb = block_num * block_size / 1_000_000
        sys.stdout.write(f"\r  downloading... {pct:3d}%  ({mb:5.1f} MB)")
        sys.stdout.flush()


def main():
    target = config.VOSK_MODEL_DIR
    if target.exists():
        print(f"Vosk model already present at:\n  {target}")
        return

    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = config.MODELS_DIR / "vosk-model-small-en-us-0.15.zip"

    print(f"Downloading Vosk model from:\n  {MODEL_URL}")
    try:
        urllib.request.urlretrieve(MODEL_URL, zip_path, _progress)
        print("\nExtracting...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(config.MODELS_DIR)
        zip_path.unlink(missing_ok=True)
    except Exception as e:  # noqa: BLE001
        print(f"\nDownload failed: {e}")
        print("You can download it manually from the URL above and unzip it into the 'models' folder.")
        sys.exit(1)

    if target.exists():
        print(f"Done! Speaking challenges are now enabled.\n  {target}")
    else:
        print("Extracted, but the expected folder name was not found. "
              "Check the 'models' folder and update config.VOSK_MODEL_DIR if needed.")


if __name__ == "__main__":
    main()
