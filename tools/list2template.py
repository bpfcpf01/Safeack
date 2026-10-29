#!/usr/bin/env python3
"""แปลงรายการจุดตรวจ <-> TEMPLATE_DATA ใน index.html

  python3 tools/list2template.py export รายการจุดตรวจ.csv   # ดึงรายการปัจจุบันออกเป็น CSV
  python3 tools/list2template.py import รายการจุดตรวจ.csv   # เขียน CSV กลับเข้า index.html

CSV มี 3 คอลัมน์: หมวด, รหัส, ตำแหน่ง (แถวแรกเป็นหัวตาราง) เปิด/แก้ใน Excel ได้
หมวดเรียงตามที่ปรากฏครั้งแรก ลำดับจุดในหมวดนับให้เองตามลำดับแถว แถวที่ว่างทั้งแถวจะถูกข้าม

ข้อควรรู้: import = stable id ของจุดเปลี่ยน ผลตรวจ/รูปที่บันทึกไว้กับรายการเดิมจะไม่โชว์ (ดู CLAUDE.md)
ใช้ตอนตั้งรายการให้ไซต์ใหม่ที่ยังไม่มีข้อมูลเท่านั้น หรือให้ผู้ใช้สำรองข้อมูลก่อน
"""
import csv, json, re, sys
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / 'index.html'
LINE_RE = re.compile(r'^window\.TEMPLATE_DATA = (.*);$', re.M)
HEAD = ['หมวด', 'รหัส', 'ตำแหน่ง']


def read_html():
    s = HTML.read_text(encoding='utf-8')
    m = LINE_RE.search(s)
    if not m:
        sys.exit('ไม่เจอบรรทัด window.TEMPLATE_DATA ใน index.html')
    return s, m


def export(out):
    _, m = read_html()
    # utf-8-sig ให้ Excel อ่านภาษาไทยถูก
    with open(out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(HEAD)
        for c in json.loads(m.group(1)):
            for p in c['points']:
                w.writerow([c['category'], p.get('code', ''), p.get('location', '')])
    print('เขียน', out)


def load_csv(src):
    with open(src, encoding='utf-8-sig', newline='') as f:
        rows = [[x.strip() for x in r] for r in csv.reader(f)]
    if rows and rows[0][:3] == HEAD:
        rows = rows[1:]
    cats = {}
    for n, r in enumerate(rows, 2):
        r = (r + ['', '', ''])[:3]
        if not any(r):
            continue
        cat, code, loc = r
        if not cat:
            sys.exit(f'แถว {n}: ไม่มีชื่อหมวด')
        if not code and not loc:
            sys.exit(f'แถว {n}: ต้องมีรหัสหรือตำแหน่งอย่างน้อยหนึ่งช่อง')
        cats.setdefault(cat, []).append((code, loc))
    if not cats:
        sys.exit('ไฟล์ไม่มีรายการ')
    # ห้ามใส่ id ลงไป — ดู CLAUDE.md หัวข้อ "id มี 2 ชั้น"
    return [{'slide': i, 'category': cat,
             'points': [{'order': str(j), 'code': code, 'location': loc}
                        for j, (code, loc) in enumerate(pts, 1)]}
            for i, (cat, pts) in enumerate(cats.items(), 1)]


def import_(src):
    data = load_csv(src)
    s, m = read_html()
    line = 'window.TEMPLATE_DATA = ' + json.dumps(data, ensure_ascii=False) + ';'
    if '</script' in line.lower():
        sys.exit('ข้อความในรายการมี "</script" ซึ่งจะทำให้หน้าเว็บพัง')
    HTML.write_text(s[:m.start()] + line + s[m.end():], encoding='utf-8')
    print(f'อัปเดต index.html: {len(data)} หมวด รวม {sum(len(c["points"]) for c in data)} จุด')


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ('export', 'import'):
        sys.exit(__doc__)
    (export if sys.argv[1] == 'export' else import_)(sys.argv[2])
