
from database import get_connection

conn = get_connection()

# Перевіряємо кількість записів
tables = [
    "departments",
    "resources",
    "department_resources",
    "tariffs",
    "consumption",
    "production"
]

print("=== ПЕРЕВІРКА БАЗИ ДАНИХ ===")

for table in tables:
    count = conn.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(f"{table}: {count} записів")

# Перевіряємо покриття за роками
print("\n=== ДАНІ ЗА РОКАМИ ===")

rows = conn.execute("""
    SELECT year, COUNT(*)
    FROM consumption
    GROUP BY year
    ORDER BY year
""").fetchall()

for year, count in rows:
    print(f"{year}: {count} записів")

# Перевіряємо виробництво послуг
print("\n=== ВИРОБНИЦТВО ПОСЛУГ ===")

production = conn.execute("""
    SELECT COUNT(*)
    FROM production
""").fetchone()[0]

print(f"Записів про послуги: {production}")

# Перевіряємо цілісність зв'язків
errors = conn.execute(
    "PRAGMA foreign_key_check"
).fetchall()

if errors:
    print("\nЗнайдено помилки зв'язків:", errors)
else:
    print("\nПомилок зовнішніх ключів немає!")

conn.close()
