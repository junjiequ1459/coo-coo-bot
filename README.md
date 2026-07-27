# 🐦 Coo Coo Discord Bot

Coo Coo is a Karuta-style anime and game card-collecting Discord bot powered by Supabase PostgreSQL, custom Pillow card rendering, and weighted gacha drops.

---

## 🎴 Features & Mechanics

- **⚡ 10,000+ Character Pool**: PostgreSQL-backed card drops covering top Anime, Manga, Genshin Impact, Wuthering Waves, and Honkai: Star Rail characters.
- **🖼️ Automated Scrapers**: Included scripts like `update_wuwa_cards.py` to automatically hit the Fandom MediaWiki API and update missing character artworks in bulk.
- **✨ Animated GIF Support**: Supports fully animated cards in Discord! Exalted cards have custom artificially generated frames to cycle through rainbow borders.
- **🎲 Gacha Rarity Distribution**:
  - `🌟 Exalted` — **0.005%**
  - `✨ Mythic` — **0.1%**
  - `🟡 Legendary` — **0.5%**
  - `🟣 Epic` — **5%**
  - `🔷 Rare` — **10%**
  - `⚪ Common` — **84.4%**
- **⏱️ Cooldown & Priority System**:
  - **Drop Cooldown**: 15 minutes (`!cd` to check).
  - **Grab Cooldown**: 5 minutes.
  - **Dropper Priority**: 10-second exclusive grab window for the dropper.
- **🧪 Dusting & 🔥 Burning**:
  - Burn duplicate cards to generate **Dust 🧪** (with a safety prompt for Epic, Legendary, and Mythic cards).
- **🏷️ Tagging System**:
  - Organize cards into custom binder folders (`!tag <id> <folder>`, `!vt <folder>`).
- **🔄 Karuta Trading**:
  - Trade cards and Gems between players (`!trade @user`, `!ta`, `!tr`).

---

## 🗂️ Project Layout

- `cogs/` — Discord commands and event listeners.
- `cogs/views/` — Buttons, modals, confirmation dialogs, and paginators.
- `data/` — Supabase PostgreSQL schema, card, and user operations.
- `utils/rendering/` — Artwork, fonts, frame, panel, badge, and gem drawing.
- `database.py` and `utils/renderer.py` — Small compatibility entry points used by the cogs.

---

## 🚀 How to Run Locally

```bash
cd /Users/user/Desktop/coo-coo-bot
./venv/bin/python bot.py
```

---

## ☁️ Cloud Deployment (Railway)

Coo Coo includes `requirements.txt` and `Procfile` ready for automatic worker deployment on Railway!


--- 
*Triggering manual redeploy*
