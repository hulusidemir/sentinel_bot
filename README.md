# Sentinel 🛡️

Sentinel is a Python-based trading bot designed for the **Bybit** exchange. It scans high-volume cryptocurrencies and generates buy/sell signals based on technical analysis indicators using a "Trend Following Pullback" strategy. Detected signals are instantly sent via **Telegram**.

## 🚀 Features

*   **Smart Volume Filter:** Filters out low-volume coins, focusing only on assets with significant market interest.
*   **Advanced Technical Analysis:** Utilizes `pandas_ta` to analyze 4H, 1H, and 15m timeframes simultaneously.
*   **Trend Following Strategy:** 
    *   Confirms trend direction using EMA 200 (4H) and EMA 50 (1H).
    *   Enters trades on pullbacks using RSI and MFI indicators.
    *   **New:** Smart Volume Check to avoid entering trades during crash/pump scenarios (Anti-Falling Knife).
*   **Risk Management:** Automatically calculates Stop Loss (SL) and Take Profit (TP) levels using ATR.
*   **Telegram Notifications:** Delivers detailed trade alerts directly to your mobile device.
*   **Cloud Ready:** Can be deployed locally or via CI/CD pipelines like GitHub Actions.

## 🛠️ Setup & Installation

### Prerequisites

*   Python 3.8+
*   A Bybit Account (Futures/Derivatives)
*   A Telegram Bot

### 1. Local Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/sentinel.git
    cd sentinel
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Configure Environment:
    *   Rename `.env.example` to `.env`.
    *   Fill in your API keys and Telegram credentials:
        ```env
        TELEGRAM_BOT_TOKEN=your_bot_token
        TELEGRAM_CHAT_ID=your_chat_id
        BYBIT_API_KEY=your_bybit_api_key
        BYBIT_API_SECRET=your_bybit_secret
        ```

4.  Run the bot:
    ```bash
    python sentinel.py
    ```

### 2. GitHub Actions (Cloud Run)

To run this bot periodically using GitHub Actions:

1.  Fork this repository.
2.  Go to **Settings** > **Secrets and variables** > **Actions**.
3.  Add the following secrets:
    *   `TELEGRAM_BOT_TOKEN`
    *   `TELEGRAM_CHAT_ID`
    *   `BYBIT_API_KEY`
    *   `BYBIT_API_SECRET`
4.  The bot is configured to run based on the workflow definition in `.github/workflows/` (if created).

## ⚠️ Disclaimer

This software is for educational and hobby purposes only. **It is not financial advice.** Cryptocurrency trading involves high risk. Use at your own risk.