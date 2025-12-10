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
## ❤️ Support

💬 **Telegram:** [AloneMusic](https://t.me/TheTeamHacker)  
📂 **GitHub Issues:** [Report a Problem](https://github.com/TheAloneTeam/AloneMusic/issues/new)

---

## 📜 License

🧾 This project is licensed under the **GNU GPLv3 License** — see the [LICENSE](/LICENSE) file for details.

---

## 🚀 Deployment Methods

### 🔹 1. Deploy on **Heroku** (One Click)
Click this button to deploy instantly on **Heroku**:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/TheAloneTeam/AloneMusic)

Or deploy manually:
```#!/bin/bash

echo "🚀 AloneMusic VPS Deployment Starting..."

# 1. System update
sudo apt update && sudo apt upgrade -y

# 2. Install system dependencies
sudo apt install -y ffmpeg git python3 python3-venv python3-pip tmux nano build-essential

# 3. Remove old folder if exists
if [ -d "AloneMusic" ]; then
    rm -rf AloneMusic
fi

# 4. Clone repo
git clone https://github.com/TheAloneTeam/AloneMusic
cd AloneMusic || exit 1

# 5. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 6. Upgrade pip
pip install --upgrade pip

# 7. Install dependencies (correct way)
pip install -e .

# 8. Setup env file
if [ -f "sample.env" ]; then
    cp sample.env .env
    echo "⚠️  Please edit .env and set BOT_TOKEN, API_ID, API_HASH, STRING_SESSION, MONGO_DB etc."
    sleep 2
    nano .env
else
    echo "❌ sample.env not found! Create .env manually."
    exit 1
fi

# 9. Start bot in tmux
tmux new-session -d -s alone "source venv/bin/activate && python3 -m AloneMusic"

echo "✅ AloneMusic Bot Deployed Successfully!"
echo "➡ Bot running inside tmux session: alone"
echo "➡ View logs: tmux attach -t alone"
