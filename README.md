Yo do you have any contacts so i can contant u

# AutoSeller – Roblox UGC Limited Seller

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)

**AutoSeller** is the #1 tool to automatically sell your Roblox UGC Limited items with smart undercutting, rate‑limit handling, and optional Discord rich presence & webhooks.

![Preview](https://github.com/user-attachments/assets/eeaa7337-bf2d-4fcd-a2ac-5502549599f3)

---

## ✨ Features

- ✅ **Automatic selling** – scans your inventory and sells every resellable UGC Limited.
- 🧠 **Smart pricing** – fetches the current lowest price and undercuts according to your settings (percentage or fixed amount).
- 🎯 **No‑competition price** – configurable default price (e.g., 1000 Robux) when an item has no other sellers.
- 🛡️ **Rate‑limit protection** – automatic exponential backoff and random delays between items.
- 🖥️ **Discord Rich Presence** – shows what you are selling in real time.
- 📨 **Webhook support** – get notified when an item is sold or bought.
- 🤖 **Discord bot** – control the seller via Discord commands (optional).
- 🐛 **Debug mode** – purple coloured debug output, toggle via `config.json`.
- 💾 **Progress saving** – remembers which items you already sold (skip them next run).

---

## 📦 Installation

### Termux (Android)
pkg update && pkg upgrade
pkg install python git
git clone https://github.com/Mainery-foxxie/AutoSeller
cd AutoSeller
pip install -r requirements.txt

### Windows / macOS / Linux
git clone https://github.com/Mainery-foxxie/AutoSeller
cd AutoSeller
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt

> **Requirements** are automatically installed if missing when you run the script for the first time.

---

## ⚙️ Configuration (`config.json`)

Create a `config.json` file in the root folder with the following structure:
{
    "Cookie": "YOUR_ROBLOX_COOKIE_HERE",
    "Discord_Rich_Presence": true,
    "Debug": true,
    "Discord_Bot": {
        "Enabled": false,
        "Token": "",
        "Prefix": "!",
        "Owner_IDs": []
    },
    "Webhook": {
        "OnSale": {
            "Enabled": false,
            "Url": ""
        },
        "OnBuy": {
            "Enabled": false,
            "Url": ""
        },
        "User_To_Ping": 0
    },
    "Auto_Sell": {
        "Ask_Before_Sell": true,
        "Save_Progress": true,
        "Skip_OnSale": false,
        "Skip_If_Cheapest": false,
        "Keep_Serials": 0,
        "Keep_Copy": 0,
        "Creators_Blacklist": [],
        "Default_Price_No_Competition": 1000,
        "Under_Cut": {
            "Type": "percent",
            "Value": 1
        }
    }
}
### Explanation of each field

| Field | Description |
|-------|-------------|
| `Cookie` | Your Roblox `.ROBLOSECURITY` cookie (required). |
| `Discord_Rich_Presence` | Show selling status on your Discord profile. |
| `Debug` | Enable purple debug output (set `false` to disable). |
| `Discord_Bot` | Optional Discord bot control (see below). |
| `Webhook` | Send notifications when an item is sold or bought. |
| `Auto_Sell.Ask_Before_Sell` | `false` = auto‑sell without confirmation, `true` = manual mode. |
| `Auto_Sell.Save_Progress` | Remember sold items in `blacklist/seen.json`. |
| `Auto_Sell.Skip_OnSale` | Skip collectibles that are already on sale. |
| `Auto_Sell.Skip_If_Cheapest` | Skip if you are already the cheapest seller. |
| `Auto_Sell.Keep_Serials` | Keep collectibles with serial number ≤ this value (0 = keep all). |
| `Auto_Sell.Keep_Copy` | Keep at least this many copies of each item (0 = sell all). |
| `Auto_Sell.Creators_Blacklist` | List of creator IDs to ignore (e.g., `[123456, 789012]`). |
| `Auto_Sell.Default_Price_No_Competition` | Price (in Robux) when an item has **no resellers**. |
| `Under_Cut.Type` | `"percent"` or `"robux"` (fixed amount). |
| `Under_Cut.Value` | Undercut amount (e.g., `1` = 1% or 1 Robux). |

---

## 🚀 Running the script

python main.py

- If `Ask_Before_Sell` is `true`, you will see a menu with options:
  - `1` – sell current item
  - `2` – change selling price
  - `3` – blacklist current item
  - `4` – skip current item
- If `Ask_Before_Sell` is `false`, the script runs fully automatically.

---

## 📁 Data files (auto‑created)

| Path | Purpose |
|------|---------|
| `blacklist/blacklist.json` | Items you never want to sell again. |
| `blacklist/seen.json` | Items already sold (progress). |
| `blacklist/not_resable.json` | Items that cannot be resold (detected automatically). |

---

## 🧠 How pricing works

1. **Check if any resellers exist** via the Roblox economy API.
2. **If yes** → apply your undercut (e.g., 1% lower than the lowest price).
3. **If no** → use the `Default_Price_No_Competition` value.
4. **Never below 5 Robux** (absolute minimum enforced by Roblox).

Example:
- Lowest price = 500, undercut = 1% → your price = 495.
- No resellers, `Default_Price_No_Competition` = 1000 → your price = 1000.

---

## 🔧 Troubleshooting

### “Invalid cookie provided”
- Make sure your `.ROBLOSECURITY` cookie is **not expired**.
- Copy the full cookie (including `_|WARNING…` part if present).

### “You don’t have premium to sell limiteds”
- Selling UGC Limiteds requires a Roblox Premium membership.

### “Failed to sell limited (412): Precondition Failed”
- The item is not resellable (e.g., non‑limited, or already on sale with a different price).  
  The script will automatically blacklist such items after a few attempts.

### “Rate limited” errors
- The script already waits 30–120 seconds and adds random delays. If you still get rate limited, increase the delay in `sell_item` (change `random.uniform(2, 5)` to e.g., `(5, 10)`).

### Price floor API returns 404 (fallback to 5)
- The script uses a per‑asset‑type API that works reliably. If you see a 404, your cookie may be invalid or the network is blocked. Check your internet connection.

---

## 💬 Support & Feedback

For questions, ideas, or bug reports, contact me on Discord:  
[**deadlysilence._**](https://discord.com/channels/)

---
**Happy selling!** 🚀
