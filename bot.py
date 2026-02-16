import aiohttp
import asyncio
from telegram import Bot
from ai_model import train_model, load_model, predict, save_training_data
import pandas as pd
import os
import time

# Получаем переменные окружения
TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

# Проверка наличия токена
if TOKEN == "YOUR_TELEGRAM_TOKEN" or not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не установлен! Добавьте его в переменные окружения Railway")

if CHAT_ID == "YOUR_CHAT_ID" or not CHAT_ID:
    raise ValueError("❌ TELEGRAM_CHAT_ID не установлен! Добавьте его в переменные окружения Railway")

bot = Bot(token=TOKEN)

DEX_URL = "https://api.dexscreener.com/latest/dex/pairs"

SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "30"))

model = load_model()

def momentum(prob):
    if prob > 80:
        return "🚀 EXPLOSIVE"
    if prob > 65:
        return "🔥 STRONG"
    if prob > 50:
        return "⚡ BUILDING"
    return "📊 WEAK"

async def send_signal(data):
    msg = f"""
🚀 MEME PUMP SIGNAL

{data['token']} | {data['chain']}
Price: ${data['price']}

Pump Score: {data['score']}
AI Probability: {data['prob']}%

Momentum: {data['momentum']}
Liquidity: ${data['liq']:,}
24h Volume: ${data.get('volume24h', 'N/A')}
"""
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print(f"✅ Signal sent: {data['token']}")
    except Exception as e:
        print(f"❌ Error sending message: {e}")

async def scan():
    global model

    print("🤖 Starting meme pump scanner...")
    print(f"📊 Scan interval: {SCAN_INTERVAL}s")
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                print(f"🔍 Scanning DEX pairs...")
                async with session.get(DEX_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        print(f"⚠️ API returned status {resp.status}")
                        await asyncio.sleep(SCAN_INTERVAL)
                        continue
                    
                    data = await resp.json()

                if "pairs" not in data:
                    print("⚠️ No pairs data in response")
                    await asyncio.sleep(SCAN_INTERVAL)
                    continue

                signals_sent = 0
                for pair in data["pairs"][:80]:
                    try:
                        # Проверка ликвидности
                        if "liquidity" not in pair or "usd" not in pair["liquidity"]:
                            continue
                        
                        liq = pair["liquidity"]["usd"]
                        if liq < 20000:
                            continue

                        token = pair.get("baseToken", {}).get("symbol", "UNKNOWN")
                        chain = pair.get("chainId", "UNKNOWN")

                        # Безопасное извлечение объемов
                        v5 = pair.get("volume", {}).get("m5", 0) or 0
                        v1 = pair.get("volume", {}).get("h1", 1) or 1
                        vsr = v5 / v1 if v1 > 0 else 0

                        # Безопасное извлечение транзакций
                        buys = pair.get("txns", {}).get("m5", {}).get("buys", 0) or 0
                        sells = pair.get("txns", {}).get("m5", {}).get("sells", 1) or 1
                        bp = buys / sells if sells > 0 else buys

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
                                "price": pair.get("priceUsd", "N/A"),
                                "score": score,
                                "prob": prob,
                                "momentum": m,
                                "liq": int(liq),
                                "volume24h": pair.get("volume", {}).get("h24", 0)
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
                            
                            signals_sent += 1

                    except Exception as e:
                        print(f"⚠️ Error processing pair: {e}")
                        continue

                # Переобучение модели
                new_model = train_model()
                if new_model:
                    model = new_model
                    print("✅ Model retrained")

                print(f"✅ Scan complete. Signals sent: {signals_sent}")
                await asyncio.sleep(SCAN_INTERVAL)

            except asyncio.TimeoutError:
                print("⚠️ Request timeout. Retrying...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"❌ Error in scan loop: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    print("🚀 Starting Meme Pump Bot...")
    asyncio.run(scan())
