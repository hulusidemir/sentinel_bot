# 🛡️ Sentinel Bot - V7 Pro Sniper

**Sentinel** is an advanced, automated crypto trading assistant designed for the **Bybit Futures** market. Unlike standard bots that rely on static indicators, Sentinel acts like a professional trader, using dynamic logic to adapt to market conditions.

It runs in **"Sniper Mode"**, patiently scanning the market for high-probability setups and delivering detailed signals directly to your **Telegram**.

## 🧠 Core Intelligence: "Pro Trader V7"

The bot operates on a multi-layer decision engine that mimics expert human analysis:

### 1. Dynamic Trend Adaptation 🌊
Instead of using fixed overbought/oversold levels, Sentinel adapts to the Trend Strength (ADX):
*   **Super Trend (ADX > 40):** Adapts RSI limits to catch early entries in strong trends (e.g., buying when RSI hits 50, not waiting for 30).
*   **Normal Market:** Waits for deeper pullbacks to ensure value entries.
*   **Chop Filter:** Strictly ignores sideways markets (ADX < 25) to prevent false signals.

### 2. Smart Open Interest (OI) Protection 🏦
Prevents entering "Falling Knife" trades by analyzing the flow of money:
*   **Long Protection:** Even if RSI is oversold, if Open Interest is skyrocketing while price drops (indicating heavy shorting by whales), Sentinel **cancels the trade**.
*   **Value Calculation:** Auto-calculates Notional Value ($) even if the API only returns contract amounts.

### 3. "Opportunistic" BTC Correlation 🌍
*   Monitors Bitcoin's 24h performance.
*   **Contrarian Logic:** If BTC drops significantly (> 3%), Sentinel treats it as a potential "Discount" opportunity for strong altcoins, relaxing entry criteria to catch the bounce.

### 4. Swing-Based Risk Management 🛡️
*   **Stop Loss:** Replaced generic percentage stops with **Swing Low/High** structure analysis (Last 10 candles). This places stops outside the "liquidity hunt" zones of market makers.
*   **Take Profit:** Calculated dynamically using ATR (Average True Range) Multipliers.

### 5. Volume Verification 📊
*   Ensures the entry candle is not part of a panic crash (Volume Spike Check).
*   Verifies that liquidity exists for a clean entry.

---

## 🚀 Features

*   **Multi-Timeframe Analysis:** Combines 4H (Trend), 1H (Confirmation), and 15m (Entry) data.
*   **Indicator Fusion:** EMA 200/50 + RSI + MFI + ADX + ATR + Open Interest.
*   **Detailed Alerts:** Telegram messages include entry price, calculated Stop Loss, Take Profit, and the **reasoning** behind the trade (Why did the bot enter?).
*   **Cloud Ready:** Zero-dependency setup, easy to run on local machines or cloud VPS.

---

## 🛠️ Setup & Installation

### Prerequisites
*   Python 3.10+
*   Bybit Account (Futures)
*   Telegram Bot Token

### 1. Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/hulusidemir/sentinel_bot.git
    cd sentinel_bot
    ```

2.  Create a virtual environment & install dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  Configuration:
    *   Create a `.env` file from the example:
        ```bash
        cp .env.example .env
        ```
    *   Edit `.env` and add your API keys:
        ```env
        TELEGRAM_BOT_TOKEN=your_token_here
        TELEGRAM_CHAT_ID=your_id_here
        BYBIT_API_KEY=your_key_here
        BYBIT_API_SECRET=your_secret_here
        ```

### 2. Running the Bot

Start the Sentinel loop:
```bash
python sentinel.py
```
*The bot will start scanning the top volume coins every 60 seconds.*

---

## ⚠️ Disclaimer

This software is for **educational purposes only**. It attempts to automate technical analysis strategies but cannot modify risk.
*   **Not Financial Advice:** The author is not responsible for any financial losses.
*   **Use Caution:** Always test with paper trading first. Cryptocurrency markets are highly volatile.

---
*License: MIT*
