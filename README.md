# 🐦 Coo Coo Discord Bot

Coo Coo is a Karuta-style Anime & Game Card Collecting Discord Bot powered by a local 10,000+ character SQLite database, custom PIL framed card rendering, and Gacha drop odds!

---

## 🎴 Features & Mechanics

- **⚡ 10,000+ Local Character Pool**: Offline 0ms SQLite card drops covering top Anime, Manga, Genshin Impact, and Honkai: Star Rail characters.
- **🎲 Gacha Rarity Distribution**:
  - `✨ Legendary` — **1%**
  - `🟣 Epic` — **8%**
  - `🔷 Rare` — **15%**
  - `⚪ Common` — **76%**
- **⏱️ Cooldown & Priority System**:
  - **Drop Cooldown**: 15 minutes (`!cd` to check).
  - **Grab Cooldown**: 5 minutes.
  - **Dropper Priority**: 5 minutes exclusive grab priority for the dropper.
- **🧪 Dusting & 🔥 Burning**:
  - Burn duplicate cards to generate **Dust 🧪** (Interactive safety prompt for Epic & Legendary cards!).
- **🏷️ Tagging System**:
  - Organize cards into custom binder folders (`!tag <id> <folder>`, `!vt <folder>`).
- **🔄 Karuta Trading**:
  - Trade cards and Gems between players (`!t @user`, `!ta`, `!tr`).

---

## 🚀 How to Run Locally

```bash
cd /Users/user/Desktop/coo-coo-bot
./venv/bin/python bot.py
```

---

## ☁️ Cloud Deployment (Railway)

Coo Coo includes `requirements.txt` and `Procfile` ready for automatic worker deployment on Railway!
