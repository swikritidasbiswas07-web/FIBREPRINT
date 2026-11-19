"""Read-only scientific spreadsheet audit using only Python standard library.

Does NOT transform rows into labelled FIBREPRINT observations.
Supports ordinary unencrypted .xlsx files; preserves originals.
Run: python inspect_workbook.py data/source_figshare_14675760_v4/FILENAME.xlsx
"""
from __future__ import annotations
import argparse
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
P = '{http://schemas.openxmlformats.org/package/2006/relationships}'


def column_number(ref: str) -> int:
    letters = re.match(r'[A-Z]+', ref or '')
    n = 0
    for c in (letters.group() if letters else ''):
        n = n * 26 + ord(c) - 64
    return n - 1


def parse_shared_strings(z):
    path = 'xl/sharedStrings.xml'
    if path not in z.namelist():
        return []
    root = ET.fromstring(z.read(path))
    return [''.join(t.text or '' for t in si.iter(S + 't')) for si in root.findall(S + 'si')]


def cell_value(cell, strings):
    kind = cell.get('t')
    if kind == 'inlineStr':
        return ''.join(t.text or '' for t in cell.iter(S+'t'))
    v = cell.find(S+'v')
    if v is None:
        return ''
    if kind == 's':
        try: return strings[int(v.text)]
        except (ValueError, IndexError, TypeError): return '<INVALID SHARED STRING>'
    return v.text or ''


def workbook_sheets(z):
    w = ET.fromstring(z.read('xl/workbook.xml'))
    links = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    relations = {item.get('Id'): item.get('Target') for item in links.findall(P+'Relationship')}
    for sheet in w.findall('.//' + S + 'sheet'):
        target = relations.get(sheet.get(R+'id'), '')
        if target.startswith('/'):
            path = target.lstrip('/')
        elif target.startswith('xl/'):
            path = target
        else:
            path = 'xl/' + target.lstrip('./')
        if path not in z.namelist():
            yield sheet.get('name'), None
        else:
            yield sheet.get('name'), path


def inspect(filename: Path, max_rows: int = 8):
    report = {'original_file': str(filename), 'file_size_bytes': filename.stat().st_size,
              'warning': 'READ-ONLY COLUMN INSPECTION. Headers and preview rows are not validated observations.',
              'sheets': []}
    with zipfile.ZipFile(filename) as z:
        if 'xl/workbook.xml' not in z.namelist():
            raise ValueError('Not a supported .xlsx workbook')
        strings = parse_shared_strings(z)
        for name, path in workbook_sheets(z):
            if not path:
                report['sheets'].append({'name': name, 'error':'sheet XML missing'}); continue
            worksheet = ET.fromstring(z.read(path))
            row_data = []
            filled = Counter()
            maxcol = -1
            for row in worksheet.findall('.//' + S + 'sheetData/' + S + 'row'):
                cells = {}
                for cell in row.findall(S+'c'):
                    idx = column_number(cell.get('r', ''))
                    if idx < 0 or idx > 5000: continue
                    value = cell_value(cell, strings)
                    if value != '':
                        cells[idx] = value[:250] if isinstance(value, str) else value
                        filled[idx] += 1
                        maxcol = max(maxcol, idx)
                if cells: row_data.append({'row': int(row.get('r') or 0), 'cells': cells})
            preview = []
            for row in row_data[:max_rows]:
                preview.append({'excel_row': row['row'],
                                'values': {str(k+1):v for k,v in sorted(row['cells'].items())}})
            report['sheets'].append({
                'name':name, 'nonempty_rows':len(row_data),'last_populated_column_index':maxcol+1,
                'nonempty_cells_by_column':{str(k+1):n for k,n in sorted(filled.items())},
                'preview_first_rows':preview,
                'note':'Cell dates, merged headers, equations and percentage formatting require manual interpretation.'
            })
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('xlsx',type=Path)
    parser.add_argument('--output', type=Path,default=None)
    args=parser.parse_args()
    if not args.xlsx.is_file(): raise SystemExit(f'File not found: {args.xlsx}')
    if args.xlsx.suffix.lower() != '.xlsx': raise SystemExit('Expected an .xlsx workbook.')
    result=inspect(args.xlsx)
    output=args.output or args.xlsx.with_name(args.xlsx.stem+'_audit.json')
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Workbook audit saved:',output)
    for s in result['sheets']:
        print(f"  {s['name']}: {s.get('nonempty_rows','?')} populated rows, "
              f"{s.get('last_populated_column_index','?')} maximum column index")
    print('Do not rename this workbook to curated_observations.csv.')


if __name__=='__main__':
    main()
