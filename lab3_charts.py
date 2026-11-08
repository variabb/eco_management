


from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import io
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from database import get_connection
from energy_data import MONTHS
from lab2_data import GCAL_TO_KWH
from indicators import annual_kpi

YEARS = list(range(2016, 2026))
RESOURCE_NAMES = ['Електроенергія', 'Теплова енергія', 'Холодна вода',
                  'Водовідведення', 'Тверді побутові відходи']
MONTH_LABELS = [f'{m+1:02d} {name[:3]}' for m, name in enumerate(MONTHS)]


def init_lab3_db():

    conn = get_connection()
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS chart_notes (
            chart_key TEXT PRIMARY KEY,
            chart_type TEXT NOT NULL,
            chart_title TEXT NOT NULL,
            period TEXT NOT NULL,
            department_id INTEGER,
            resource_id INTEGER,
            comment TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        conn.commit()
    finally:
        conn.close()


def save_note(chart_key, chart_type, title, period, department_id, resource_id, comment):
    conn = get_connection()
    try:
        conn.execute('''INSERT INTO chart_notes
            (chart_key,chart_type,chart_title,period,department_id,resource_id,comment,updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(chart_key) DO UPDATE SET
            comment=excluded.comment, updated_at=excluded.updated_at,
            chart_title=excluded.chart_title
        ''', (chart_key, chart_type, title, str(period), department_id, resource_id,
              comment.strip(), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    finally:
        conn.close()


def get_note(chart_key):
    conn = get_connection()
    try:
        row = conn.execute('SELECT comment FROM chart_notes WHERE chart_key=?',(chart_key,)).fetchone()
        return row[0] if row else ''
    finally:
        conn.close()


def all_notes():
    conn = get_connection()
    try:
        return conn.execute('SELECT chart_key,chart_title,comment,updated_at FROM chart_notes ORDER BY updated_at DESC').fetchall()
    finally:
        conn.close()


def departments():
    conn = get_connection()
    try:
        return conn.execute("SELECT id,name FROM departments WHERE type='Підрозділ' ORDER BY id").fetchall()
    finally:
        conn.close()


def resources():
    conn=get_connection()
    try:
        return conn.execute('SELECT id,name,unit FROM resources ORDER BY id').fetchall()
    finally:
        conn.close()


def _df(data):
    return pd.DataFrame(data, columns=['Період','Серія','Значення','Виключити'])


def monthly_consumption(year, resource_id, department_id=None):
    conn = get_connection()
    try:
        q = '''SELECT c.month, d.name, SUM(c.amount)
               FROM consumption c JOIN departments d ON d.id=c.department_id
               WHERE c.year=? AND c.resource_id=?'''
        params=[year,resource_id]
        if department_id is not None:
            q += ' AND c.department_id=?'; params.append(department_id)
        q += ' GROUP BY c.month,d.id ORDER BY d.id,c.month'
        records=[]
        for month,name,value in conn.execute(q, params):
            records.append((MONTH_LABELS[month-1],name,float(value),False))
        return _df(records)
    finally:
        conn.close()


def yearly_consumption(resource_id, department_id=None):
    conn=get_connection()
    try:
        q='''SELECT c.year,d.name,SUM(c.amount) FROM consumption c
             JOIN departments d ON d.id=c.department_id WHERE c.resource_id=?'''
        args=[resource_id]
        if department_id is not None:
            q+=' AND c.department_id=?';args.append(department_id)
        q+=' GROUP BY c.year,d.id ORDER BY d.id,c.year'
        return _df([(str(y),name,float(v),False) for y,name,v in conn.execute(q,args)])
    finally:
        conn.close()


def heating_vs_weather(year, department_id=None):


    conn=get_connection()
    try:
        q='''SELECT c.month,c.department_id,c.working_days,c.outdoor_temp,
                    COALESCE((SELECT SUM(x.amount) FROM consumption x
                        JOIN resources r ON r.id=x.resource_id
                        WHERE x.department_id=c.department_id AND x.year=c.year
                        AND x.month=c.month AND r.name='Електроенергія'),0),
                    COALESCE((SELECT SUM(x.amount) FROM consumption x
                        JOIN resources r ON r.id=x.resource_id
                        WHERE x.department_id=c.department_id AND x.year=c.year
                        AND x.month=c.month AND r.name='Теплова енергія'),0)
             FROM monthly_conditions c WHERE c.year=?'''
        args=[year]
        if department_id is not None:
            q+=' AND c.department_id=?';args.append(department_id)
        q+=' ORDER BY c.month,c.department_id'
        data=defaultdict(lambda:{'energy':0.,'degree':[]})
        for month,dept,days,temp,e,h in conn.execute(q,args):
            data[month]['energy']+=e+h*GCAL_TO_KWH
            if temp is not None and days is not None:
                data[month]['degree'].append(max(0,15.5-temp)*days)
        rows=[]
        for month in sorted(data):
            val=data[month]
            degree=sum(val['degree'])/len(val['degree']) if val['degree'] else None
            rows.append((MONTH_LABELS[month-1],'Енергія, кВт·год екв.',round(val['energy'],3),False))
            if degree is not None:
                rows.append((MONTH_LABELS[month-1],'Градусо-дні, °C·доби',round(degree,2),False))
        return _df(rows)
    finally:
        conn.close()


def _price(tariffs, res_id, dep_id, dt):
    valid=[r for r in tariffs[res_id] if (r[0] is None or r[0]==dep_id)
           and r[2]<=dt and (r[3] is None or r[3]>=dt)]
    if not valid:
        return None
    valid.sort(key=lambda r: (r[0] == dep_id, r[2]),reverse=True)
    return float(valid[0][1])


def get_cost_records(year=None):

    conn=get_connection()
    try:
        tariffs=defaultdict(list)
        for r,dep,price,start,end in conn.execute('SELECT resource_id,department_id,price,start_date,end_date FROM tariffs'):
            tariffs[r].append((dep,price,start,end))
        q='''SELECT c.year,c.month,c.department_id,d.name,c.resource_id,r.name,c.amount
              FROM consumption c JOIN departments d ON d.id=c.department_id
              JOIN resources r ON r.id=c.resource_id'''
        args=[]
        if year is not None: q+=' WHERE c.year=?';args=[year]
        rows=[];missing=[]
        for y,m,d,dname,r,rname,amount in conn.execute(q,args):
            price=_price(tariffs,r,d,f'{y:04d}-{m:02d}-01')
            if price is None:
                missing.append((y,m,dname,rname))
            else:
                rows.append(dict(year=y,month=m,department=dname,department_id=d,
                                 resource=rname,resource_id=r,amount=amount,
                                 price=price,cost=amount*price))
        return rows,missing
    finally:
        conn.close()


def monthly_cost(year, by='resource', department_id=None):
    rows,missing=get_cost_records(year)
    aggregate=defaultdict(float)
    for r in rows:
        if department_id is not None and r['department_id']!=department_id:continue
        series=r['resource'] if by=='resource' else r['department']
        aggregate[(r['month'],series)]+=r['cost']
    return _df([(MONTH_LABELS[m-1],s,round(v,2),False) for (m,s),v in sorted(aggregate.items())]), missing


def yearly_cost(by='resource', department_id=None):
    rows,missing=get_cost_records()
    aggregate=defaultdict(float)
    for r in rows:
        if department_id is not None and r['department_id']!=department_id: continue
        series=r['resource'] if by=='resource' else r['department']
        aggregate[(r['year'],series)]+=r['cost']
    return _df([(str(y),s,round(v,2),False) for (y,s),v in sorted(aggregate.items())]), missing


def pie_cost(year, department_id=None):
    rows,missing=get_cost_records(year)
    totals=defaultdict(float)
    for r in rows:
        if department_id is not None and r['department_id']!=department_id:continue
        totals[r['resource']]+=r['cost']
    return _df([(str(year),name,round(value,2),False) for name,value in sorted(totals.items())]),missing


INDICATOR_LABELS={
    'energy_cost_grn':'Витрати на енергію, грн',
    'energy_share_percent':'Енергетична складова витрат, %',
    'generation_share_percent':'Частка власної генерації, %',
    'energy_intensity_kwh_per_1000grn':'Енергоємність послуг, кВт·год/тис. грн',
    'co2_kg':'Розрахункові викиди CO₂, кг',
    'co2_kg_per_1000grn':'Питомі викиди CO₂, кг/тис. грн'
}


def indicator_yearly(indicator,department_id=None):
    return _df([(str(year),INDICATOR_LABELS[indicator],round(val,4),False)
                for year in YEARS if (val:=annual_kpi(year,department_id).get(indicator)) is not None])


def plot_dataframe(df, title, kind='line', ylabel='Показник', caption=None):


    df = df.copy()
    if df.empty:
        fig,ax=plt.subplots(figsize=(10,4)); ax.text(.5,.5,'Немає даних',ha='center',va='center'); ax.axis('off');return fig
    df['Значення']=pd.to_numeric(df['Значення'],errors='coerce')
    df['Виключити']=df['Виключити'].fillna(False).astype(bool)


    zero_gap = df['Значення'] <= 0
    if kind == 'dual':
        zero_gap = zero_gap & ~df['Серія'].str.contains('Градусо-дні', na=False)
    elif 'власної генерації' in title.lower():
        zero_gap = zero_gap & False
    df.loc[df['Виключити'] | zero_gap, 'Значення']=float('nan')
    periods=list(dict.fromkeys(df['Період'].astype(str)))
    fig,ax=plt.subplots(figsize=(10.6,4.6),dpi=130)
    if kind=='pie':
        view=df[df['Значення'].notna()].groupby('Серія')['Значення'].sum().sort_values(ascending=False)
        if len(view):
            wedges,_,autotexts=ax.pie(view.values,autopct='%1.1f%%',startangle=90,
                            pctdistance=.8,wedgeprops=dict(width=.7,edgecolor='white'))
            ax.legend(wedges,view.index,loc='center left',bbox_to_anchor=(1.0,.5),fontsize=9)
            for t in autotexts: t.set_fontsize(9)
        else:ax.text(.5,.5,'Немає додатних значень',ha='center',va='center')
        ax.set_aspect('equal')
    elif kind=='dual':
        left='Енергія, кВт·год екв.'
        right='Градусо-дні, °C·доби'
        for ser,axis,style in [(left,ax,'-o'),(right,ax.twinx(),'--s')]:
            group=df[df['Серія']==ser].set_index('Період')['Значення']
            vals=[group.get(p,float('nan')) for p in periods]
            axis.plot(range(len(periods)),vals,style,label=ser,markersize=4)
            axis.set_ylabel(ser,fontsize=8)
        ax.set_xticks(range(len(periods)));ax.set_xticklabels(periods,rotation=35,ha='right',fontsize=8)
        ax.grid(alpha=.2)
    else:
        for ser,group in df.groupby('Серія',sort=False):
            vals=group.groupby('Період')['Значення'].sum(min_count=1)
            y=[vals.get(p,float('nan')) for p in periods]
            if kind=='bar':

                n=max(1,df['Серія'].nunique())
                width=.78/n
                k=list(dict.fromkeys(df['Серія'])) .index(ser)
                ax.bar([x-.39+(k+.5)*width for x in range(len(periods))],y,width,label=ser)
            else:ax.plot(range(len(periods)),y,marker='o',markersize=3.5,label=ser)
        ax.set_xticks(range(len(periods)));ax.set_xticklabels(periods,rotation=35,ha='right',fontsize=8)
        ax.set_ylabel(ylabel,fontsize=9)
        ax.grid(axis='y',alpha=.22)
        if df['Серія'].nunique()>1:ax.legend(loc='best',fontsize=7,ncol=2)
    ax.set_title(title,fontsize=13,fontweight='bold',pad=12)
    if caption: fig.text(.5,.005,caption,ha='center',fontsize=7,color='dimgray')
    fig.tight_layout(rect=(0,.028,1,1))
    return fig


def chart_png_bytes(df, title, kind, ylabel):
    fig=plot_dataframe(df,title,kind,ylabel)
    buff=io.BytesIO();fig.savefig(buff,format='png',dpi=150,bbox_inches='tight',facecolor='white')
    plt.close(fig);buff.seek(0)
    return buff.getvalue()
