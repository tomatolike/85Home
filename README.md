sudo apt-get update
sudo apt-get install build-essential portaudio19-dev espeak-ng

python -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt

cp Modules/VoiceRec/models/ggml-tiny.en.bin ~/.local/share/whispercpp/

# Spotify
plughw:CARD=Headphones,DEV=0
https://docs.spotifyd.rs/advanced/systemd.html
https://www.youtube.com/watch?v=GGXJuzSise4

curl https://sh.rustup.rs -sSf | sh
source $HOME/.cargo/env
sudo apt update
sudo apt install -y libasound2-dev libdbus-1-dev build-essential pkg-config
git clone https://github.com/Spotifyd/spotifyd.git
cd spotifyd
cargo build --release --features dbus_mpris
