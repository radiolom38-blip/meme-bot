from flask import Flask, render_template_string
import pandas as pd
import os

app = Flask(__name__)

HTML = """
<h2>🚀 Meme Pump Dashboard</h2>
<table border=1 cellpadding=6>
<tr>
<th>Token</th>
<th>Score</th>
<th>AI Prob</th>
<th>Liquidity</th>
<th>Momentum</th>
</tr>
{% for row in rows %}
<tr>
<td>{{row.token}}</td>
<td>{{row.score}}</td>
<td>{{row.prob}}%</td>
<td>${{row.liq}}</td>
<td>{{row.momentum}}</td>
</tr>
{% endfor %}
</table>
"""

@app.route("/")
def home():
    if not os.path.exists("signals.csv"):
        return "No signals yet"

    df = pd.read_csv("signals.csv").tail(20)
    return render_template_string(HTML, rows=df.to_dict(orient="records"))

app.run(host="0.0.0.0", port=5000)
