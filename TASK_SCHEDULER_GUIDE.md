# Task Scheduler Setup for Weather Bot (Windows)

## روش سریع: Import Task (پیشنهادی)

1. فایل `weather_bot_task.xml` رو دانلود/کپی کن (در همین پوشه)
2. `Win + R` → `taskschd.msc` → Enter
3. در پنل راست: **Import Task...** → فایل XML رو انتخاب → OK
4. در دیالوگ: **Run whether user is logged on or not** تیک بزن → OK
5. رمز ویندوزت رو وارد کن → OK

---

## روش دستی (گام‌به‌گام)

### ۱. باز کردن Task Scheduler
```
Win + R → taskschd.msc → Enter
```

### ۲. Create Task (نه Basic Task)
در پنل راست: **Create Task...**

### ۳. تب General
- **Name**: `Weather Bot - نوشهر`
- **Description**: `Runs weather forecast analysis every Friday & Tuesday at 23:00`
- ✅ **Run whether user is logged on or not** ← **مهم**
- ✅ **Run with highest privileges**
- **Configure for**: `Windows 10` (یا 11)

### ۴. تب Triggers → New...
- **Begin the task**: `On a schedule`
- **Settings**: `Weekly`
- **Start**: امروز، ساعت `23:00:00`
- ✅ **Friday** و ✅ **Tuesday** (بقیه رو بردار)
- ✅ **Enabled**
- OK

### ۵. تب Actions → New...
- **Action**: `Start a program`
- **Program/script**: `C:\Users\Ebi\workspace\weather_bot\run_weather_bot.bat`
- **Add arguments**: (خالی بذار)
- **Start in**: `C:\Users\Ebi\workspace\weather_bot`
- OK

### ۶. تب Conditions
- ❌ **Start the task only if the computer is on AC power** (برداش، برای لپ‌تاپ)
- ❌ **Stop if the computer switches to battery power** (برداش)
- ✅ **Wake the computer to run this task** ← **مهم** (سیستم از Sleep بیدار میشه)
- ❌ **Start only if network available** (اختیاری)

### ۷. تب Settings
- ✅ **Allow task to be run on demand**
- ✅ **Run task as soon as possible after a scheduled start is missed**
- ❌ **Stop the task if it runs longer than**: (خالی/پیش‌فرض)
- ✅ **If the running task does not end when requested, force it to stop**
- **If the task is already running**: `Do not start a new instance`
- OK

### ۸. ورود رمز
بعد از OK، ویندوز رمز کاربریت رو می‌پرسه (برای Run whether user is logged on or not). وارد کن.

---

## ✅ تست کردن

در Task Scheduler:
1. Task رو پیدا کن → راست‌کلیک → **Run**
2. تب **History** رو فعال کن (اگر غیرفعاله: در پنل راست **Enable All Tasks History**)
3. لاگ‌ها رو چک کن — باید `✅ Done!` رو ببینی

---

## ⚡ نکات مهم برای لپ‌تاپ

| حالت | کار می‌کنه؟ | نکته |
|------|-------------|------|
| **روشن (On)** | ✅ بله | عادی اجرا میشه |
| **Sleep** | ✅ بله (اگه Wake Timer روشن باشه) | تب Conditions → **Wake the computer** تیک داشته باشه |
| **Hibernate** | ✅ بله (اگه Wake Timer روشن باشه) | مثل Sleep |
| **Shutdown / Off** | ❌ خیر | سیستم باید روشن باشه |
| **Battery saver / Modern Standby** | ⚠️ شاید | برخی لپ‌تاپ‌های جدید Wake Timer رو در باطری غیرفعال می‌کنن |

### چک کردن Wake Timer:
```powershell
powercfg /waketimers
```
اگر خالی بود، یعنی فعاله. اگه غیرفعاله:
```powershell
powercfg /deviceenablewake "System Device"  # معمولاً کافیه
```

---

## 🔧 عیب‌یابی

| مشکل | راه حل |
|-------|--------|
| Task اجرا نمیشه | History چک کن → Event Viewer → TaskScheduler |
| "Access denied" | Run with highest privileges تیک داره؟ رمز درست وارد شده؟ |
| Python not found | در bat فایل، مسیر کامل python.exe رو بذار: `C:\Users\Ebi\AppData\Local\Programs\Python\Python314\python.exe` |
| Env vars خالی | در bat فایل مقادیر واقعی رو ست کردی؟ |
| در باطری Wake نمیشه | Power Options → Change plan settings → Change advanced → Sleep → Allow wake timers → Enable |

---

## 📁 فایل‌های مرتبط

```
weather_bot/
├── run_weather_bot.bat      # ← اجرای با env vars
├── weather_bot_task.xml     # ← برای Import سریع
├── weather_bot.py
├── config.yaml
└── ...
```