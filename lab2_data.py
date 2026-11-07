"""ЛР №2: модельні умови, витрати, власна генерація та CO₂.
Дані синтетичні, створені для навчальної задачі; не звітність кінотеатру.
"""
import calendar
import math
from database import get_connection
from energy_data import find_tariff

MONTHLY_KYIV_TEMPS = [-2.0, -1.0, 4.0, 11.0, 16.0, 20.0, 22.0, 21.0, 16.0, 10.0, 4.0, 0.0]
HEATED_AREAS_M2 = {
    'Кінозали': 1500.0,
    'Кіномаркет': 320.0,
    'Фойє': 460.0,
    'Адміністративно-технічна зона': 350.0,
}
# Умовні фактори, а НЕ перевірені коефіцієнти для конкретного підприємства.
CO2_ELECTRIC_KG_PER_KWH = 0.40
CO2_HEAT_KG_PER_GCAL = 230.0
GCAL_TO_KWH = 1162.22


def create_lab2_schema():
    conn = get_connection()
    try:
        columns = {r[1] for r in conn.execute('PRAGMA table_info(departments)')}
        if 'heated_area' not in columns:
            conn.execute('ALTER TABLE departments ADD COLUMN heated_area REAL CHECK(heated_area >= 0)')
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS monthly_conditions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          department_id INTEGER NOT NULL REFERENCES departments(id),
          year INTEGER NOT NULL, month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
          working_days INTEGER NOT NULL CHECK(working_days BETWEEN 0 AND 31),
          outdoor_temp REAL, indoor_temp REAL,
          UNIQUE(department_id, year, month)
        );
        CREATE TABLE IF NOT EXISTS monthly_finances (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          department_id INTEGER NOT NULL REFERENCES departments(id),
          year INTEGER NOT NULL, month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
          total_expenses REAL NOT NULL CHECK(total_expenses >= 0),
          UNIQUE(department_id, year, month)
        );
        CREATE TABLE IF NOT EXISTS monthly_generation (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          department_id INTEGER NOT NULL REFERENCES departments(id),
          resource_id INTEGER NOT NULL REFERENCES resources(id),
          year INTEGER NOT NULL, month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
          amount REAL NOT NULL CHECK(amount >= 0),
          UNIQUE(department_id, resource_id, year, month)
        );
        CREATE TABLE IF NOT EXISTS monthly_electricity_breakdown (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          department_id INTEGER NOT NULL REFERENCES departments(id),
          year INTEGER NOT NULL, month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
          lighting_kwh REAL NOT NULL CHECK(lighting_kwh >= 0),
          cooling_kwh REAL NOT NULL CHECK(cooling_kwh >= 0),
          other_kwh REAL NOT NULL CHECK(other_kwh >= 0),
          UNIQUE(department_id, year, month)
        );
        CREATE TABLE IF NOT EXISTS monthly_emissions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          department_id INTEGER NOT NULL REFERENCES departments(id),
          year INTEGER NOT NULL, month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
          co2_kg REAL NOT NULL CHECK(co2_kg >= 0),
          UNIQUE(department_id, year, month)
        );
        ''')
        conn.commit()
    finally:
        conn.close()


def populate_lab2_model():
    """Заповнення відсутніх модельних даних; повторний запуск без дублювання."""
    create_lab2_schema()
    conn = get_connection()
    try:
        depts = conn.execute("SELECT id,name FROM departments WHERE type='Підрозділ' ORDER BY id").fetchall()
        resource_ids = {name: rid for rid, name in conn.execute('SELECT id,name FROM resources')}
        electricity_id = resource_ids['Електроенергія']
        for dept_id, name in depts:
            area = HEATED_AREAS_M2.get(name)
            if area is not None:
                conn.execute('UPDATE departments SET heated_area = COALESCE(heated_area, ?) WHERE id=?', (area,dept_id))
            for year in range(2016,2026):
                for month in range(1,13):
                    days_in_month = calendar.monthrange(year,month)[1]
                    closed = (year == 2020 and month in (4,5))
                    working_days = 0 if closed else days_in_month
                    temp = MONTHLY_KYIV_TEMPS[month-1] + round(0.35 * math.sin(year * 2 + month),1)
                    indoor = 22.0 if month in (6,7,8) else 20.5
                    conn.execute('''INSERT OR IGNORE INTO monthly_conditions
                       (department_id,year,month,working_days,outdoor_temp,indoor_temp)
                       VALUES (?,?,?,?,?,?)''', (dept_id,year,month,working_days,temp,indoor))
                    # Реалізація сценарію власної генерації: УМОВНІ сонячні панелі з 2023 р.
                    if name == 'Адміністративно-технічна зона':
                        solar = 0.0
                        if year >= 2023 and not closed:
                            solar = round((750 + 550 * max(0, math.sin((month-2) * math.pi / 12))) * (1 + 0.02*(year-2023)),2)
                        conn.execute('''INSERT OR IGNORE INTO monthly_generation
                           (department_id,resource_id,year,month,amount)
                           VALUES (?,?,?,?,?)''',(dept_id,electricity_id,year,month,solar))
                    # Умовний розподіл споживання електроенергії:
                    # освітлення / кондиціювання / інше (без лічильників це лише модель).
                    electricity = conn.execute('''SELECT c.amount FROM consumption c JOIN resources r ON r.id=c.resource_id
                        WHERE c.department_id=? AND c.year=? AND c.month=?
                        AND r.name='Електроенергія' ''',(dept_id,year,month)).fetchone()
                    electricity_amount = float(electricity[0]) if electricity else 0.0
                    lighting = round(electricity_amount * (0.27 if name=='Кінозали' else 0.32),4)
                    cooling = round(electricity_amount * (0.34 if month in (6,7,8) else 0.09),4)
                    others = round(electricity_amount-lighting-cooling,4)
                    conn.execute('''INSERT OR IGNORE INTO monthly_electricity_breakdown
                        (department_id,year,month,lighting_kwh,cooling_kwh,other_kwh)
                        VALUES(?,?,?,?,?,?)''',(dept_id,year,month,lighting,cooling,others))
                    # Фінансова модель: енергія + інші ресурси + умовні операційні витрати.
                    items = conn.execute('''SELECT c.resource_id,c.amount,r.name FROM consumption c
                        JOIN resources r ON r.id=c.resource_id
                        WHERE c.department_id=? AND c.year=? AND c.month=?''',(dept_id,year,month)).fetchall()
                    resource_cost = 0.0
                    for resource_id, amount, _ in items:
                        price = find_tariff(conn,resource_id,dept_id,year,month)
                        if price is not None:
                            resource_cost += amount*price
                    baseline = {'Кінозали':220000,'Кіномаркет':70000,'Фойє':85000,'Адміністративно-технічна зона':95000}.get(name,50000)
                    expenses = round(resource_cost * 1.4 + (0 if closed else baseline * (1.05 ** (year - 2016))),2)
                    conn.execute('''INSERT OR IGNORE INTO monthly_finances
                       (department_id,year,month,total_expenses) VALUES (?,?,?,?)''',
                       (dept_id,year,month,expenses))
        conn.commit()
    finally:
        conn.close()
    refresh_emissions()
    refresh_electricity_breakdown()


def refresh_electricity_breakdown():
    """Синхронізує освітлення / кондиціювання після ручного редагування ЛР №1.
    Частки модельні; окремих лічильників у вихідній базі немає.
    """
    conn = get_connection()
    try:
        rows = conn.execute("""SELECT c.department_id,d.name,c.year,c.month,c.amount
           FROM consumption c
           JOIN resources r ON r.id=c.resource_id
           JOIN departments d ON d.id=c.department_id
           WHERE r.name='Електроенергія'""").fetchall()
        for did,name,year,month,amount in rows:
            lighting = round(amount * (0.27 if name=='Кінозали' else 0.32),4)
            cooling = round(amount * (0.34 if month in (6,7,8) else 0.09),4)
            other = round(amount - lighting - cooling,4)
            conn.execute("""INSERT INTO monthly_electricity_breakdown
              (department_id,year,month,lighting_kwh,cooling_kwh,other_kwh)
              VALUES(?,?,?,?,?,?)
              ON CONFLICT(department_id,year,month) DO UPDATE SET
              lighting_kwh=excluded.lighting_kwh,
              cooling_kwh=excluded.cooling_kwh,
              other_kwh=excluded.other_kwh""",(did,year,month,lighting,cooling,other))
        conn.commit()
    finally:
        conn.close()


def refresh_emissions():
    """Оновлює розрахункові викиди із поточних показників споживання."""
    conn = get_connection()
    try:
        rows = conn.execute('''SELECT c.department_id,c.year,c.month,
            SUM(CASE WHEN r.name='Електроенергія' THEN c.amount ELSE 0 END),
            SUM(CASE WHEN r.name='Теплова енергія' THEN c.amount ELSE 0 END)
            FROM consumption c JOIN resources r ON r.id=c.resource_id
            GROUP BY c.department_id,c.year,c.month''').fetchall()
        for dept,year,month,electricity,heat in rows:
            kg = round(electricity*CO2_ELECTRIC_KG_PER_KWH + heat*CO2_HEAT_KG_PER_GCAL,3)
            conn.execute('''INSERT INTO monthly_emissions(department_id,year,month,co2_kg)
               VALUES(?,?,?,?) ON CONFLICT(department_id,year,month)
               DO UPDATE SET co2_kg=excluded.co2_kg''',(dept,year,month,kg))
        conn.commit()
    finally:
        conn.close()


def refresh_finances():
    """Не перераховує довільні фінансові дані користувача; фінансовий план редагується окремо."""
    return None


if __name__ == '__main__':
    populate_lab2_model()
    print('Модельні показники лабораторної №2 сформовано.')
