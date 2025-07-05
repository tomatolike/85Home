sudo apt-get update
sudo apt-get install build-essential portaudio19-dev

python -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt