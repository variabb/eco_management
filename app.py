
import sqlite3
import streamlit as st
import pandas as pd
from datetime import date

from database import get_connection, init_db, seed_data
from energy_data import (
    YEARS, MONTHS,
    generate_consumption,
    build_report
)


# Ініціалізація бази даних
init_db()
seed_data()

st.set_page_config(
    page_title="Eco Energy Management",
    page_icon="🍿",
    layout="wide"
)


# Робота з базою даних
def fetch_data(query, params=()):
    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return rows
    finally:
        conn.close()


def execute_query(query, params=()):
    conn = get_connection()
    try:
        conn.execute(query, params)
        conn.commit()
    finally:
        conn.close()


# Стилізація
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3 {
        font-weight: 650;
    }

    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 12px;
        padding: 16px;
    }
</style>
""", unsafe_allow_html=True)


# Бічне меню
with st.sidebar:
    st.title("🍿 Planetakino")


    st.divider()

    page = st.radio(
        "Навігація",
        [
            "🏠 Огляд",
            "🏢 Підрозділи",
            "⚡ Ресурси",
            "🔗 Енергетичний паспорт",
            "💰 Тарифи",
            "📊 Споживання ресурсів"
        ]
    )

    st.divider()
    st.caption("Лабораторна робота №1")
    st.caption("Комп'ютерний еко-енергетичний менеджмент")


# Сторінка 1. Огляд
if page == "🏠 Огляд":
    st.title("🏠 Панель управління")
    st.subheader("Планета Кіно — Блокбастер")

    st.write(
        "Система обліку та моніторингу споживання "
        "енергетичних ресурсів кінотеатру."
    )

    st.divider()

    departments_count = fetch_data("""
        SELECT COUNT(*) FROM departments
        WHERE type = 'Підрозділ'
    """)[0][0]

    resources_count = fetch_data("""
        SELECT COUNT(*) FROM resources
    """)[0][0]

    consumption_count = fetch_data("""
        SELECT COUNT(*) FROM consumption
    """)[0][0]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("🏢 Підрозділи", departments_count)

    with col2:
        st.metric("⚡ Ресурси", resources_count)

    with col3:
        st.metric("📊 Записи споживання", consumption_count)

    st.divider()

    st.subheader("📍 Інформація про об'єкт")

    st.write("**Назва:** Планета Кіно — Блокбастер")
    st.write("**Місто:** Київ")
    st.write("**Адреса:** проспект Степана Бандери, 34В")
    st.write("**Сфера діяльності:** демонстрація кінофільмів")
    st.write("**Період дослідження:** 2016–2025 роки")

    st.info(
        "У системі використовуються модельні дані "
        "для навчального аналізу енергоспоживання."
    )


# Сторінка 2. Підрозділи
elif page == "🏢 Підрозділи":
    st.title("🏢 Структура підприємства")

    st.write(
        "Інвентаризація структурних одиниць "
        "та зон енергетичного обліку кінотеатру."
    )

    rows = fetch_data("""
        SELECT
            d.id,
            d.name,
            d.type,
            COALESCE(p.name, '—') AS parent_name
        FROM departments d
        LEFT JOIN departments p
            ON d.parent_id = p.id
        ORDER BY d.id
    """)

    st.subheader("Список структурних одиниць")

    table_data = [
        {
            "ID": row[0],
            "Назва": row[1],
            "Тип": row[2],
            "Підпорядкування": row[3]
        }
        for row in rows
    ]

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("➕ Додати підрозділ")

    parent_options = {
        f"{row[0]} — {row[1]}": row[0]
        for row in rows
    }

    with st.form("add_department"):
        name = st.text_input(
            "Назва підрозділу",
            placeholder="Наприклад, Склад обладнання"
        )

        parent_label = st.selectbox(
            "До якої структурної одиниці належить?",
            options=list(parent_options.keys())
        )

        submitted = st.form_submit_button(
            "Додати підрозділ",
            type="primary"
        )

        if submitted:
            if not name.strip():
                st.error("Введи назву підрозділу.")
            else:
                execute_query("""
                    INSERT INTO departments
                        (name, type, parent_id)
                    VALUES (?, ?, ?)
                """, (
                    name.strip(),
                    "Підрозділ",
                    parent_options[parent_label]
                ))

                st.success("Підрозділ успішно додано!")
                st.rerun()


# Сторінка 3. Ресурси
elif page == "⚡ Ресурси":
    st.title("⚡ Енергетичні ресурси")

    st.write(
        "Довідник ресурсів, що використовуються "
        "для енергетичного моніторингу."
    )

    rows = fetch_data("""
        SELECT id, name, unit
        FROM resources
        ORDER BY id
    """)

    table_data = [
        {
            "ID": row[0],
            "Ресурс": row[1],
            "Одиниця вимірювання": row[2]
        }
        for row in rows
    ]

    st.subheader("Список ресурсів")

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True
    )

    st.divider()
    st.subheader("➕ Додати ресурс")

    with st.form("add_resource"):
        resource_name = st.text_input(
            "Назва ресурсу",
            placeholder="Наприклад, Природний газ"
        )

        unit = st.text_input(
            "Одиниця вимірювання",
            placeholder="Наприклад, тис. м³"
        )

        submitted = st.form_submit_button(
            "Додати ресурс",
            type="primary"
        )

        if submitted:
            if not resource_name.strip() or not unit.strip():
                st.error("Заповни всі поля.")
            else:
                try:
                    execute_query("""
                        INSERT INTO resources (name, unit)
                        VALUES (?, ?)
                    """, (
                        resource_name.strip(),
                        unit.strip()
                    ))

                    st.success("Ресурс додано!")
                    st.rerun()

                except sqlite3.IntegrityError:
                    st.error("Такий ресурс уже існує.")


elif page == "🔗 Енергетичний паспорт":
    st.title("🔗 Енергетичний паспорт")

    st.write(
        "Визначення ресурсів, які використовуються "
        "структурними підрозділами кінотеатру."
    )

    departments = fetch_data("""
        SELECT id, name
        FROM departments
        WHERE type = 'Підрозділ'
        ORDER BY id
    """)

    resources = fetch_data("""
        SELECT id, name, unit
        FROM resources
        ORDER BY id
    """)

    department_options = {
        name: department_id
        for department_id, name in departments
    }

    resource_options = {
        f"{name} ({unit})": resource_id
        for resource_id, name, unit in resources
    }

    st.subheader("Призначення ресурсів")

    if not departments or not resources:
        st.warning(
            "Спочатку додайте підрозділи та ресурси."
        )
    else:
        with st.form("resource_assignment"):
            department_name = st.selectbox(
                "Оберіть підрозділ",
                list(department_options.keys())
            )

            selected_resources = st.multiselect(
                "Які ресурси використовує підрозділ?",
                list(resource_options.keys())
            )

            submitted = st.form_submit_button(
                "Зберегти ресурси",
                type="primary"
            )

            if submitted:
                department_id = department_options[
                    department_name
                ]

                conn = get_connection()

                try:
                    for resource_name in selected_resources:
                        resource_id = resource_options[
                            resource_name
                        ]

                        conn.execute("""
                            INSERT OR IGNORE INTO
                                department_resources
                                (department_id, resource_id)
                            VALUES (?, ?)
                        """, (department_id, resource_id))

                    conn.commit()
                    st.success("Ресурси успішно збережено!")
                finally:
                    conn.close()

    st.divider()

    st.subheader("Енергетичний паспорт підприємства")

    rows = fetch_data("""
        SELECT
            d.name,
            r.name,
            r.unit
        FROM department_resources dr
        JOIN departments d
            ON dr.department_id = d.id
        JOIN resources r
            ON dr.resource_id = r.id
        ORDER BY d.id, r.id
    """)

    if rows:
        table_data = [
            {
                "Підрозділ": row[0],
                "Ресурс": row[1],
                "Одиниця вимірювання": row[2]
            }
            for row in rows
        ]

        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True
        )

        df = pd.DataFrame(report)

        st.download_button(
            label="📥 Завантажити таблицю (CSV)",
            data=df.to_csv(
                index=False,
                sep=";"
            ).encode("utf-8-sig"),
            file_name=f"energy_report_{selected_year}.csv",
            mime="text/csv"
        )

    else:
        st.info("Ресурси ще не призначені.")


# Сторінка 5. Тарифи
elif page == "💰 Тарифи":
    st.title("💰 Управління тарифами")

    st.write(
        "Облік вартості енергоресурсів "
        "з урахуванням періодів дії тарифів."
    )

    st.info(
        "У лабораторній використовуються модельні тарифи. "
        "Вони не є фактичними тарифами кінотеатру."
    )

    resources = fetch_data("""
        SELECT id, name, unit
        FROM resources
        ORDER BY id
    """)

    departments = fetch_data("""
        SELECT id, name
        FROM departments
        WHERE type = 'Підрозділ'
        ORDER BY id
    """)

    resource_options = {
        f"{name} ({unit})": resource_id
        for resource_id, name, unit in resources
    }

    department_options = {
        "Загальний тариф": None
    }

    for department_id, name in departments:
        department_options[
            f"{department_id} — {name}"
        ] = department_id

    # Генерація початкових модельних тарифів
    st.subheader("⚙️ Автоматичне заповнення")

    st.write(
        "Можна автоматично сформувати навчальні "
        "тарифи за 2016–2025 роки."
    )

    sample_prices = {
        "Електроенергія": [2.20, 3.80, 6.20],
        "Теплова енергія": [1100, 1650, 2600],
        "Холодна вода": [12000, 18000, 30000],
        "Водовідведення": [10000, 16000, 26000],
        "Тверді побутові відходи": [900, 1400, 2200]
    }

    periods = [
        ("2016-01-01", "2019-12-31"),
        ("2020-01-01", "2022-12-31"),
        ("2023-01-01", "2025-12-31")
    ]

    if st.button("⚡ Згенерувати модельні тарифи"):
        conn = get_connection()

        try:
            added = 0

            for resource_id, name, unit in resources:
                if name not in sample_prices:
                    continue

                # Не перезаписуємо вже наявні тарифи
                existing = conn.execute("""
                    SELECT COUNT(*)
                    FROM tariffs
                    WHERE resource_id = ?
                      AND department_id IS NULL
                """, (resource_id,)).fetchone()[0]

                if existing > 0:
                    continue

                prices = sample_prices[name]

                for i, (start, end) in enumerate(periods):
                    conn.execute("""
                        INSERT INTO tariffs (
                            resource_id,
                            department_id,
                            price,
                            start_date,
                            end_date
                        )
                        VALUES (?, NULL, ?, ?, ?)
                    """, (
                        resource_id,
                        prices[i],
                        start,
                        end
                    ))

                    added += 1

            conn.commit()

            st.success(
                f"Додано {added} тарифних записів!"
            )

        finally:
            conn.close()

    st.divider()

    # Ручне додавання тарифів
    st.subheader("➕ Додати тариф вручну")

    with st.form("add_tariff"):
        selected_resource = st.selectbox(
            "Оберіть ресурс",
            list(resource_options.keys())
        )

        selected_department = st.selectbox(
            "Для якого підрозділу?",
            list(department_options.keys())
        )

        price = st.number_input(
            "Вартість одиниці ресурсу, грн",
            min_value=0.0,
            value=1.0,
            step=0.1,
            format="%.2f"
        )

        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "Дата початку дії",
                value=date(2016, 1, 1)
            )

        with col2:
            end_date = st.date_input(
                "Дата завершення дії",
                value=date(2019, 12, 31)
            )

        submitted = st.form_submit_button(
            "Зберегти тариф",
            type="primary"
        )

        if submitted:
            resource_id = resource_options[
                selected_resource
            ]

            department_id = department_options[
                selected_department
            ]

            start = start_date.isoformat()
            end = end_date.isoformat()

            if end_date < start_date:
                st.error(
                    "Дата завершення не може бути "
                    "ранішою за дату початку."
                )
            else:
                conn = get_connection()

                try:
                    # Перевірка перетину тарифних періодів
                    overlap = conn.execute("""
                        SELECT COUNT(*)
                        FROM tariffs
                        WHERE resource_id = ?
                          AND department_id IS ?
                          AND start_date <= ?
                          AND COALESCE(
                              end_date, '9999-12-31'
                          ) >= ?
                    """, (
                        resource_id,
                        department_id,
                        end,
                        start
                    )).fetchone()[0]

                    if overlap:
                        st.error(
                            "Для цього ресурсу та підрозділу "
                            "вже існує тариф у вибраному періоді."
                        )
                    else:
                        conn.execute("""
                            INSERT INTO tariffs (
                                resource_id,
                                department_id,
                                price,
                                start_date,
                                end_date
                            )
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            resource_id,
                            department_id,
                            price,
                            start,
                            end
                        ))

                        conn.commit()
                        st.success("Тариф успішно додано!")

                finally:
                    conn.close()

    st.divider()

    # Таблиця тарифів
    st.subheader("📋 Історія тарифів")

    tariffs = fetch_data("""
        SELECT
            t.id,
            r.name,
            COALESCE(d.name, 'Загальний'),
            t.price,
            r.unit,
            t.start_date,
            t.end_date
        FROM tariffs t
        JOIN resources r
            ON t.resource_id = r.id
        LEFT JOIN departments d
            ON t.department_id = d.id
        ORDER BY r.id, t.start_date
    """)

    if tariffs:
        table_data = [
            {
                "ID": row[0],
                "Ресурс": row[1],
                "Підрозділ": row[2],
                "Тариф, грн": row[3],
                "За одиницю": row[4],
                "Початок дії": row[5],
                "Кінець дії": row[6]
            }
            for row in tariffs
        ]

        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True
        )

        st.metric(
            "Кількість тарифних записів",
            len(tariffs)
        )
    else:
        st.warning("Тарифи ще не додані.")

# Сторінка 6. Споживання ресурсів
elif page == "📊 Споживання ресурсів":
    st.title("📊 Моніторинг енергоспоживання")

    st.write(
        "Автоматична генерація, перегляд та редагування "
        "первинних даних енергоспоживання."
    )

    st.info(
        "Дані є модельними та використовуються "
        "виключно для навчальної лабораторної роботи."
    )

    # Генерація
    st.subheader("⚙️ Генерація даних за 10 років")

    if st.button(
        "Згенерувати дані за 2016–2025 роки",
        type="primary"
    ):
        added, production_added = generate_consumption()

        st.success(
            f"Створено {added} записів споживання "
            f"та {production_added} записів виробництва послуг."
        )

    st.divider()

    departments = fetch_data("""
        SELECT id, name
        FROM departments
        WHERE type = 'Підрозділ'
        ORDER BY id
    """)

    department_options = {
        "Усе підприємство": None
    }

    for dept_id, name in departments:
        department_options[name] = dept_id

    # Зведені таблиці
    st.subheader("📋 Зведена таблиця споживання")

    col1, col2 = st.columns(2)

    with col1:
        selected_department = st.selectbox(
            "Підрозділ",
            list(department_options.keys()),
            key="report_department"
        )

    with col2:
        selected_year = st.selectbox(
            "Рік",
            YEARS[::-1],
            key="report_year"
        )

    report, missing_tariffs = build_report(
        selected_year,
        department_options[selected_department]
    )

    if report:
        st.dataframe(
            report,
            hide_index=True,
            use_container_width=True
        )

        if missing_tariffs:
            st.warning(
                "Для деяких місяців не знайдено тарифів. "
                "Відповідні витрати в таблиці неповні."
            )

        total_cost = sum(
            row["Усього за рік"]
            for row in report
            if row["Показник"].startswith("Витрати:")
        )

        st.metric(
            "Загальні витрати на ресурси за рік",
            f"{total_cost:,.2f} грн"
        )

    else:
        st.warning(
            "Даних немає. Спочатку виконайте генерацію."
        )

    st.divider()



    # Редагування споживання
    st.subheader("✏️ Ручне редагування споживання")

    edit_department = st.selectbox(
        "Підрозділ",
        [name for name in department_options
         if department_options[name] is not None],
        key="edit_department"
    )

    edit_dept_id = department_options[edit_department]

    assigned_resources = fetch_data("""
        SELECT r.id, r.name, r.unit
        FROM department_resources dr
        JOIN resources r ON r.id = dr.resource_id
        WHERE dr.department_id = ?
        ORDER BY r.id
    """, (edit_dept_id,))

    resource_options = {
        f"{name} ({unit})": res_id
        for res_id, name, unit in assigned_resources
    }

    if resource_options:
        selected_resource = st.selectbox(
            "Ресурс",
            list(resource_options.keys()),
            key="edit_resource"
        )

        col1, col2 = st.columns(2)

        with col1:
            edit_year = st.selectbox(
                "Рік", YEARS[::-1],
                key="edit_year"
            )

        with col2:
            edit_month = st.selectbox(
                "Місяць", MONTHS,
                key="edit_month"
            )

        resource_id = resource_options[selected_resource]
        month_number = MONTHS.index(edit_month) + 1

        # Отримуємо поточне значення з БД
        existing = fetch_data("""
            SELECT amount
            FROM consumption
            WHERE department_id = ?
              AND resource_id = ?
              AND year = ?
              AND month = ?
        """, (
            edit_dept_id,
            resource_id,
            edit_year,
            month_number
        ))

        current_amount = (
            float(existing[0][0]) if existing else 0.0
        )

        st.caption(
            f"Поточне значення: {current_amount:.4f}"
        )

        with st.form(
            f"edit_{edit_dept_id}_{resource_id}_"
            f"{edit_year}_{month_number}"
        ):
            new_amount = st.number_input(
                "Нове значення споживання",
                min_value=0.0,
                value=current_amount,
                format="%.4f"
            )

            if st.form_submit_button(
                "Зберегти зміни",
                type="primary"
            ):
                execute_query("""
                    INSERT INTO consumption (
                        department_id,
                        resource_id,
                        year,
                        month,
                        amount
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (
                        department_id,
                        resource_id,
                        year,
                        month
                    )
                    DO UPDATE
                    SET amount = excluded.amount
                """, (
                    edit_dept_id,
                    resource_id,
                    edit_year,
                    month_number,
                    new_amount
                ))

                st.success("Значення оновлено!")
                st.rerun()
    else:
        st.info("Цьому підрозділу не призначено ресурсів.")


    st.divider()

    # Редагування виробництва послуг
    st.subheader("🎟️ Обсяги реалізації послуг")

    with st.form("edit_production"):
        production_department = st.selectbox(
            "Підрозділ",
            [name for name in department_options
             if department_options[name] is not None],
            key="production_department"
        )

        prod_col1, prod_col2 = st.columns(2)

        with prod_col1:
            production_year = st.selectbox(
                "Рік",
                YEARS[::-1],
                key="production_year"
            )

        with prod_col2:
            production_month = st.selectbox(
                "Місяць",
                MONTHS,
                key="production_month"
            )

        revenue = st.number_input(
            "Обсяг реалізованих послуг, грн",
            min_value=0.0,
            value=0.0,
            step=1000.0
        )

        if st.form_submit_button("Зберегти обсяг послуг"):
            execute_query("""
                INSERT INTO production (
                    department_id, year, month, revenue
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(department_id, year, month)
                DO UPDATE SET revenue = excluded.revenue
            """, (
                department_options[production_department],
                production_year,
                MONTHS.index(production_month) + 1,
                revenue
            ))

            st.success("Дані про послуги збережено!")
            st.rerun()

