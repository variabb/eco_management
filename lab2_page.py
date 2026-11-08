


import pandas as pd
import streamlit as st
from database import get_connection
from energy_data import MONTHS
from indicators import month_rows, year_statistics, monthly_indicators, annual_kpi, year_comparison
from lab2_data import populate_lab2_model, refresh_emissions


def _round_table(items, columns):
    frame = pd.DataFrame(items)
    if frame.empty:
        return frame
    frame = frame[columns]
    for key in frame:
        if pd.api.types.is_float_dtype(frame[key]):
            frame[key] = frame[key].round(3)
    return frame


def _download_csv(data, filename):
    if not data.empty:
        st.download_button('📥 Завантажити CSV',
            data=data.to_csv(index=False, sep=';').encode('utf-8-sig'),
            file_name=filename, mime='text/csv')


def show_lab2_page():
    st.title('📐 Енергетичні індикатори — лабораторна №2')
    st.caption('Кінотеатр «Планета Кіно — Блокбастер» · 2016–2025')

    db = get_connection()
    try:
        depts = db.execute("SELECT id,name FROM departments WHERE type='Підрозділ' ORDER BY id").fetchall()
        resources = db.execute('SELECT id,name,unit FROM resources ORDER BY id').fetchall()
    finally:
        db.close()
    if not depts:
        st.warning('Немає структурних підрозділів. Спочатку заповніть лабораторну №1.')
        return

    a,b,c=st.columns([1,2,2])
    with a:
        year=st.selectbox('Рік',list(range(2025,2015,-1)),key='lab2_year')
    with b:
        dept_name=st.selectbox('Зона обліку',['Усе підприємство']+[n for _,n in depts],key='lab2_dept')
    with c:
        selected_r=st.selectbox('Ресурс для аналізу',['Усі ресурси']+[n for _,n,_ in resources],key='lab2_res')
    dept_id=next((i for i,n in depts if n==dept_name),None)
    rid=next((i for i,n,_ in resources if n==selected_r),None)

    annual=annual_kpi(year,dept_id)
    k1,k2,k3,k4=st.columns(4)
    k1.metric('Енергія, кВт·год екв.',f"{annual['energy_eq_kwh']:,.0f}")
    k2.metric('Частка енерговитрат',f"{annual['energy_share_percent'] or 0:.1f}%")
    k3.metric('Частка власної генерації',f"{annual['generation_share_percent'] or 0:.1f}%")
    k4.metric('Розрахункові викиди CO₂',f"{annual['co2_kg']/1000:,.1f} т")

    tab1,tab2,tab3,tab4,tab5 = st.tabs([
        '📅 Середньодобові', '📊 Макс / мін', '⚡ Енергоефективність',
        '🌿 Вплив на довкілля', '🛠️ Вхідні дані'])

    with tab1:
        st.subheader('Середньодобове споживання ресурсів')
        st.write('Показник = помісячний обсяг / кількість відпрацьованих днів. Нульові місяці позначені як відсутність середньодобового значення.')
        mr=month_rows(year,dept_id,rid)
        df=_round_table([{
            'Підрозділ':x['department'], 'Ресурс':x['resource'],
            'Місяць':MONTHS[x['month']-1], 'Днів роботи':x['working_days'],
            'Обсяг':x['amount'], 'Середньодобове':x['daily'],
            'Витрати, грн':x['cost']
        } for x in mr],['Підрозділ','Ресурс','Місяць','Днів роботи','Обсяг','Середньодобове','Витрати, грн'])
        st.dataframe(df,hide_index=True,use_container_width=True,height=440)
        _download_csv(df,f'lab2_daily_{year}.csv')

    with tab2:
        st.subheader('Нерівномірність та екстремальні значення')
        stats=year_statistics(year,dept_id)
        if rid is not None:
            stats=[x for x in stats if x['resource']==selected_r]
        summary=_round_table([{
            'Підрозділ':x['department'], 'Ресурс':x['resource'],
            'Робочих місяців':x['active_months'],
            'Середньодобове за рік':x['mean_daily'],
            'Мінімум':x['min_daily'],
            'Місяць min':MONTHS[x['min_month']-1] if x['min_month'] else '—',
            'Максимум':x['max_daily'],
            'Місяць max':MONTHS[x['max_month']-1] if x['max_month'] else '—',
            'Коеф. нерівномірності':x['nonuniformity'],
            'Місяці без споживання':', '.join(MONTHS[m-1] for m in x['missing_months']) or '—'
        } for x in stats],['Підрозділ','Ресурс','Робочих місяців','Середньодобове за рік',
            'Мінімум','Місяць min','Максимум','Місяць max','Коеф. нерівномірності','Місяці без споживання'])
        st.dataframe(summary,hide_index=True,use_container_width=True,height=440)
        _download_csv(summary,f'lab2_nonuniformity_{year}.csv')
        st.caption('Середньодобове за рік — середнє значення за активні місяці; це не річна сума споживання.')

    with tab3:
        st.subheader('Енергетичні індикатори')
        rows=monthly_indicators(year,dept_id)
        table=_round_table([{
            'Підрозділ':x['department'], 'Місяць':MONTHS[x['month']-1],
            'Площа, м²':x['area_m2'], 'Градусо-дні':x['degree_days'],
            'Ел., кВт·год/м²':x['electricity_specific_kwh_m2'],
            'Тепло, Гкал/м²':x['heat_specific_gcal_m2'],
            'Освітлення*, кВт·год/м²':x['lighting_specific_kwh_m2'],
            'Кондиціювання*, кВт·год/м²':x['cooling_specific_kwh_m2'],
            'Енерговитрати, грн':x['energy_cost_grn'],
            'Частка енерговитрат, %':x['energy_share_percent'],
            'Власна генерація, кВт·год':x['generation_kwh'],
            'Частка генерації, %':x['generation_share_percent'],
            'Енергоємність, кВт·год/тис. грн':x['energy_intensity_kwh_per_1000grn']
        } for x in rows],['Підрозділ','Місяць','Площа, м²','Градусо-дні','Ел., кВт·год/м²',
            'Тепло, Гкал/м²','Освітлення*, кВт·год/м²','Кондиціювання*, кВт·год/м²','Енерговитрати, грн','Частка енерговитрат, %',
            'Власна генерація, кВт·год','Частка генерації, %','Енергоємність, кВт·год/тис. грн'])
        st.dataframe(table,hide_index=True,use_container_width=True,height=410)
        _download_csv(table,f'lab2_kpi_{year}.csv')
        st.warning('Показники освітлення й кондиціювання розраховані за розподілом загального споживання електроенергії.')
        comparison=year_comparison(2016,2025,dept_id)
        cmp=pd.DataFrame(comparison)[['year','energy_eq_kwh','energy_share_percent','generation_share_percent','co2_kg']]
        cmp.columns=['Рік','Енергоспоживання, кВт·год екв.','Енерговитрати, %','Генерація, %','CO₂, кг']
        st.subheader('Динаміка показників за 10 років')
        st.line_chart(cmp.set_index('Рік')[['Енергоспоживання, кВт·год екв.']])

    with tab4:
        st.subheader('Викиди CO₂ і питома екологічна інтенсивність')
        st.markdown('**Коефіцієнти розрахунку:** 0,40 кг CO₂/кВт·год електроенергії; 230 кг CO₂/Гкал теплової енергії.')
        records=monthly_indicators(year,dept_id)
        pollution=_round_table([{'Підрозділ':r['department'],'Місяць':MONTHS[r['month']-1],
               'CO₂, кг':r['co2_kg'],'Виручка, грн':r['revenue_grn'],
               'CO₂, кг/тис. грн послуг':r['co2_kg_per_1000grn']}
               for r in records],['Підрозділ','Місяць','CO₂, кг','Виручка, грн','CO₂, кг/тис. грн послуг'])
        st.dataframe(pollution,hide_index=True,use_container_width=True,height=400)
        _download_csv(pollution,f'lab2_co2_{year}.csv')
        if annual['revenue_grn']:
            st.metric('Питомі викиди на 1000 грн послуг',
                      f"{annual['co2_kg_per_1000grn']:.3f} кг")
        st.caption('Виручку внесено для «Кінозалів»; для інших підрозділів цей питомий показник не обчислюється.')

    with tab5:
        st.subheader('Вихідні дані')
        st.write('Можна змінити площу приміщення, робочі дні, температуру, загальні витрати та власну генерацію. Зміни зберігаються в SQLite.')
        selected_id=st.selectbox('Підрозділ для редагування',options=[i for i,_ in depts],format_func=lambda did:next(n for i,n in depts if i==did),key='lab2_edit_dept')
        month=st.selectbox('Місяць для редагування',range(1,13),format_func=lambda m:MONTHS[m-1],key='lab2_edit_month')
        conn=get_connection()
        try:
            area=conn.execute('SELECT heated_area FROM departments WHERE id=?',(selected_id,)).fetchone()[0]
            cond=conn.execute('''SELECT working_days,outdoor_temp,indoor_temp FROM monthly_conditions
               WHERE department_id=? AND year=? AND month=?''',(selected_id,year,month)).fetchone()
            fin=conn.execute('''SELECT total_expenses FROM monthly_finances
               WHERE department_id=? AND year=? AND month=?''',(selected_id,year,month)).fetchone()
            electricity_id=conn.execute("SELECT id FROM resources WHERE name='Електроенергія'").fetchone()[0]
            gen=conn.execute('''SELECT amount FROM monthly_generation
               WHERE department_id=? AND year=? AND month=? AND resource_id=?''',(selected_id,year,month,electricity_id)).fetchone()
        finally:conn.close()
        if not cond:
            st.error('Немає даних умов за обраний місяць.');return
        with st.form(f'lab2_edit_{selected_id}_{year}_{month}'):
            p_area=st.number_input('Опалювальна площа, м²',min_value=0.0,value=float(area or 0),step=10.0)
            workdays=st.number_input('Днів роботи',min_value=0,max_value=31,value=int(cond[0]))
            outdoor=st.number_input('Середня температура зовні, °C',value=float(cond[1]),step=0.5)
            indoor=st.number_input('Середня температура всередині, °C',value=float(cond[2]),step=0.5)
            exp=st.number_input('Загальні витрати, грн',min_value=0.0,value=float(fin[0] if fin else 0),step=100.0)
            generation=st.number_input('Власна генерація електроенергії, кВт·год',min_value=0.0,value=float(gen[0] if gen else 0),step=100.0)
            save=st.form_submit_button('💾 Зберегти дані',type='primary')
            if save:
                conn=get_connection()
                try:
                    conn.execute('UPDATE departments SET heated_area=? WHERE id=?',(p_area,selected_id))
                    conn.execute('''UPDATE monthly_conditions SET working_days=?,outdoor_temp=?,indoor_temp=?
                         WHERE department_id=? AND year=? AND month=?''',(workdays,outdoor,indoor,selected_id,year,month))
                    conn.execute('''INSERT INTO monthly_finances(department_id,year,month,total_expenses)
                         VALUES(?,?,?,?) ON CONFLICT(department_id,year,month) DO UPDATE SET total_expenses=excluded.total_expenses''',(selected_id,year,month,exp))
                    conn.execute('''INSERT INTO monthly_generation(department_id,resource_id,year,month,amount)
                         VALUES(?,?,?,?,?) ON CONFLICT(department_id,resource_id,year,month) DO UPDATE SET amount=excluded.amount''',(selected_id,electricity_id,year,month,generation))
                    conn.commit()
                finally:conn.close()
                st.success('Дані збережено.');st.rerun()
        if st.button('🔄 Перерахувати збережені викиди CO₂'):
            refresh_emissions()
            st.success('Викиди у базі оновлено відповідно до поточного споживання.')
        st.caption('Показники власної генерації за 2023–2025 рр. обчислено для сценарію СЕС.')
