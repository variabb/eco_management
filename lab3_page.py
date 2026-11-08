
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from lab3_charts import (
    YEARS, INDICATOR_LABELS, resources, departments, init_lab3_db, save_note, get_note,
    monthly_consumption, yearly_consumption, heating_vs_weather, monthly_cost, yearly_cost,
    pie_cost, indicator_yearly, plot_dataframe, chart_png_bytes, all_notes,
)
from lab3_exports import export_word, export_excel


def show_lab3_page():
    init_lab3_db()
    st.title('📈 Графічний аналіз (ЛР №3)')
    st.caption('«Планета Кіно - Блокбастер» · лабораторна робота №3')


    deps=departments();ress=resources()
    dept_options={'Усе підприємство': None, **{n:d for d,n in deps}}
    res_options={f'{n} ({u})':(r,n,u) for r,n,u in ress}

    def _editor_and_note(chart_key, typ, title, description, df, kind, ylabel, period, did=None, rid=None):
        if df.empty:
            st.warning('Для заданого набору параметрів даних немає.');return
        st.subheader(title)
        st.caption(description)
        with st.expander('✏️ Режим експерта — редагування/вилучення точок (тільки в графіку)',expanded=False):
            col_a,col_b=st.columns([1,3])
            with col_a:
                reset=st.button('↩️ Відновити значення',key=f'reset:{chart_key}')
            editor_key=f'edit:{chart_key}'
            if reset:
                st.session_state.pop(editor_key,None)
                st.session_state.get('lab3_saved',{}).pop(chart_key,None)
                st.rerun()
            edited=st.data_editor(df, key=editor_key, hide_index=True, use_container_width=True,
                                  num_rows='fixed',disabled=['Період','Серія'],
                                  column_config={
                                   'Значення':st.column_config.NumberColumn('Значення',format='%.2f',min_value=0.0),
                                   'Виключити':st.column_config.CheckboxColumn('Виключити точку')})
            st.caption('Вилучена або нульова точка перетворюється на розрив; ')
        if editor_key not in st.session_state:
            edited=df.copy()
        edited=edited.copy()
        edited['Значення']=pd.to_numeric(edited['Значення'],errors='coerce')
        fig=plot_dataframe(edited,title,kind,ylabel,caption='Нульові значення відображаються розривами')
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        st.download_button('📥 Зберегти графік (PNG)',chart_png_bytes(edited,title,kind,ylabel),
                           file_name=f'{chart_key.replace(":","_")}.png',mime='image/png',key='png:'+chart_key)
        comment_key='note:'+chart_key
        if comment_key not in st.session_state:
            st.session_state[comment_key]=get_note(chart_key)
        st.text_area('Експертний коментар / оцінка результату',height=88,key=comment_key,
                     placeholder='Опиши тенденцію, максимум/мінімум, аномалії, можливі причини та висновок…')
        if st.button('💾 Зберегти коментар у SQLite',key='save:'+chart_key):
            text=st.session_state[comment_key].strip()
            if not text:st.warning('Спочатку введи експертний висновок.')
            else:
                save_note(chart_key,typ,title,period,did,rid,text)
                st.success('Експертний коментар записано до таблиці chart_notes!')
        if 'lab3_saved' not in st.session_state: st.session_state['lab3_saved']={}
        st.session_state['lab3_saved'][chart_key]=dict(key=chart_key,type=typ,title=title,
            description=description,df=edited,kind=kind,ylabel=ylabel,
            period=period,department_id=did,resource_id=rid,
            comment=st.session_state[comment_key].strip())

    tabs=st.tabs(['📉 Обсяги споживання','🌡️ Енергія та погода',
                 '💰 Грошові витрати','🥧 Енергобаланс','📐 Індикатори','🗂️ Експорт і коментарі'])

    with tabs[0]:
        c1,c2,c3,c4=st.columns([1,1.5,1.5,1])
        with c1: period_type=st.radio('Періодичність',['Помісячно','За роками'],horizontal=True,key='v_period')
        with c2: year=st.selectbox('Рік',YEARS[::-1],key='v_year',disabled=period_type=='За роками')
        with c3: res_label=st.selectbox('Ресурс',list(res_options),key='v_resource')
        with c4: dep_label=st.selectbox('Підрозділ',list(dept_options),key='v_dep')
        rid,rname,unit=res_options[res_label];did=dept_options[dep_label]
        if period_type=='Помісячно':
            frame=monthly_consumption(year,rid,did);term=str(year);ptype='month'
        else:
            frame=yearly_consumption(rid,did);term='2016–2025';ptype='year'
        title=f'Споживання «{rname}» · {dep_label} · {term}'
        _editor_and_note(f'volume:{ptype}:{year if ptype=="month" else "all"}:{rid}:{did}',
             'Обсяги споживання',title,
             'Динаміка споживання за ресурсом і структурним підрозділом.',
             frame,'line',unit,term,did,rid)
    with tabs[1]:
        c1,c2=st.columns(2)
        with c1: y_weather=st.selectbox('Рік',YEARS[::-1],key='w_year')
        with c2: d_weather=st.selectbox('Підрозділ',list(dept_options),key='w_dep')
        did=dept_options[d_weather]
        frame=heating_vs_weather(y_weather,did)
        title=f'Енергоспоживання і градусо-дні · {d_weather} · {y_weather}'
        _editor_and_note(f'weather:{y_weather}:{did}', 'Енергоспоживання',title,
             'Електроенергія й теплова енергія в кВт·год; порівняння з градусо-днями.',
             frame,'dual','кВт·год екв.',str(y_weather),did,None)
    with tabs[2]:
        c1,c2,c3,c4=st.columns(4)
        with c1: cost_period=st.radio('Періодичність',['За роками','Помісячно'],key='c_period')
        with c2: y_cost=st.selectbox('Рік',YEARS[::-1],key='c_year',disabled=cost_period=='За роками')
        with c3: b_cost=st.selectbox('Групування',['За ресурсами','За підрозділами'],key='c_group')
        with c4: d_cost=st.selectbox('Підрозділ',list(dept_options),key='c_dep')
        did=dept_options[d_cost];by='resource' if b_cost=='За ресурсами' else 'department'
        frame,miss=(yearly_cost(by,did) if cost_period=='За роками' else monthly_cost(y_cost,by,did))
        term='2016–2025' if cost_period=='За роками' else str(y_cost)
        title=f'Грошові витрати {b_cost.lower()} · {d_cost} · {term}'
        if miss:st.warning(f'Не всі тарифи знайдені: {len(miss)} записів не включено в суми.')
        _editor_and_note(f'cost:{"annual" if cost_period=="За роками" else y_cost}:{by}:{did}',
             'Грошові витрати',title,
             'Витрати = помісячний обсяг × тариф, чинний у відповідному місяці; порівняння за роками та місяцями.',
             frame,'bar' if cost_period=='За роками' else 'line','грн',term,did,None)
    with tabs[3]:
        c1,c2=st.columns(2)
        with c1:y_pie=st.selectbox('Рік',YEARS[::-1],key='p_year')
        with c2:d_pie=st.selectbox('Підрозділ',list(dept_options),key='p_dep')
        did=dept_options[d_pie];frame,miss=pie_cost(y_pie,did)
        title=f'Енергобаланс (структура витрат за ресурсами) · {d_pie} · {y_pie}'
        st.caption('У відсотках показано структуру витрат на ресурси. '
                   'Натуральні одиниці різних ресурсів між собою не додаються.')
        _editor_and_note(f'pie:{y_pie}:{did}', 'Енергобаланс',title,
            'Кругова діаграма вартості електроенергії, тепла, води, водовідведення й відходів.',
            frame,'pie','грн',str(y_pie),did,None)
    with tabs[4]:
        c1,c2=st.columns(2)
        with c1:ind_name=st.selectbox('Індикатор',list(INDICATOR_LABELS.values()),key='k_type')
        with c2:d_kpi=st.selectbox('Підрозділ',list(dept_options),key='k_dep')
        ind=next(key for key,label in INDICATOR_LABELS.items() if label==ind_name)
        did=dept_options[d_kpi];frame=indicator_yearly(ind,did)
        title=f'{ind_name} · {d_kpi} · 2016–2025'
        _editor_and_note(f'indicator:{ind}:{did}', 'Енергетичні індикатори',title,
            'Графічний аналіз індикаторів ЛР №2. Показники визначені лише за наявності необхідних даних.',
            frame,'line',ind_name,'2016–2025',did,None)
    with tabs[5]:
        st.subheader('📄 Звіт із графіками, таблицями та коментарями')
        st.write('Експорт містить усі графіки, відкриті на цій сторінці з поточними фільтрами, '
                 'включно з тимчасовими експертними корекціями. Ні Word, ні Excel не змінюють дані SQLite.')
        packs=list(st.session_state.get('lab3_saved',{}).values())
        st.metric('Графіків у поточному звіті',len(packs))
        if packs:
            if st.button('🧾 Підготувати Word і Excel зі всіма графіками', key='prepare_lab3'):
                with st.spinner('Формуємо звіти...'):
                    st.session_state['lab3_export_files'] = {
                        'word': export_word(packs),
                        'excel': export_excel(packs)
                    }
                st.success('Файли підготовлено. Завантаж їх кнопками нижче.')
            exported=st.session_state.get('lab3_export_files')
            if exported:
                st.download_button('📥 Експорт у Word (.docx)', data=exported['word'],
                    file_name='Planetakino_Expert_Charts_Lab3.docx',
                    mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    key='export_word')
                st.download_button('📥 Експорт у Excel (.xlsx)', data=exported['excel'],
                    file_name='Planetakino_Expert_Charts_Lab3.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='export_excel')
        st.subheader('💬 Збережені експертні оцінки з SQLite')
        notes=all_notes()
        if notes:
            st.dataframe(pd.DataFrame(notes,columns=['Ключ','Графік','Коментар','Оновлено']),
                         use_container_width=True,hide_index=True)
        else:
            st.info('Поки що коментарів немає. Заповни хоча б один висновок біля графіка.')
