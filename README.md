# Telegram Kino Boti (Python)

Ushbu loyiha Telegram orqali kinolarni kodlari bo'yicha qidirish va yuklab olish imkonini beruvchi bot hisoblanadi. Bot zamonaviy **python-telegram-bot v20+ (async API)** va **SQLite** bazasida qurilgan.

---

## 🚀 Imkoniyatlar

- **Foydalanuvchilar uchun:**
  - `/start` — Botni ishga tushirish va tanishuv.
  - Kod yuborish — Kinoning raqamli yoki matnli kodini yuborganda, bot avtomatik tarzda kinoni (video yoki fayl) sarlavhasi bilan yuboradi.
  - `/help` — Botdan foydalanish bo'yicha qo'llanma.

- **Adminlar uchun:**
  - `/addmovie` — Bosqichma-bosqich kino yuklash (Fayl -> Kod -> Nom).
  - **Tezkor yuklash (Quick mode):** Video yoki hujjatni sarlavhasiga `kod | nom` (masalan: `101 | Forsaj 10`) deb yozib yuborish orqali bir zumda saqlash.
  - `/delmovie <kod>` — Kinoni kod bo'yicha o'chirish.
  - `/listmovies` — Bazadagi oxirgi 20 ta kinoni ko'rish.
  - `/stats` — Umumiy kinolar, foydalanuvchilar va adminlar statistikasi.
  - `/broadcast` — Barcha foydalanuvchilarga xabar tarqatish (bloklagan foydalanuvchilar hisobga olinadi).

- **Super Admin uchun:**
  - `/addadmin <user_id>` — Yangi admin qo'shish (yoki foydalanuvchi xabariga `reply` qilib).
  - `/deladmin <user_id>` — Adminni o'chirish.
  - `/admins` — Barcha adminlar ro'yxatini ko'rish.
  - *Super Admin huquqi `.env` faylida belgilanadi va uni o'chirib bo'lmaydi.*

- **Xavfsizlik va barqarorlik:**
  - Admin buyruqlari begona foydalanuvchilar uchun yashirin (javob qaytarmaydi).
  - Kodlarda probel bo'lmasligi va 20 belgidan oshmasligi tekshiriladi.
  - Xatoliklar `bot.log` fayliga yozib boriladi va tarmoq uzilishlarida avtomatik qayta ulanadi.

---

## 🛠 O'rnatish va Sozlash

### 1. Telegram Bot Tokenini olish
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/newbot` buyrug'ini yuboring va botingizga nom hamda username bering.
3. BotFather sizga **HTTP API token** beradi (masalan: `7123456789:AAH...`).

### 2. O'zingizning Telegram ID'ingizni aniqlash
1. Telegramda [@userinfobot](https://t.me/userinfobot) botiga `/start` yuboring.
2. Bot sizga `Id:` qatorida raqamli ID'ingizni beradi (masalan: `123456789`). Bu sizning `SUPER_ADMIN_ID`ingiz bo'ladi.

### 3. `.env` faylini to'ldirish
Loyiha papkasida `.env` faylini oching (yoki `.env.example` dan nusxa oling) va o'z ma'lumotlaringizni kiriting:

```env
BOT_TOKEN=1234567890:AAFxxxxxxxxx_your_token_here
SUPER_ADMIN_ID=123456789
DATABASE_PATH=kino_bot.db
LOG_FILE=bot.log
```

---

## 📦 Kutubxonalarni o'rnatish

Terminal yoki buyruqlar satrida (PowerShell / CMD) loyiha papkasiga kiring va quyidagi buyruqni bajaring:

```bash
pip install -r requirements.txt
```

---

## 🎬 Botni ishga tushirish

Botni ishga tushirish uchun quyidagi buyruqni bering:

```bash
python main.py
```

> **Eslatma:** Birinchi marta ishga tushirilganda SQLite ma'lumotlar bazasi (`kino_bot.db`) va barcha jadvallar avtomatik yaratiladi!

---

## 👑 Birinchi adminni qo'shish

1. `.env` faylidagi `SUPER_ADMIN_ID` ga o'z ID raqamingizni kiritganingiz sababli, bot sizni **Super Admin** sifatida taniydi.
2. Qo'shimcha admin qo'shish uchun:
   - Botga kiring va `/start` bosing.
   - Yangi admin qilmoqchi bo'lgan shaxsning ID sini bilib oling va quyidagicha yuboring:
     ```text
     /addadmin 987654321
     ```
   - Yoki foydalanuvchining botga yozgan xabariga reply (javob) qilib `/addadmin` deb yuboring.
3. Barcha adminlarni ko'rish uchun: `/admins`.

---

## 📂 Loyiha tuzilishi

```text
kino bot/
├── main.py            # Asosiy kirish nuqtasi, handlerlar va xatoliklar ushlovchisi
├── config.py          # .env sozlamalarini yuklovchi modul
├── database.py        # SQLite ma'lumotlar bazasi bilan ishlash
├── handlers/
│   ├── user.py        # Oddiy foydalanuvchilar uchun handlerlar (/start, /help, qidiruv)
│   └── admin.py       # Admin va Super Admin buyruqlari (/addmovie, /delmovie, /broadcast...)
├── .env               # Maxfiy token va sozlamalar
├── .env.example       # Namuna sozlamalar
├── requirements.txt   # Kerakli Python kutubxonalari
└── README.md          # O'rnatish va foydalanish qo'llanmasi
```
