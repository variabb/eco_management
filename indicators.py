
from collections import defaultdict
from database import get_connection
from energy_data import find_tariff
from lab2_data import GCAL_TO_KWH, CO2_ELECTRIC_KG_PER_KWH, CO2_HEAT_KG_PER_GCAL


def active_mean(values):
    positive = [v for v in values if v is not None and v > 0]
    return sum(positive)/len(positive) if positive else None


def annual_nonuniformity(values):
    positive = [v for v in values if v is not None and v > 0]
    return max(positive)/min(positive) if positive else None



def month_rows(year, department_id=None, resource_id=None):
    conn = get_connection()
    try:
        conditions = { (d,m): days for d,m,days in conn.execute(
            'SELECT department_id,month,working_days FROM monthly_conditions WHERE year=?',(year,)) }
        query='''SELECT c.department_id,d.name,c.resource_id,r.name,r.unit,c.month,c.amount
                 FROM consumption c JOIN departments d ON d.id=c.department_id
                 JOIN resources r ON r.id=c.resource_id WHERE c.year=?'''
        params=[year]
        if department_id is not None:
            query+=' AND c.department_id=?';params.append(department_id)
        if resource_id is not None:
            query+=' AND c.resource_id=?';params.append(resource_id)
        query+=' ORDER BY d.id,r.id,c.month'
        rows=[]
        for d,dname,r,rname,unit,m,amount in conn.execute(query,params):
            days=conditions.get((d,m))
            mean=amount/days if days and amount>0 else None
            tariff=find_tariff(conn,r,d,year,m)
            rows.append(dict(department_id=d,department=dname,resource_id=r,resource=rname,unit=unit,
                             year=year,month=m,amount=amount,working_days=days,daily=mean,
                             tariff=tariff,cost=amount*tariff if tariff is not None else None))
        return rows
    finally:
        conn.close()


def year_statistics(year, department_id=None):
    grouped=defaultdict(list)
    for row in month_rows(year,department_id):
        grouped[(row['department_id'],row['department'],row['resource'],row['unit'])].append(row)
    result=[]
    for (did,dname,rname,unit),records in grouped.items():
        valid=[r for r in records if r['daily'] is not None]
        maxrow=max(valid,key=lambda x:x['daily']) if valid else None
        minrow=min(valid,key=lambda x:x['daily']) if valid else None
        result.append(dict(department=dname,department_id=did,resource=rname,unit=unit,
                           annual_volume=sum(r['amount'] for r in records),
                           active_months=len(valid),missing_months=[r['month'] for r in records if not r['daily']],
                           mean_daily=active_mean([r['daily'] for r in records]),
                           max_daily=maxrow['daily'] if maxrow else None,
                           max_month=maxrow['month'] if maxrow else None,
                           min_daily=minrow['daily'] if minrow else None,
                           min_month=minrow['month'] if minrow else None,
                           nonuniformity=annual_nonuniformity([r['daily'] for r in records])))
    return result


def monthly_indicators(year, department_id=None):

    conn=get_connection()
    try:
        query='''SELECT d.id,d.name,d.heated_area,c.month,c.working_days,c.outdoor_temp,c.indoor_temp
              FROM monthly_conditions c JOIN departments d ON d.id=c.department_id
              WHERE c.year=? AND d.type='Підрозділ' '''
        args=[year]
        if department_id is not None:
            query+=' AND d.id=?';args.append(department_id)
        query+=' ORDER BY d.id,c.month'
        rows=[]
        for did,name,area,month,days,outdoor,indoor in conn.execute(query,args):
            vals=dict(conn.execute('''SELECT r.name,c.amount FROM consumption c JOIN resources r
                  ON r.id=c.resource_id WHERE c.department_id=? AND c.year=? AND c.month=?''',(did,year,month)))
            e=vals.get('Електроенергія',0.0)
            heat=vals.get('Теплова енергія',0.0)
            cost_energy=0.0
            for rid,rname,amount in conn.execute('''SELECT r.id,r.name,c.amount FROM consumption c JOIN resources r
                ON r.id=c.resource_id WHERE c.department_id=? AND c.year=? AND c.month=?''',(did,year,month)):
                if rname in ('Електроенергія','Теплова енергія'):
                    tariff=find_tariff(conn,rid,did,year,month)
                    if tariff is not None: cost_energy+=amount*tariff
            finance=conn.execute('''SELECT total_expenses FROM monthly_finances
                WHERE department_id=? AND year=? AND month=?''',(did,year,month)).fetchone()
            rev=conn.execute('''SELECT revenue FROM production
                WHERE department_id=? AND year=? AND month=?''',(did,year,month)).fetchone()
            split=conn.execute('''SELECT lighting_kwh,cooling_kwh FROM monthly_electricity_breakdown
                WHERE department_id=? AND year=? AND month=?''',(did,year,month)).fetchone()
            lighting_kwh, cooling_kwh = split if split else (None,None)
            gen=conn.execute('''SELECT COALESCE(SUM(amount),0) FROM monthly_generation
                WHERE department_id=? AND year=? AND month=?''',(did,year,month)).fetchone()[0]
            emissions=e*CO2_ELECTRIC_KG_PER_KWH+heat*CO2_HEAT_KG_PER_GCAL
            total_expenses=finance[0] if finance else None
            revenue=rev[0] if rev else None
            eq_kwh=e+heat*GCAL_TO_KWH+gen
            rows.append(dict(department_id=did,department=name,year=year,month=month,days=days,
                outdoor_temp=outdoor,indoor_temp=indoor,area_m2=area,
                degree_days=max(0.0,15.5-outdoor)*days if days is not None and outdoor is not None else None,
                electricity_kwh=e,heat_gcal=heat,energy_eq_kwh=eq_kwh,
                heat_specific_gcal_m2=heat/area if area else None,
                electricity_specific_kwh_m2=e/area if area else None,
                lighting_specific_kwh_m2=lighting_kwh/area if (area and lighting_kwh is not None) else None,
                cooling_specific_kwh_m2=cooling_kwh/area if (area and cooling_kwh is not None) else None,
                energy_cost_grn=cost_energy,total_expenses_grn=total_expenses,
                energy_share_percent=cost_energy/total_expenses*100 if total_expenses and total_expenses>0 else None,
                generation_kwh=gen,
                generation_share_percent=gen/(gen+e)*100 if (gen+e)>0 else None,
                revenue_grn=revenue,
                energy_intensity_kwh_per_1000grn=eq_kwh/revenue*1000 if revenue and revenue>0 else None,
                co2_kg=emissions,co2_kg_per_1000grn=emissions/revenue*1000 if revenue and revenue>0 else None))
        return rows
    finally:
        conn.close()


def annual_kpi(year, department_id=None):

    rows=monthly_indicators(year,department_id)
    e=sum(x['electricity_kwh'] for x in rows)
    h=sum(x['heat_gcal'] for x in rows)
    g=sum(x['generation_kwh'] for x in rows)
    cost=sum(x['energy_cost_grn'] for x in rows)
    expenses=sum(x['total_expenses_grn'] or 0 for x in rows)
    rev=sum(x['revenue_grn'] or 0 for x in rows)
    co2=sum(x['co2_kg'] for x in rows)
    eq=e+h*GCAL_TO_KWH+g
    return {'year':year,'department_id':department_id,'electricity_kwh':e,'heat_gcal':h,
      'generated_kwh':g,'energy_eq_kwh':eq,'energy_cost_grn':cost,'total_expenses_grn':expenses,
      'revenue_grn':rev,'co2_kg':co2,
      'energy_share_percent': cost/expenses*100 if expenses else None,
      'generation_share_percent':g/(g+e)*100 if g+e else None,
      'energy_intensity_kwh_per_1000grn':eq/rev*1000 if rev else None,
      'co2_kg_per_1000grn':co2/rev*1000 if rev else None}


def year_comparison(start=2016,end=2025,department_id=None):
    return [annual_kpi(y,department_id) for y in range(start,end+1)]
