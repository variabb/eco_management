
import io
import math
import sqlite3
import unittest
import zipfile
from pathlib import Path
import matplotlib.pyplot as plt
from database import get_connection
from lab3_charts import (monthly_consumption,yearly_consumption,heating_vs_weather,
    yearly_cost,pie_cost,indicator_yearly,plot_dataframe,chart_png_bytes,
    get_cost_records,save_note,get_note,init_lab3_db)
from lab3_exports import export_word,export_excel


class TestLab3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_lab3_db()

    def test_01_source_data_complete(self):
        c=get_connection()
        try:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM consumption').fetchone()[0],2040)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM production').fetchone()[0],120)
            self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())
        finally:c.close()

    def test_02_month_and_year(self):
        self.assertEqual(len(monthly_consumption(2025,1)),48)
        self.assertEqual(len(yearly_consumption(1)),40)
        self.assertEqual(len(heating_vs_weather(2025)),24)

    def test_03_closed_month_gap(self):
        df=monthly_consumption(2020,1)
        self.assertTrue((df[df['Період'].str.startswith(('04','05'))]['Значення']==0).all())
        fig=plot_dataframe(df,'2020','line','кВт·год')
        try:
            for line in fig.axes[0].lines:
                self.assertTrue(math.isnan(float(line.get_ydata()[3])))
                self.assertTrue(math.isnan(float(line.get_ydata()[4])))
        finally:plt.close(fig)

    def test_04_costs_and_tariffs(self):
        rows,missing=get_cost_records(2025)
        self.assertFalse(missing)
        total=sum(x['cost'] for x in rows)
        self.assertAlmostEqual(total,3965298.39972,places=2)
        pie,_=pie_cost(2025)
        self.assertAlmostEqual(sum(pie['Значення']),round(total,2),delta=.05)

    def test_05_editor_does_not_modify_db(self):
        c=get_connection()
        try:before=c.execute('SELECT SUM(amount) FROM consumption').fetchone()[0]
        finally:c.close()
        df=monthly_consumption(2025,1);copy=df.copy();copy.loc[0,'Значення']+=1000
        copy.loc[1,'Виключити']=True
        bytes_data=chart_png_bytes(copy,'Тест','line','кВт·год')
        self.assertGreater(len(bytes_data),1000)
        c=get_connection()
        try:after=c.execute('SELECT SUM(amount) FROM consumption').fetchone()[0]
        finally:c.close()
        self.assertEqual(before,after)

    def test_06_expert_note_saved(self):
        key='unittest:lab3:temporary'
        save_note(key,'Тест','Тестовий графік','2025',None,None,'Перевірено')
        self.assertEqual(get_note(key),'Перевірено')
        c=get_connection()
        try:c.execute('DELETE FROM chart_notes WHERE chart_key=?',(key,));c.commit()
        finally:c.close()

    def test_07_exports(self):
        chart=dict(title='Тестовий графік',df=monthly_consumption(2025,1),
                   kind='line',ylabel='кВт·год',description='Тест',comment='Коментар')
        doc=export_word([chart]);xls=export_excel([chart])
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(doc)))
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(xls)))
        self.assertGreater(len(doc),20000)
        self.assertGreater(len(xls),10000)

    def test_08_indicator_data(self):
        self.assertEqual(len(indicator_yearly('energy_share_percent')),10)


if __name__=='__main__':unittest.main(verbosity=2)
