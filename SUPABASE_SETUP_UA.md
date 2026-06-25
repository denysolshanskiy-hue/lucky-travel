# 🚀 Інструкція з інтеграції Supabase

## Крок 1: Створення проекту на Supabase

1. Перейди на https://supabase.com
2. Натисни "Create new project"
3. Заповни дані проекту:
   - **Project name**: Назва для твого бота (напр. "kayak-bot")
   - **Password**: Надійний пароль для PostgreSQL
   - **Region**: Вибери найближчий регіон (напр. Europe - Frankfurt)
4. Зачекай, поки проект буде створений (~2 хвилини)

## Крок 2: Отримання ключів API

1. Перейди в проект → Settings → API
2. Скопіюй:
   - **Project URL** (SUPABASE_URL) - виглядає як `https://xxxxx.supabase.co`
   - **anon public** ключ (SUPABASE_KEY) - копіюй ключ для анонімного доступу

## Крок 3: Створення таблиць у Supabase

1. У проекті натисни **SQL Editor** (ліва панель)
2. Натисни **New Query**
3. Скопіюй і виконай цей SQL код:

```sql
-- Таблиця турів
CREATE TABLE tours (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  title TEXT NOT NULL,
  starts_at TEXT NOT NULL,
  adult_price INTEGER NOT NULL DEFAULT 0,
  child_price INTEGER NOT NULL DEFAULT 0,
  prepay INTEGER,
  seats_total INTEGER NOT NULL DEFAULT 0,
  kind TEXT NOT NULL,
  photo_file_id TEXT,
  included TEXT NOT NULL,
  route TEXT NOT NULL,
  payment_url TEXT,
  instructor_contact TEXT,
  car_number TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

-- Таблиця бронювань турів
CREATE TABLE bookings (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  tour_id BIGINT NOT NULL REFERENCES tours(id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL,
  username TEXT,
  full_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  people_count INTEGER NOT NULL,
  ages TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  reminder_3d_sent INTEGER NOT NULL DEFAULT 0,
  reminder_1d_sent INTEGER NOT NULL DEFAULT 0
);

-- Таблиця кемпінгу
CREATE TABLE camping_bookings (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id BIGINT NOT NULL,
  username TEXT,
  full_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  option_code TEXT NOT NULL,
  option_title TEXT NOT NULL,
  item_type TEXT NOT NULL,
  item_number INTEGER NOT NULL DEFAULT 0,
  units INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'booked',
  booking_date TEXT,
  created_at TEXT NOT NULL
);

-- Таблиця бронювань прокату
CREATE TABLE rental_bookings (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  user_id BIGINT NOT NULL,
  username TEXT,
  full_name TEXT NOT NULL,
  booking_date TEXT,
  phone TEXT NOT NULL,
  rental_title TEXT NOT NULL,
  rental_price INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL
);

-- Індекси для оптимізації
CREATE INDEX idx_bookings_tour_id ON bookings(tour_id);
CREATE INDEX idx_bookings_user_id ON bookings(user_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_camping_user_id ON camping_bookings(user_id);
CREATE INDEX idx_rental_user_id ON rental_bookings(user_id);
```

## Крок 4: Налаштування .env файлу

1. Відкрий файл `.env` у папці проекту
2. Додай або оновиши параметри:

```env
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_IDS=your_telegram_id_1,your_telegram_id_2
MONO_PAYMENT_URL=https://send.monobank.ua/jar/...
CAMPING_PAYMENT_URL=https://send.monobank.ua/jar/...

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key-here
```

## Крок 5: Встановлення залежностей

Виконай команду в терміналі:

```bash
pip install -r requirements.txt
```

## Крок 6: Запуск бота

```bash
python bot.py
```

---

## 🔄 Міграція даних з SQLite (якщо потрібна)

Якщо у тебе вже був bot.db з даними:

1. Експортуй дані з SQLite
2. Використай Supabase web interface для імпорту

Або створи скрипт миграції (напиши на запит, допоможу).

## ⚠️ Важні замітки

- **Суточний ліміт запитів**: Free tier має обмеження на кількість запитів
- **Безпека**: Никогда не публікуй SUPABASE_KEY на GitHub - триматим у `.env`
- **Backup**: Supabase автоматично робить резервні копії
- **PostgreSQL**: Supabase використовує PostgreSQL - це краще ніж SQLite для частих запитів

## 📞 Troubleshooting

### "SUPABASE_URL is missing"
→ Перевір, чи додав SUPABASE_URL в .env файл

### "SUPABASE_KEY is missing"
→ Скопіюй anon key з Settings → API

### "Таблиця не існує"
→ Запусти SQL код з кроку 3 ще раз

### Помилки підключення
→ Перевір інтернет-з'єднання та правильність ключів
