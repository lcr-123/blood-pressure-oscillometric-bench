"""检查 table 的 tblGrid 列宽是否真的写进去了（python-docx 的 cell.width 不写 gridCol）。"""
import re
from docx import Document

doc = Document(r"C:\Users\31800\Desktop\血压仪\示波法血压采集流程说明.docx")
for idx, t in enumerate(doc.tables):
    xml = t._tbl.xml
    grid = re.search(r"<w:tblGrid>.*?</w:tblGrid>", xml, re.S)
    cols = re.findall(r'<w:gridCol w:w="(\d+)"', grid.group(0)) if grid else []
    tw = re.search(r'<w:tblW w:type="(\w+)" w:w="(\d+)"', xml)
    print(f"table[{idx}] cols={len(t.columns)} rows={len(t.rows)} "
          f"gridCol={cols} sum={sum(int(c) for c in cols)} tblW={tw.groups() if tw else None}")
