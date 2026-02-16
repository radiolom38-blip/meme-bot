from flask import Flask, render_template_string, jsonify
import pandas as pd
import os
from threading import Thread
import asyncio

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🚀 Meme Pump Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0a0e27;
            color: #fff;
            padding: 20px;
        }
        h2 {
            text-align: center;
            color: #00ff88;
        }
        table {
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
            background: #1a1f3a;
            border-collapse: collapse;
            border-radius: 10px;
            overflow: hidden;
        }
        th {
            background: #00ff88;
            color: #0a0e27;
            padding: 15px;
            font-weight: bold;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #2a2f4a;
            text-align: center;
        }
        tr:hover {
            background: #2a2f4a;
        }
        .momentum {
            font-weight: bold;
        }
        .status {
            text-align: center;
            padding: 10px;
            color: #00ff88;
        }
    </style>
</head>
<body>
    <h2>🚀 Meme Pump Dashboard</h2>
    <div class="status">Auto-refresh every 30 seconds</div>
    {% if rows %}
    <table>
        <tr>
            <th>Token</th>
            <th>Score</th>
            <th>AI Prob</th>
            <th>Liquidity</th>
            <th>Momentum</th>
        </tr>
        {% for row in rows %}
        <tr>
            <td><strong>{{row.token}}</strong></td>
            <td>{{row.score}}</td>
            <td>{{row.prob}}%</td>
            <td>${{"{:,}".format(row.liq)}}</td>
            <td class="momentum">{{row.momentum}}</td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <div class="status">No signals yet. Bot is scanning...</div>
    {% endif %}
</body>
</html>
"""

@app.route("/")
def home():
    if not os.path.exists("signals.csv"):
        return render_template_string(HTML, rows=None)

    try:
        df = pd.read_csv("signals.csv").tail(20)
        return render_template_string(HTML, rows=df.to_dict(orient="records"))
    except Exception as e:
        return f"Error loading data: {e}"

@app.route("/api/signals")
def api_signals():
    """API endpoint для получения сигналов в JSON"""
    if not os.path.exists("signals.csv"):
        return jsonify({"signals": [], "count": 0})
    
    try:
        df = pd.read_csv("signals.csv").tail(20)
        return jsonify({
            "signals": df.to_dict(orient="records"),
            "count": len(df)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    """Health check endpoint для Railway"""
    return jsonify({"status": "ok"}), 200

def run_bot():
    """Запуск бота в отдельном потоке"""
    from bot import scan
    asyncio.run(scan())

if __name__ == "__main__":
    # Запускаем бот в отдельном потоке
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
