# 🎵 AloneMusic

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Stars](https://img.shields.io/github/stars/TheAloneTeam/AloneMusic?style=social)](https://github.com/TheAloneTeam/AloneMusic/stargazers)
[![Forks](https://img.shields.io/github/forks/TheAloneTeam/AloneMusic?style=social)](https://github.com/TheAloneTeam/AloneMusic/network/members)

---

## 🚀 Introduction
**AloneMusic** is a Python-based **music bot/service** that allows users to play, pause, skip, and manage playlists with ease.  
It’s designed to be lightweight, fast, and customizable.  

---

## ✨ Features
- 🎶 Play / Pause / Skip / Stop songs  
- 📂 Playlist management (add/remove/list)  
- 🔗 Play via song name or URL  
- ⚡ Fast and smooth performance  
- ⚙️ Easy configuration with `.env` file  
- 🐳 Docker & Heroku deployment support  

---

---

## 🚀 Deployment Methods

### 🔹 1. Deploy on **Heroku** (One Click)
Click this button to deploy instantly on **Heroku**:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/TheAloneTeam/AloneMusic)

Or deploy manually:
```bash


# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install system dependencies
sudo apt install python3 python3-pip git ffmpeg screen -y

# 3. Clone the repository
git clone https://github.com/TheAloneTeam/AloneMusic.git
cd AloneMusic

# 4. Install build backend (in case it's missing)
pip install build setuptools wheel

# 5. Install project dependencies using pyproject.toml
# (This automatically reads dependencies from pyproject.toml)
pip install .

# 6. Setup environment variables
cp sample.env .env
nano .env    # Fill BOT_TOKEN, API_ID, API_HASH, etc.

# 7. (Optional) Run bot in a screen session so it keeps running
screen -S alone

# 8. Run the bot
python3 -m AloneMusic.bot

# 9. To detach from screen safely:
# Ctrl + A + D

# 10. To reattach:
# screen -r alone```

## ❤️ Support

💬 **Telegram:** [AloneMusic](https://t.me/TheTeamHacker)  
📂 **GitHub Issues:** [Report a Problem](https://github.com/TheAloneTeam/AloneMusic/issues/new)

---

## 📜 License

🧾 This project is licensed under the **GNU GPLv3 License** — see the [LICENSE](../LICENSE) file for details.
