#!/usr/bin/env python3
"""
Weather Forecast Analysis Bot
Fetches GFS, ECMWF, ICON forecasts from Open-Meteo,
analyzes with Gemini (google-genai SDK), sends Persian analysis to Telegram.
Runs on schedule: Friday 23:00 and Tuesday 23:00 (Asia/Tehran).
"""

import os
import sys
import yaml
import requests
from datetime import datetime
from telegram import Bot
import asyncio
import logging

# New Google GenAI SDK
from google import genai
from google.genai import types

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def fetch_open_meteo(lat, lon, model, days=14):
    """Fetch forecast from Open-Meteo for a specific model."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "precipitation_probability_max",
            "windspeed_10m_max", "winddirection_10m_dominant",
            "weathercode", "relative_humidity_2m_mean"
        ],
        "timezone": "Asia/Tehran",
        "forecast_days": days,
        "models": model
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get('daily', {})
    except Exception as e:
        logger.error(f"Error fetching {model}: {e}")
        return {}


def format_forecast_data(daily_data, model_name, location_name, days=14):
    """Format raw forecast data into a structured text for Gemini."""
    if not daily_data or 'time' not in daily_data:
        return f"داده‌ای برای مدل {model_name} دریافت نشد."

    lines = [
        f"📍 پیش‌بینی {days} روزه برای {location_name} — مدل {model_name}",
        f"🕐 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 50
    ]

    weather_codes = {
        0: "☀️ آفتابی", 1: "🌤️ بیشتره آفتابی", 2: "⛅ بردرفته",
        3: "☁️ ابری", 45: "🌫️ مه", 48: "🌫️ مه یخ‌زده",
        51: "🌦️ بوفار سبک", 53: "🌦️ بوفار متوسط", 55: "🌧️ بوفار شدید",
        61: "🌧️ باران سبک", 63: "🌧️ باران متوسط", 65: "🌧️ باران شدید",
        71: "❄️ برف سبک", 73: "❄️ برف متوسط", 75: "❄️ برف شدید",
        80: "🌦️ رگبار سبک", 81: "🌦️ رگبار متوسط", 82: "🌧️ رگبار شدید",
        95: "⛈️ طوفان رعدی", 96: "⛈️ طوفان رعدی با توف", 99: "⛈️ طوفان رعدی شدید با توف"
    }

    for i in range(min(days, len(daily_data['time']))):
        date = daily_data['time'][i]
        t_max = daily_data['temperature_2m_max'][i]
        t_min = daily_data['temperature_2m_min'][i]
        precip = daily_data['precipitation_sum'][i]
        precip_prob = daily_data['precipitation_probability_max'][i]
        wind = daily_data['windspeed_10m_max'][i]
        wind_dir = daily_data['winddirection_10m_dominant'][i]
        humidity = daily_data['relative_humidity_2m_mean'][i]
        wcode = daily_data['weathercode'][i]
        weather_desc = weather_codes.get(wcode, f"کد {wcode}")

        lines.append(
            f"\n📅 {date} | {weather_desc}\n"
            f"   🌡️ ماکس: {t_max}°C | مین: {t_min}°C\n"
            f"   💧 بارش: {precip}mm ({precip_prob}% احتمال)\n"
            f"   💨 باد: {wind} km/h ({wind_dir}°)\\n"
            f"   💦 رطوبت: {humidity}%"
        )

    return "\n".join(lines)


def analyze_with_gemini(api_key, model_name, forecast_texts, location_name, days):
    """Send all model forecasts to Gemini for comparative Persian analysis."""
    client = genai.Client(api_key=api_key)

    prompt = f"""تو یک متخصص هواشناسی با تجربه هستی که پیش‌بینی‌های چند مدل رو برای یک کاربر عادی تحلیل می‌کنی.

موقعیت: {location_name}
بازه: {days} روز آینده

⚠️ **ترجیحات کاربر (بسیار مهم)**:
- از **گرما** و **رطوبت بالا** متنفره
- هوا «خوب» برایش یعنی: **سرد** (زیر ۱۵℃)، **کم‌رطوبت** (زیر ۵۰٪)، **بارانی**
- بارش برایش «خوب» فقط اگه همراه با هوای خنک باشه
- وقتی می‌گی «هوا خوب می‌شه» منظور تو نباید گرم/مرطوب باشه

داده‌های خام سه مدل پیش‌بینی:
{chr(10).join(forecast_texts)}

لطفاً یک تحلیل جامع، روان و «خودمانی» به فارسی تولید کن که شامل موارد زیر باشه:

1. **خلاصه کلی روزانه** (۲-۳ خط برای هر روز): چه انتظار داریم؟ بارش؟ تغییر دما؟ راحت باش یا چتر بگیر؟ **از منظر سلیقه کاربر (دوستدار هواهای خنک/خشک) بنویس.**

2. **مقایسه مدل‌ها**: کدوم مدل چی می‌گه؟ کجا موافق هستن؟ کجا اختلاف دارن؟ چه مدل‌های روی هم سوار شدن و چه مدل‌ها دایورجن داده؟

3. **نکات فنی مهم**: اگر مدل‌های GFS، ECMWF، ICON رو می‌شناسی، دیدگاه اختصاصی هر کدوم رو توضیح بده:
   - GFS: مدل آمریکایی، چطور در این منطقه عمل می‌کنه؟
   - ECMWF: مدل اروپایی، چرا معمولاً دقیق‌تره؟
   - ICON: مدل آلمانی، چطور در عرض‌های جغرافیایی ایران رفتار می‌کنه؟

4. **پیشنهاد عملی**: برای هر روز، کاربر چه باید بکنه؟ (پیک آب‌وهوا، پوشیدن، برنامه‌ریزی بیرون رفتن) **با در نظر گرفتن نفرین از گرما/رطوبت.**

لحن: دوستانه، تخصصی ولی بدونژه، مثل یه دوست که از هواشناسی می‌فهمه و می‌خواد به دوشش کمک کنه.
از اموجی استفاده کن. ساختاردهی واضح با هدرها.
طول متن: کامل ولی خسته‌کننده نباش."""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"❌ خطا در تحلیل جمینای: {e}"


async def send_telegram(bot_token, chat_id, text):
    """Send message to Telegram."""
    bot = Bot(token=bot_token)
    # Telegram max message length is 4096 chars
    if len(text) <= 4000:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    else:
        # Split into chunks
        for i in range(0, len(text), 4000):
            chunk = text[i:i+4000]
            await bot.send_message(chat_id=chat_id, text=chunk, parse_mode='HTML')
            await asyncio.sleep(0.5)


def main():
    config = load_config()

    # Read secrets from environment variables first (secure), fallback to config.yaml
    gemini_key = os.environ.get("GEMINI_API_KEY") or config['gemini'].get('api_key', '')
    tg_token = os.environ.get("TG_BOT_TOKEN") or config['telegram'].get('bot_token', '')
    chat_id = os.environ.get("TG_CHAT_ID") or config['telegram'].get('chat_id', '')

    lat = config['location']['latitude']
    lon = config['location']['longitude']
    loc_name = config['location']['name']
    days = config['forecast']['days']
    models = config['models']

    if not tg_token or not chat_id:
        logger.error("❌ Telegram credentials missing. Set TG_BOT_TOKEN and TG_CHAT_ID env vars or config.yaml")
        sys.exit(1)
    if not gemini_key:
        logger.error("❌ Gemini API key missing. Set GEMINI_API_KEY env var or config.yaml")
        sys.exit(1)

    logger.info(f"Fetching forecasts for {loc_name} ({lat}, {lon})...")

    # Fetch all models
    forecast_texts = []
    for m in models:
        model_key = m['open_meteo_model']
        model_name = m['name']
        logger.info(f"Fetching {model_name} ({model_key})...")
        daily = fetch_open_meteo(lat, lon, model_key, days)
        text = format_forecast_data(daily, model_name, loc_name, days)
        forecast_texts.append(text)
        logger.info(f"  ✓ {model_name} done")

    # Analyze with Gemini
    logger.info("Analyzing with Gemini...")
    analysis = analyze_with_gemini(gemini_key, config['gemini']['model'], forecast_texts, loc_name, days)

    # Send to Telegram
    logger.info("Sending to Telegram...")
    asyncio.run(send_telegram(tg_token, chat_id, analysis))
    logger.info("✅ Done!")


if __name__ == "__main__":
    main()