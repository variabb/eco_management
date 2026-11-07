"""Експорт розрахунків ЛР №2 у CSV без додаткових бібліотек.
Запуск: python export_lab2.py
"""
import csv
from pathlib import Path
from indicators import year_comparison, year_statistics, monthly_indicators, month_rows
from lab2_data import populate_lab2_model

OUT=Path(__file__).resolve().parent / 'exports'


def save(name,rows):
    rows=list(rows)
    if not rows:return
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as fp:
        writer=csv.DictWriter(fp,fieldnames=list(rows[0]),delimiter=';')
        writer.writeheader()
        for row in rows:writer.writerow(row)
    print(f'Створено: exports/{name} ({len(rows)} рядків)')


def main():
    OUT.mkdir(exist_ok=True)
    populate_lab2_model()
    save('kpi_2016_2025.csv',year_comparison())
    save('kpi_2025_monthly.csv',monthly_indicators(2025))
    save('daily_2025.csv',month_rows(2025))
    save('nonuniformity_2025.csv',year_statistics(2025))
    save('nonuniformity_2020.csv',year_statistics(2020))
    from database import get_connection
    c=get_connection()
    try:
        depts=[d for d,n in c.execute("SELECT id,name FROM departments WHERE type='Підрозділ'")]
    finally:c.close()
    save('departments_kpi_2016_2025.csv',[annual for d in depts for annual in year_comparison(2016,2025,d)])

if __name__=='__main__':main()
