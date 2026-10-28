
import random
from datetime import date

from database import get_connection


YEARS = list(range(2016, 2026))

MONTHS = [
    "Січень", "Лютий", "Березень", "Квітень",
    "Травень", "Червень", "Липень", "Серпень",
    "Вересень", "Жовтень", "Листопад", "Грудень"
]

# Модельні межі споживання за місяць.
# Для води значення задані в тис. м³.
BASE_RANGES = {
    "Кінозали": {
        "Електроенергія": (15000, 25000),
        "Теплова енергія": (12, 24)
    },
    "Кіномаркет": {
        "Електроенергія": (2000, 4500),
        "Теплова енергія": (3, 7),
        "Холодна вода": (0.025, 0.065),
        "Водовідведення": (0.020, 0.055),
        "Тверді побутові відходи": (0.6, 1.7)
    },
    "Фойє": {
        "Електроенергія": (4000, 7500),
        "Теплова енергія": (6, 13),
        "Холодна вода": (0.040, 0.090),
        "Водовідведення": (0.035, 0.080),
        "Тверді побутові відходи": (0.4, 1.0)
    },
    "Адміністративно-технічна зона": {
        "Електроенергія": (2500, 5000),
        "Теплова енергія": (4, 9),
        "Холодна вода": (0.015, 0.040),
        "Водовідведення": (0.012, 0.035),
        "Тверді побутові відходи": (0.15, 0.5)
    }
}


def seasonal_factor(resource, month):
    """Модельна залежність споживання від сезону."""

    winter = month in (12, 1, 2)
    summer = month in (6, 7, 8)

    if resource == "Теплова енергія":
        if winter:
            return 1.5
        if summer:
            return 0.15
        return 0.7

    if resource == "Електроенергія":
        if summer:
            return 1.25
        if winter:
            return 1.1

    return 1.0


def generate_consumption():
    """Генерує дані, не перезаписуючи наявні."""

    rng = random.Random(2026)
    conn = get_connection()

    try:
        assignments = conn.execute("""
            SELECT d.id, d.name, r.id, r.name, r.unit
            FROM department_resources dr
            JOIN departments d
                ON d.id = dr.department_id
            JOIN resources r
                ON r.id = dr.resource_id
            ORDER BY d.id, r.id
        """).fetchall()

        if not assignments:
            return 0, 0

        added = 0

        for dept_id, dept_name, res_id, res_name, unit in assignments:
            limits = BASE_RANGES.get(dept_name, {})
            low, high = limits.get(res_name, (1, 10))

            for year in YEARS:
                for month in range(1, 13):

                    # Умовний сценарій призупинення
                    # роботи у квітні-травні 2020 року.
                    if year == 2020 and month in (4, 5):
                        amount = 0.0
                    else:
                        base = rng.uniform(low, high)
                        season = seasonal_factor(res_name, month)

                        # Умовна поступова зміна споживання
                        trend = 1 + 0.012 * (year - 2016)

                        amount = round(
                            base * season * trend, 4
                        )

                    cursor = conn.execute("""
                        INSERT OR IGNORE INTO consumption
                            (department_id, resource_id,
                             year, month, amount)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        dept_id, res_id, year,
                        month, amount
                    ))

                    added += cursor.rowcount

        # Модельні обсяги реалізації кінопоказів
        cinema = conn.execute("""
            SELECT id
            FROM departments
            WHERE name = 'Кінозали'
            LIMIT 1
        """).fetchone()

        production_added = 0

        if cinema:
            cinema_id = cinema[0]

            for year in YEARS:
                for month in range(1, 13):

                    if year == 2020 and month in (4, 5):
                        revenue = 0.0
                    else:
                        revenue = round(
                            rng.uniform(600000, 1300000)
                            * (1.045 ** (year - 2016)),
                            2
                        )

                    cursor = conn.execute("""
                        INSERT OR IGNORE INTO production
                            (department_id, year, month, revenue)
                        VALUES (?, ?, ?, ?)
                    """, (
                        cinema_id, year, month, revenue
                    ))

                    production_added += cursor.rowcount

        conn.commit()
        return added, production_added

    finally:
        conn.close()


def find_tariff(conn, resource_id, department_id, year, month):
    """Шукає тариф на перше число місяця.

    Тариф підрозділу має пріоритет над загальним.
    """

    month_date = date(year, month, 1).isoformat()

    row = conn.execute("""
        SELECT price
        FROM tariffs
        WHERE resource_id = ?
          AND (department_id = ? OR department_id IS NULL)
          AND start_date <= ?
          AND (end_date IS NULL OR end_date >= ?)
        ORDER BY
            CASE WHEN department_id = ? THEN 0 ELSE 1 END,
            start_date DESC
        LIMIT 1
    """, (
        resource_id, department_id,
        month_date, month_date, department_id
    )).fetchone()

    return row[0] if row else None


def build_report(year, department_id=None):
    """Формує таблицю за зразком 1.7 методички."""

    conn = get_connection()

    try:
        query = """
            SELECT
                c.department_id, c.resource_id,
                r.name, r.unit, c.month, c.amount
            FROM consumption c
            JOIN resources r ON r.id = c.resource_id
            WHERE c.year = ?
        """

        params = [year]

        if department_id is not None:
            query += " AND c.department_id = ?"
            params.append(department_id)

        query += " ORDER BY r.id, c.month"

        rows = conn.execute(query, params).fetchall()

        values = {}
        costs = {}
        missing_tariffs = set()

        for dept_id, res_id, name, unit, month, amount in rows:
            key = (res_id, name, unit)

            if key not in values:
                values[key] = [0.0] * 12
                costs[key] = [0.0] * 12

            values[key][month - 1] += amount

            tariff = find_tariff(
                conn, res_id, dept_id, year, month
            )

            if tariff is None:
                missing_tariffs.add((name, year, month))
            else:
                costs[key][month - 1] += amount * tariff

        report = []

        def add_row(label, numbers, unit):
            record = {
                "Показник": label,
                "Од. виміру": unit
            }

            for i, month_name in enumerate(MONTHS):
                record[month_name] = round(numbers[i], 2)

            record["Усього за рік"] = round(
                sum(numbers), 2
            )
            report.append(record)

        for key, monthly in values.items():
            _, name, unit = key

            add_row(
                f"Споживання: {name}",
                monthly,
                unit
            )

            add_row(
                f"Витрати: {name}",
                costs[key],
                "грн"
            )

        # Додаємо обсяги виробництва послуг
        production_query = """
            SELECT month, SUM(revenue)
            FROM production
            WHERE year = ?
        """
        production_params = [year]

        if department_id is not None:
            production_query += " AND department_id = ?"
            production_params.append(department_id)

        production_query += " GROUP BY month"

        production_rows = conn.execute(
            production_query, production_params
        ).fetchall()

        if production_rows:
            production_values = [0.0] * 12

            for month, revenue in production_rows:
                production_values[month - 1] = revenue

            add_row(
                "Обсяги виробництва продукції та послуг",
                production_values,
                "грн"
            )

        return report, missing_tariffs

    finally:
        conn.close()
