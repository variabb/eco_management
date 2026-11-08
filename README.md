Python / Streamlit / SQLite. Лабораторні роботи № 1–3.

## Запуск

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Перевірка

```bash
python -m unittest -q test_lab3
python test_lab2.py
```

## Файли

- `app.py` - інтерфейс застосунку.
- `database.py`, `energy.db` - база даних та її структура.
- `energy_data.py`-— споживання, тарифи, агрегування.
- `lab2_data.py`, `indicators.py`, `lab2_page.py` - енергетичні індикатори.
- `lab3_charts.py`, `lab3_page.py`, `lab3_exports.py` - графіки, редагування, експорт.
- `test_lab2.py`, `test_lab3.py`-— перевірка розрахунків.

Показники споживання, тарифи та частину умов аналізу сформовано програмно. Вони не є даними фактичних лічильників кінотеатру.
