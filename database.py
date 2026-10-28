
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "energy.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Підприємство та його підрозділи
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            parent_id INTEGER,
            FOREIGN KEY (parent_id)
                REFERENCES departments(id)
        )
    """)

    # 2. Довідник ресурсів
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            unit TEXT NOT NULL
        )
    """)

    # 3. Тарифи з періодами дії
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tariffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL,
            department_id INTEGER,
            price REAL NOT NULL CHECK(price >= 0),
            start_date TEXT NOT NULL,
            end_date TEXT,
            FOREIGN KEY (resource_id)
                REFERENCES resources(id),
            FOREIGN KEY (department_id)
                REFERENCES departments(id)
        )
    """)

    # 4. Помісячне споживання ресурсів
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL
                CHECK(month BETWEEN 1 AND 12),
            amount REAL NOT NULL CHECK(amount >= 0),

            UNIQUE(department_id, resource_id, year, month),

            FOREIGN KEY (department_id)
                REFERENCES departments(id),
            FOREIGN KEY (resource_id)
                REFERENCES resources(id)
        )
    """)

    # 5. Обсяги виробництва продукції та послуг
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL
                CHECK(month BETWEEN 1 AND 12),
            revenue REAL NOT NULL CHECK(revenue >= 0),

            UNIQUE(department_id, year, month),

            FOREIGN KEY (department_id)
                REFERENCES departments(id)
        )
    """)
    cursor.execute("""
         CREATE TABLE IF NOT EXISTS department_resources (
             department_id INTEGER NOT NULL,
             resource_id INTEGER NOT NULL,

             PRIMARY KEY (department_id, resource_id),

             FOREIGN KEY (department_id)
                 REFERENCES departments(id),

             FOREIGN KEY (resource_id)
                 REFERENCES resources(id)
         )
     """)
    conn.commit()
    conn.close()


def seed_data():
    conn = get_connection()
    cursor = conn.cursor()

    # Додаємо підприємство та умовні зони обліку
    cursor.execute("SELECT COUNT(*) FROM departments")

    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO departments (name, type, parent_id)
            VALUES (?, ?, NULL)
        """, ("Планета Кіно — Блокбастер", "Підприємство"))

        company_id = cursor.lastrowid

        departments = [
            ("Кінозали", "Підрозділ", company_id),
            ("Кіномаркет", "Підрозділ", company_id),
            ("Фойє", "Підрозділ", company_id),
            ("Адміністративно-технічна зона",
             "Підрозділ", company_id)
        ]

        cursor.executemany("""
            INSERT INTO departments (name, type, parent_id)
            VALUES (?, ?, ?)
        """, departments)

    # Створюємо довідник ресурсів
    resources = [
        ("Електроенергія", "кВт·год"),
        ("Теплова енергія", "Гкал"),
        ("Холодна вода", "тис. м³"),
        ("Водовідведення", "тис. м³"),
        ("Тверді побутові відходи", "т")
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO resources (name, unit)
        VALUES (?, ?)
    """, resources)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    seed_data()

    print("Базу даних успішно створено!")

    conn = get_connection()

    print("\nСтруктура підприємства:")
    for row in conn.execute(
        "SELECT id, name, type, parent_id FROM departments"
    ):
        print(row)

    print("\nРесурси:")
    for row in conn.execute(
        "SELECT id, name, unit FROM resources"
    ):
        print(row)

    conn.close()
