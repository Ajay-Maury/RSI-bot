# 📈 RSI + EMA Algo Trading Bot with Streamlit Dashboard

A Python-based swing trading bot using RSI, EMA, SMA, ADX, and MACD filters with backtesting and a live interactive Streamlit dashboard.

## 🚀 Features

- Multi-symbol scanning
- RSI + EMA crossover logic
- Optional SMA, ADX, and MACD filters
- Streamlit dashboard for tuning + visualization
- Backtest engine with win rate, P&L, equity curve
- Configurable via `config.yaml`
- Discord and Email alerts supported

## 📂 Project Structure

```
rsi_bot/
├── alerts.py            # Alerts via Discord or Email
├── backtest.py          # Backtesting engine
├── config.yaml          # Strategy and broker settings
├── strategy.py          # RSI, EMA, SMA, ADX, MACD logic
├── streamlit_app.py     # Interactive web dashboard
├── utils.py             # Kite Connect and data utilities
```

## 📦 Setup

1. Install dependencies:
```bash
pip install streamlit ta kiteconnect pyyaml
```

2. Add your Kite Connect API keys and Discord webhook to `config.yaml`.

3. Run the dashboard:
```bash
streamlit run streamlit_app.py
```

## 🧪 Backtesting

Use the dashboard to:
- Visualize trade signals
- Adjust RSI/EMA/SMA thresholds
- Run historical backtests and evaluate performance

## ⚠️ Disclaimer

This project is for educational purposes only. Trading involves risk. Use at your own discretion.

---

Made with ❤️ using Python and Streamlit.