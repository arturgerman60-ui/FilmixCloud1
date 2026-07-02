# 🎮 FunPay AutoResponder

A **premium cross-platform auto-responder for FunPay** with a modern dark UI,
smart rules, message templates, local-AI integration, system-tray operation and
anti-ban protection.

> 🇷🇺 Русская версия: [README.md](README.md)

---

## ✨ Features

| Category | What it does |
|----------|--------------|
| 🖥️ **UI** | CustomTkinter, dark/light theme + 5 accent palettes (glass/neumorphism), Russian & English, smooth cards, toasts, tooltips |
| ⚡ **Auto-replies** | Priority rules: keywords, contains, exact, regular expressions, catch-all |
| 📝 **Templates** | Variables `{username}`, `{game}`, `{price}` and more, AI generation |
| 🤖 **AI** | Local models via **Ollama** or **LM Studio**: replies, template generation, best-reply suggestions |
| 🛡️ **Anti-ban** | Randomised polling (3–8 s) and reply (8–25 s) delays, human jitter, typing simulation, per-chat cooldown |
| 🎯 **Modes** | "New dialogs only", "All chats", "Specific games", black/white lists |
| 🌐 **Network** | Headless browser (Playwright), HTTP/SOCKS5 proxy |
| 🔔 **Notifications** | System notifications with preview + sound |
| 📊 **Statistics** | Processed / replied / earned, per-day chart, top rules |
| 🧩 **Plugins** | Simple plugin system (reply transforms, lifecycle hooks) |
| 📦 **Extras** | Settings export/import (JSON), autostart, update check, tray, secure secret storage (keyring) |

---

## 🚀 Installation

### Option 1 — Windows installer (recommended for end users)

1. Download `FunPayAutoResponder-Setup-x.x.x.exe` from Releases.
2. Run it and follow the wizard (optional desktop shortcut & autostart).
3. Installs to `C:\Program Files\FunPay AutoResponder`.

### Option 2 — From source (all platforms)

Requires **Python 3.11+**.

```bash
git clone <repo-url> FunPay-AutoResponder
cd FunPay-AutoResponder

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
python scripts/generate_assets.py          # icons + sound
python -m playwright install chromium       # browser for real mode

python src/main.py
```

> 💡 **Demo mode.** If no account is configured or Playwright is unavailable,
> the app runs in a safe demo mode generating synthetic messages so you can
> explore everything without a real login.

### Building an executable

```bash
# Windows
build.bat

# Linux / macOS
./build.sh
```

The bundle appears in `dist/FunPayAutoResponder/`. For the Windows installer,
compile `installer/setup.iss` with **Inno Setup 6+** (`iscc installer\setup.iss`).

---

## 🔑 Configuring your FunPay account

The recommended login method is the **`golden_key`** cookie (more stable than
username/password and avoids captcha).

**How to get `golden_key`:**

1. Log in to [funpay.com](https://funpay.com) in your browser.
2. Open DevTools (`F12`) → **Application/Storage** → **Cookies** →
   `https://funpay.com`.
3. Find the cookie named **`golden_key`** and copy its value.
4. In the app: **Settings → FunPay account** → paste it into the `golden_key`
   field → **Test login**.

Alternatively enter login + password in the same section (less reliable).

> 🔒 Secrets (password, `golden_key`, proxy password) are stored in the OS
> keyring, never in plain text.

---

## 📏 Creating your first rule

1. **Auto-replies → ➕ Add rule**.
2. Fill in:
   - **Name** — e.g. "Greeting".
   - **Match type** — `keyword`.
   - **Pattern / keywords** — `hi, hello, привет`.
   - **Response** — a template name (`greeting`) **or** text with variables:
     `Hello {username}! How can I help?`
   - **Priority** — higher = checked earlier (e.g. `200`).
   - **Cooldown** — minimum interval per chat (seconds), 0 = none.
3. **Save**. The switch toggles the rule on/off.

The app ships with several ready-made rules and templates you can edit.

---

## 🛡️ Anti-ban tips

- **Keep delays realistic.** Polling `3–8 s` and reply `8–25 s` mimic a human.
  Instant replies are a red flag.
- **Enable "human jitter"** and "typing simulation" (Settings → Timing).
- **Don't reply to everything.** Use "New dialogs only" or a game filter.
- **Set a cooldown** on catch-all rules so you don't flood a single chat.
- **Use a proxy** and a warmed-up account; avoid multiple bots per IP.
- **Don't run 24/7** without breaks; log in manually now and then.
- Start small: 1–2 rules, observe, then expand.

---

## 🤖 Enabling AI (optional)

**Ollama:**
```bash
# install Ollama (https://ollama.com), then:
ollama pull llama3.1
ollama serve
```
In the app: **Settings → Artificial intelligence** → backend `ollama`,
URL `http://localhost:11434`, model `llama3.1` → **Ping**.

**LM Studio:** start the local server (port `1234`), pick backend `lmstudio`,
URL `http://localhost:1234`.

The **"Use AI only when no rule matches"** option keeps your rules in charge and
uses AI only as a fallback.

---

## 🧩 Plugins

Drop a `.py` file into `plugins/` with a `Plugin` subclass:

```python
from src.core.plugins import Plugin

class SignaturePlugin(Plugin):
    name = "Signature"
    enabled = True
    def on_before_send(self, message, reply):
        return reply + "\n\nBest regards, the seller"
```

Hooks: `on_load`, `on_start`, `on_stop`, `on_message`, `on_before_send`.

---

## 🗂️ Project structure

```
FunPay-AutoResponder/
├── src/
│   ├── main.py                 # entry point
│   ├── ui/                     # windows, tabs, widgets, tray
│   ├── core/                   # engine, rules, AI, scheduler, plugins
│   ├── models/                 # rules, templates, accounts, stats
│   ├── browser/                # Playwright wrapper + demo client
│   ├── utils/                  # config, logging, i18n, paths, security
│   └── assets/                 # icons, sounds
├── installer/                  # Inno Setup script (.iss)
├── plugins/                    # user plugins
├── scripts/                    # asset generation, smoke tests
├── data/                       # DB, logs, sessions (auto-created)
├── requirements.txt
├── build.bat / build.sh
├── README.md / README_EN.md
```

---

## ❓ FAQ

**The window disappeared.** It minimised to the system tray. Click the tray icon
(left click = show, right click = menu).

**Nothing happens / status "Stopped".** Click **Start**. Make sure an account is
configured and login works ("Test login").

**Replies are delayed.** By design — 8–25 s for anti-ban. Adjust under "Timing".

**Selector errors in the log.** FunPay may have changed its markup. All selectors
live in `src/browser/funpay_client.py` (`Selectors` class) — update them there.

**Where are the logs?** The real-time "Logs" tab + files in `data/logs/`.

**Migrating settings?** Settings → Export/Import (JSON).

---

## ⚠️ Disclaimer

This tool is provided "as is" for educational purposes. Automating third-party
services may violate their terms of use. You are solely responsible for
complying with FunPay's terms and applicable law. The authors are not liable for
account bans or any damages.

## 📄 License

MIT — see [LICENSE](LICENSE).
