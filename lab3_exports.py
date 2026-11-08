
from __future__ import annotations
import io
import re
from datetime import datetime
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlsxImage
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from lab3_charts import chart_png_bytes


def _clean_value(x):
    import pandas as pd
    if pd.isna(x):return None
    return x.item() if hasattr(x,'item') else x


def export_word(charts, full_title='Звіт із графічного аналізу енергоспоживання'):
    doc=Document();sec=doc.sections[0]
    sec.top_margin=Cm(2.1);sec.bottom_margin=Cm(2.1)
    sec.left_margin=Cm(2.2);sec.right_margin=Cm(2.2)
    styles=doc.styles;normal=styles['Normal'];normal.font.name='DejaVu Sans';normal.font.size=Pt(10)
    normal.paragraph_format.space_after=Pt(5)
    t=doc.add_heading(full_title,0);t.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p=doc.add_paragraph('Кінотеатр «Планета Кіно — Блокбастер»');p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f'Сформовано: {datetime.now():%d.%m.%Y %H:%M} · Кількість графіків: {len(charts)}')
    doc.add_paragraph('Зміни точок графіка не впливають на вихідні записи бази даних.')
    for ix,chart in enumerate(charts,1):
        doc.add_heading(f'Рисунок 3.{ix} — {chart["title"]}',level=2)
        if chart.get('description'):doc.add_paragraph(chart['description'])
        img=io.BytesIO(chart.get('png') or chart_png_bytes(chart['df'],chart['title'],chart['kind'],chart['ylabel']))
        doc.add_picture(img,width=Cm(15.6))
        p=doc.add_paragraph(f'Рисунок 3.{ix} — {chart["title"]}')
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph('Експертний висновок:',style='Subtitle')
        doc.add_paragraph(chart.get('comment','Коментар не введено.') or 'Коментар не введено.')
        dframe=chart['df'];doc.add_paragraph('Числові значення графіка (режим експертного сценарію):')
        table=doc.add_table(rows=1,cols=4);table.style='Table Grid'
        for cell,text in zip(table.rows[0].cells, ['Період','Серія','Значення','Вилучено']):cell.text=text
        if len(dframe)>50:
            doc.add_paragraph('Повний набір даних наведено в експортованій книзі Excel;')
            dframe=dframe.head(40)
        for row in dframe.itertuples(index=False,name=None):
            cells=table.add_row().cells
            for c,v in zip(cells,row):c.text= '—' if v is None else str(v)
    doc.add_heading('Загальні висновки',level=1)
    doc.add_paragraph('Побудовано графіки динаміки використання ресурсів і фінансових витрат, '
                      'проведено зіставлення енерговикористання з погодними умовами, '
                      'оцінено розподіл грошових витрат між ресурсами та енергетичні індикатори. '
                      'Коментарі використано для інтерпретації тенденцій. '
                      'Редагування на графіку не змінює первинні записи.')
    buff=io.BytesIO();doc.save(buff);return buff.getvalue()


def export_excel(charts):
    wb=Workbook();summary=wb.active;summary.title='Огляд'
    summary.append(['ЕКО-ЕНЕРГЕТИЧНИЙ МЕНЕДЖМЕНТ | ЛР №3'])
    summary.append(['Кінотеатр «Планета Кіно — Блокбастер»'])
    summary.append(['Редагування графіка не змінює вихідні записи SQLite.'])
    summary.append([]);summary.append(['№ рисунка','Назва','Коментар'])
    for i,chart in enumerate(charts,1):
        summary.append([f'3.{i}',chart['title'],chart.get('comment','')])
        sh=wb.create_sheet(f'Графік 3.{i}')
        sh.append([f'Рисунок 3.{i} — {chart["title"]}'])
        sh.append(['Період','Серія','Значення','Виключено'])
        for row in chart['df'].itertuples(index=False,name=None):
            sh.append([_clean_value(x) for x in row])
        last=sh.max_row+2
        sh.cell(last,1,'Експертний коментар')
        sh.cell(last+1,1,chart.get('comment','Коментар не введено'))
        png=io.BytesIO(chart.get('png') or chart_png_bytes(chart['df'],chart['title'],chart['kind'],chart['ylabel']))
        png.name=f'chart_{i}.png'
        img=XlsxImage(png);img.width=840;img.height=360
        sh.add_image(img, f'F3')
        sh.freeze_panes='C4'
        sh.auto_filter.ref=f'A3:D{last-2}'
        sh.column_dimensions['A'].width=20
        sh.column_dimensions['B'].width=38
        sh.column_dimensions['C'].width=19
        sh.column_dimensions['D'].width=17
        sh.column_dimensions['F'].width=25
        for c in sh[3]:c.fill=PatternFill('solid',fgColor='17324D');c.font=Font(color='FFFFFF',bold=True)
        for row in sh.iter_rows(min_row=4,max_row=last-2,min_col=3,max_col=3):
            for cell in row:cell.number_format='#,##0.00'
        sh['A1'].font=Font(bold=True,size=14,color='17324D')
        sh['A2'].font=Font(italic=True,color='64748B')
    summary.column_dimensions['A'].width=18
    summary.column_dimensions['B'].width=72
    summary.column_dimensions['C'].width=88
    summary.freeze_panes='B6'
    for c in summary[5]:c.fill=PatternFill('solid',fgColor='17324D');c.font=Font(color='FFFFFF',bold=True)
    summary['A1'].font=Font(size=14,bold=True,color='17324D')
    summary['A2'].font=Font(italic=True,color='64748B')
    buff=io.BytesIO();wb.save(buff);return buff.getvalue()
