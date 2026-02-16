import aiohttp
import asyncio
from telegram import Bot
from ai_model import train_model, load_model, predict, save_training_data
import pandas as pd
import os
import time

TOKEN = "YOUR_TELEGRAM_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

bot = Bot(token=TOKEN)

DEX_URL = "https://api.dexscreener.com/latest/dex/pairs"

SCAN_INTERVAL = 30

model = load_model()

def momentum(prob):
    if prob > 80:
        return "🚀 EXPLOSIVE"
    if prob > 65:
        return "🔥 STRONG"
    if prob > 50:
        return "BUILDING"
    return "WEAK"

async def send_signal(data):
    msg = f"""
🚀 MEME PUMP SIGNAL

{data['token']} | {data['chain']}
Price: ${data['price']}

Pump Score: {data['score']}
AI Probability: {data['prob']}%

Momentum: {data['momentum']}
Liquidity: ${data['liq']}
"""
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def scan():
    global model

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(DEX_URL) as resp:
                    data = await resp.json()

                for pair in data["pairs"][:80]:

                    liq = pair["liquidity"]["usd"]
                    if liq < 20000:
                        continue

                    token = pair["baseToken"]["symbol"]
                    chain = pair["chainId"]

                    v5 = pair["volume"]["m5"]
                    v1 = pair["volume"]["h1"]
                    vsr = v5 / v1 if v1 else 0

                    buys = pair["txns"]["m5"]["buys"]
                    sells = pair["txns"]["m5"]["sells"]
                    bp = buys / sells if sells else buys

                    txns = buys + sells
                    whale = 0.25
                    hype = 300

                    score = round(vsr*25 + bp*15)

                    prob = predict(model, vsr, bp, liq, txns, whale, hype)

                    if score > 70 and prob > 60:

                        m = momentum(prob)

                        await send_signal({
                            "token": token,
                            "chain": chain,
                            "price": pair["priceUsd"],
                            "score": score,
                            "prob": prob,
                            "momentum": m,
                            "liq": int(liq)
                        })

                        save_training_data({
                            "vsr": vsr,
                            "bp": bp,
                            "liq": liq,
                            "txns": txns,
                            "whale": whale,
                            "hype": hype,
                            "pumped": 1
                        })

                        df = pd.DataFrame([{
                            "token": token,
                            "score": score,
                            "prob": prob,
                            "liq": int(liq),
                            "momentum": m
                        }])

                        if os.path.exists("signals.csv"):
                            df.to_csv("signals.csv", mode="a", header=False, index=False)
                        else:
                            df.to_csv("signals.csv", index=False)

                model = train_model()

                await asyncio.sleep(SCAN_INTERVAL)

            except Exception as e:
                print("Error:", e)
                await asyncio.sleep(5)

asyncio.run(scan())
