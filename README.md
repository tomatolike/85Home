sudo apt-get update
sudo apt-get install build-essential portaudio19-dev espeak-ng

python -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt

cp Modules/VoiceRec/models/ggml-tiny.en.bin ~/.local/share/whispercpp/
