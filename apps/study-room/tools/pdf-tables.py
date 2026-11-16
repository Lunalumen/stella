"""Bounded, offline pdfplumber adapter. Upstream: jsvine/pdfplumber (MIT)."""
import json,sys
import pdfplumber

def extract(path,page):
    with pdfplumber.open(path,pages=[page]) as pdf:
        source=pdf.pages[0]
        # Avoid quadratic line intersection work on pathological vector drawings.
        if len(source.edges)>6000:raise ValueError('Page has too many vector edges for bounded table extraction.')
        found=source.find_tables()
        tables=[];remaining=12000;truncated=len(found)>5
        for table in found[:5]:
            raw=table.extract();rows=[]
            truncated|=len(raw)>50
            for row in raw[:50]:
                cells=[];truncated|=len(row)>12
                for cell in row[:12]:
                    text=cell or '';limit=min(300,remaining)
                    cells.append(text[:limit]);remaining-=len(cells[-1]);truncated|=len(text)>limit
                rows.append(cells)
                if remaining<=0:break
            tables.append({'bbox':list(table.bbox),'rows':rows})
            if remaining<=0:truncated=True;break
        return {'page':page,'engine':'pdfplumber','version':pdfplumber.__version__,'tables':tables,'detectedTables':len(found),'truncated':truncated,'verified':False,
                'warning':'텍스트 PDF의 선·셀 기반 표 추출입니다. 빈 결과는 표 없음의 증명이 아닙니다. 병합 셀·스캔 표는 원본과 대조하세요.'}

if __name__=='__main__':
    try:print(json.dumps(extract(sys.argv[1],int(sys.argv[2])),ensure_ascii=False))
    except Exception:
        print('Local table extraction failed.',file=sys.stderr);raise SystemExit(1)
