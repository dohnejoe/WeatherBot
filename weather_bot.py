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
from zoneinfo import ZoneInfo
from telegram import Bot
import jdatetime
from telegram.error import TelegramError
import asyncio
import logging

# New Google GenAI SDK
from google import genai

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# httpx logs full request URLs, which can expose the bot token in Telegram URLs.
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')

PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
]
GREGORIAN_MONTHS = [
    "ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن",
    "ژوئیه", "آگوست", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"
]


def to_persian_digits(value):
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def format_date_mapping(iso_date):
    """Return a deterministic Gregorian/Jalali label for Gemini to copy."""
    gregorian = datetime.strptime(iso_date, "%Y-%m-%d").date()
    jalali = jdatetime.date.fromgregorian(date=gregorian)
    gregorian_label = (
        f"{to_persian_digits(gregorian.day)} "
        f"{GREGORIAN_MONTHS[gregorian.month - 1]} "
        f"{to_persian_digits(gregorian.year)}"
    )
    jalali_label = (
        f"{to_persian_digits(jalali.day)} "
        f"{PERSIAN_MONTHS[jalali.month - 1]} "
        f"{to_persian_digits(jalali.year)}"
    )
    return f"{gregorian_label} ({jalali_label})"


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
    required_fields = [
        'time', 'temperature_2m_max', 'temperature_2m_min',
        'precipitation_sum', 'precipitation_probability_max',
        'windspeed_10m_max', 'winddirection_10m_dominant',
        'relative_humidity_2m_mean', 'weathercode'
    ]
    if not daily_data or any(field not in daily_data for field in required_fields):
        return f"داده‌ای برای مدل {model_name} دریافت نشد."

    row_count = min(len(daily_data[field]) for field in required_fields)
    if row_count == 0:
        return f"داده‌ای برای مدل {model_name} دریافت نشد."

    lines = [
        f"📍 پیش‌بینی {days} روزه برای {location_name} — مدل {model_name}",
        f"🕐 Generated: {datetime.now(ZoneInfo('Asia/Tehran')).strftime('%Y-%m-%d %H:%M')}",
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

    for i in range(min(days, row_count)):
        date = daily_data['time'][i]
        date_mapping = format_date_mapping(date)
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
            f"\n📅 {date} | {date_mapping} | {weather_desc}\n"
            f"   🌡️ ماکس: {t_max}°C | مین: {t_min}°C\n"
            f"   💧 بارش: {precip}mm ({precip_prob}% احتمال)\n"
            f"   💨 باد: {wind} km/h ({wind_dir}°)\n"
            f"   💦 رطوبت: {humidity}%"
        )

    return "\n".join(lines)


def analyze_with_gemini(api_key, model_name, forecast_texts, location_name, days):
    """Send all model forecasts to Gemini for comparative Persian analysis."""
    client = genai.Client(api_key=api_key)

    prompt = f"""تو یک متخصص هواشناسی با تجربه هستی که پیش‌بینی‌های چند مدل رو برای یک کاربر عادی تحلیل می‌کنی.

موقعیت: {location_name}
بازه: {days} روز آینده

قانون فنی تاریخ‌ها (الزامی): تاریخ هر روز در داده خام به‌صورت میلادی ISO و در کنار آن با mapping قطعی میلادی/شمسی آمده است. در پاسخ فقط از همین mapping استفاده کن و هرگز روز و ماه را جداگانه تبدیل یا حدس نزن. برای بازه‌ها نیز نام ماه میلادی و معادل شمسی را دقیقاً مطابق همین mapping بنویس؛ مثلاً «۱۴ تا ۱۹ آگوست (۲۳ تا ۲۸ مرداد)».

⚠️ **ترجیحات کاربر (بسیار مهم)**:
- از **گرما** و **رطوبت بالا** متنفره
- هوای «خوب» برایش یعنی: **سرد** (زیر ۱۵℃)، **کم‌رطوبت** (زیر ۵۰٪)، **بارانی**
- بارش برایش «عالی» فقط اگه همراه با هوای خنک باشه
- وقتی می‌گی «هوا خوب می‌شه» منظور تو نباید گرم/مرطوب باشه

داده‌های خام سه مدل پیش‌بینی:
{chr(10).join(forecast_texts)}

لطفاً یک تحلیل جامع، روان و «خودمانی» به فارسی تولید کن که شامل موارد زیر باشه:

1. **خلاصه کلی روزانه** (۲-۳ خط برای هر روز): چه انتظار داریم؟ بارش؟ تغییر دما؟ راحت باش یا چتر بگیر؟ **از منظر سلیقه کاربر (دوستدار هواهای خنک/بارشی) بنویس.**

2. **مقایسه مدل‌ها**: کدوم مدل چی می‌گه؟ کجا موافق هستن؟ کجا اختلاف دارن؟ چه مدل‌های روی هم سوار شدن و چه مدل‌ها دایورجن داده؟

3. **نکات فنی مهم**: اگر مدل‌های GFS، ECMWF، ICON رو می‌شناسی، دیدگاه اختصاصی هر کدوم رو توضیح بده:
   - GFS: مدل آمریکایی، چطور در این منطقه عمل می‌کنه؟
   - ECMWF: مدل اروپایی، چرا معمولاً دقیق‌تره؟
   - ICON: مدل آلمانی، چطور در عرض‌های جغرافیایی ایران رفتار می‌کنه؟

4. **پیشنهاد عملی**: برای هر روز، کاربر چه باید بکنه؟ (پیک آب‌وهوا، پوشیدن، برنامه‌ریزی بیرون رفتن) **با در نظر گرفتن نفرت از گرمای مرطوب.**

لحن: دوستانه، تخصصی ولی بدونژه، مثل یه دوست که از هواشناسی می‌فهمه و می‌خواد به دوستش کمک کنه.
از اموجی استفاده کن. ساختاردهی واضح با هدرها.
طول متن: کامل ولی خسته‌کننده نباش."""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text or "❌ پاسخ متنی از جمینای دریافت نشد."
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"❌ خطا در تحلیل جمینای: {e}"


async def send_telegram(bot_token, chat_id, text):
    """Send plain-text message chunks to Telegram."""
    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > 4000 and current:
            chunks.append(current)
            current = ""
        while len(line) > 4000:
            chunks.append(line[:4000])
            line = line[4000:]
        current += line
    if current or not chunks:
        chunks.append(current)

    async with Bot(token=bot_token) as bot:
        for index, chunk in enumerate(chunks):
            await bot.send_message(chat_id=chat_id, text=chunk)
            if index < len(chunks) - 1:
                await asyncio.sleep(0.5)


def main():
    config = load_config()

    # Read secrets from environment variables first (secure), fallback to config.yaml
    gemini_key = os.environ.get("GEMINI_API_KEY") or config['gemini'].get('api_key', '')
    tg_token = os.environ.get("TG_BOT_TOKEN") or config['telegram'].get('bot_token', '')
    chat_ids_env = os.environ.get('TG_CHAT_IDS', '')
    chat_ids = [item.strip() for item in chat_ids_env.split(',') if item.strip()]
    if not chat_ids:
        chat_ids = config['telegram'].get('chat_ids', [])
    if isinstance(chat_ids, (str, int)):
        chat_ids = [str(chat_ids)]

    lat = config['location']['latitude']
    lon = config['location']['longitude']
    loc_name = config['location']['name']
    days = config['forecast']['days']
    models = config['models']

    if not tg_token or tg_token == 'YOUR_TELEGRAM_BOT_TOKEN' or not chat_ids:
        logger.error("❌ Telegram credentials missing. Set TG_BOT_TOKEN and chat IDs.")
        sys.exit(1)
    if not gemini_key or gemini_key == 'YOUR_GEMINI_API_KEY':
        logger.error("❌ Gemini API key missing. Set GEMINI_API_KEY.")
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

    # Send to Telegram for all chat IDs. One invalid/inaccessible chat must not
    # prevent delivery to the remaining recipients.
    failed_chat_ids = []
    for chat_id in chat_ids:
        logger.info(f"Sending to Telegram chat ID: {chat_id}...")
        try:
            asyncio.run(send_telegram(tg_token, chat_id, analysis))
        except TelegramError as exc:
            failed_chat_ids.append(str(chat_id))
            logger.error(
                "Telegram delivery failed for chat ID %s: %s",
                chat_id,
                exc
            )
        except Exception:
            failed_chat_ids.append(str(chat_id))
            logger.exception("Unexpected delivery failure for chat ID %s", chat_id)

    if failed_chat_ids:
        logger.warning("Failed Telegram chat IDs: %s", ', '.join(failed_chat_ids))
    if len(failed_chat_ids) == len(chat_ids):
        logger.error("Telegram delivery failed for every configured chat ID.")
        sys.exit(1)
    logger.info("✅ Done!")


if __name__ == "__main__":
    main()
