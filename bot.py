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

SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "30"))

model = load_model()

# Функция для получения трендовых пар
async def fetch_trending_pairs(session):
    """Получает трендовые пары через поиск популярных токенов"""
    pairs = []
    
    # Поиск популярных базовых токенов на разных сетях
    search_queries = [
        "SOL",  # Solana
        "ETH",  # Ethereum  
        "WBNB", # BSC
        "WETH", # Base/Arbitrum
        "PEPE", # Популярные мемкоины
        "DOGE",
        "SHIB",
    ]
    
    for query in search_queries:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "pairs" in data:
                        pairs.extend(data["pairs"][:15])  # Берем топ-15 пар для каждого запроса
                elif resp.status == 404:
                    print(f"⚠️ API endpoint not found for {query}")
                else:
                    print(f"⚠️ API returned status {resp.status} for {query}")
                    
                await asyncio.sleep(0.3)  # Задержка между запросами для соблюдения rate limit
        except Exception as e:
            print(f"⚠️ Error searching {query}: {e}")
            continue
    
    # Удаляем дубликаты по pairAddress
    unique_pairs = {}
    for pair in pairs:
        addr = pair.get("pairAddress")
        if addr and addr not in unique_pairs:
            unique_pairs[addr] = pair
    
    return list(unique_pairs.values())

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

📊 URL: {data.get('url', 'N/A')}
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
    print(f"🔧 Using DexScreener API v2 (search endpoint)")
    
    async with aiohttp.ClientSession() as session:
        scan_count = 0
        while True:
            try:
                scan_count += 1
                print(f"\n{'='*50}")
                print(f"🔍 Scan #{scan_count} - Fetching trending pairs...")
                
                # Получаем трендовые пары
                pairs = await fetch_trending_pairs(session)
                
                if not pairs:
                    print("⚠️ No pairs data received")
                    await asyncio.sleep(SCAN_INTERVAL)
                    continue

                print(f"✅ Received {len(pairs)} unique pairs")
                signals_sent = 0
                
                for pair in pairs:
                    try:
                        # Проверка ликвидности
                        if "liquidity" not in pair or "usd" not in pair["liquidity"]:
                            continue
                        
                        liq = pair["liquidity"]["usd"]
                        if not liq or liq < 20000:
                            continue

                        token = pair.get("baseToken", {}).get("symbol", "UNKNOWN")
                        chain = pair.get("chainId", "UNKNOWN")

                        # Безопасное извлечение объемов
                        v5 = pair.get("volume", {}).get("m5", 0) or 0
                        v1 = pair.get("volume", {}).get("h1", 1) or 1
                        vsr = v5 / v1 if v1 > 0 else 0

                        # Безопасное извлечение транзакций
                        txns_data = pair.get("txns", {})
                        buys = 0
                        sells = 1
                        
                        # Проверяем разные возможные ключи
                        if "m5" in txns_data:
                            buys = txns_data["m5"].get("buys", 0) or 0
                            sells = txns_data["m5"].get("sells", 1) or 1
                        elif "h1" in txns_data:
                            buys = txns_data["h1"].get("buys", 0) or 0
                            sells = txns_data["h1"].get("sells", 1) or 1
                        
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
                                "volume24h": pair.get("volume", {}).get("h24", 0),
                                "url": pair.get("url", "")
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
                    print("🤖 Model retrained")

                print(f"✅ Scan #{scan_count} complete. Signals sent: {signals_sent}/{len(pairs)}")
                print(f"⏳ Sleeping for {SCAN_INTERVAL}s...")
                await asyncio.sleep(SCAN_INTERVAL)

            except asyncio.TimeoutError:
                print("⚠️ Request timeout. Retrying...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"❌ Error in scan loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)

if __name__ == "__main__":
    print("🚀 Starting Meme Pump Bot...")
    print("=" * 50)
    asyncio.run(scan())
