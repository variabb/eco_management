"""Автоматичні перевірки лабораторної №2 (запуск: python test_lab2.py)."""
import math
from database import get_connection, init_db,seed_data
from lab2_data import populate_lab2_model, CO2_ELECTRIC_KG_PER_KWH, CO2_HEAT_KG_PER_GCAL
from indicators import month_rows, year_statistics, monthly_indicators, annual_kpi, year_comparison


def approx(a,b):
    assert math.isclose(a,b,rel_tol=1e-8,abs_tol=0.001),(a,b)


def run_checks():
    init_db();seed_data();populate_lab2_model()
    conn=get_connection()
    try:
        expected={'departments':5,'resources':5,'department_resources':17,'tariffs':15,
          'consumption':2040,'production':120,'monthly_conditions':480,
          'monthly_finances':480,'monthly_generation':120,'monthly_emissions':480,'monthly_electricity_breakdown':480}
        for table,num in expected.items():
            actual=conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            assert actual==num, (table,actual,num)
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
        years=conn.execute('SELECT MIN(year),MAX(year),COUNT(DISTINCT year) FROM consumption').fetchone()
        assert years==(2016,2025,10),years
        c=conn.execute('''SELECT SUM(amount) FROM consumption c JOIN resources r ON r.id=c.resource_id
                WHERE c.year=2025 AND r.name='Електроенергія' ''').fetchone()[0]
        approx(annual_kpi(2025)['electricity_kwh'],c)
        kpi=annual_kpi(2025)
        approx(kpi['energy_share_percent'], kpi['energy_cost_grn']/kpi['total_expenses_grn']*100)
        approx(kpi['co2_kg'], kpi['electricity_kwh']*CO2_ELECTRIC_KG_PER_KWH + kpi['heat_gcal']*CO2_HEAT_KG_PER_GCAL)
        april=monthly_indicators(2020)
        assert all(r['days']==0 and r['electricity_kwh']==0 for r in april if r['month'] in (4,5))
        assert all(r['generation_kwh']==0 for r in monthly_indicators(2022))
        assert sum(r['generation_kwh'] for r in monthly_indicators(2025))>0
        assert len(year_statistics(2025))==17
        assert all(r['lighting_specific_kwh_m2'] is not None for r in monthly_indicators(2025))
        assert len(month_rows(2025))==204
        stats_2020=year_statistics(2020)
        assert all(s['active_months']==10 for s in stats_2020)
        assert all(s['min_daily']>0 and s['nonuniformity']>=1 for s in stats_2020)
        assert len(year_comparison())==10
        assert math.isclose(annual_kpi(2025,2)['revenue_grn'], kpi['revenue_grn'])
        assert annual_kpi(2025,3)['revenue_grn']==0
        assert all(r['energy_intensity_kwh_per_1000grn'] is None for r in monthly_indicators(2025,3))
        # Повторне наповнення не збільшує кількість записів
        populate_lab2_model()
        for table,num in expected.items():
            assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]==num
        print('ЛР №2: УСІ ПЕРЕВІРКИ ПРОЙДЕНО')
        print('Таблиці:','; '.join(f'{t}={n}' for t,n in expected.items()))
        print('Роки: 2016–2025. Кількість рядків за 2025 рік: 204.')
        print('2020: квітень і травень виключаються з середньодобових мінімумів та середніх.')
        for year in (2016,2020,2023,2025):
            d=annual_kpi(year)
            print(f"{year}: енергія {d['energy_eq_kwh']:,.2f} кВт·год екв.; "
                  f"енерговитрати {d['energy_cost_grn']:,.2f} грн; "
                  f"частка {d['energy_share_percent']:.2f}%; "
                  f"генерація {d['generation_share_percent']:.2f}%; CO₂ {d['co2_kg']:,.2f} кг")
    finally:
        conn.close()

if __name__=='__main__':run_checks()
