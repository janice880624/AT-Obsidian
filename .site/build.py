"""把 Obsidian Vault 轉成單頁互動學習網站。

用法：python3 .site/build.py            （在 repo 根目錄執行）
輸出：_site/index.html                   （GitHub Actions 會自動部署到 GitHub Pages）
"""
import os, re, json, subprocess, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from subareas import SUB, COMMON  # noqa: E402

VAULT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(HERE)
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(VAULT, '_site', 'index.html')

# 筆記類型 → 臨床路徑階段
STAGE = {
    '骨骼或關節': 'anat', '肌肉': 'anat', '韌帶': 'anat', '肌腱': 'anat', '神經': 'anat',
    '傷害': 'inj',
    '主觀問診': 'eval', '系統性評估': 'eval', '身體檢查': 'eval', 'STTT理學檢查': 'eval', '臨床評估': 'eval',
    '評估': 'eval', '臨床決策規則': 'eval', '轉介分流': 'eval', '評估與檢查': 'eval',
    '特殊檢查': 'test', '運動治療': 'rx', '貼紮': 'rx', '功能性測試': 'func',
}
# 模板留下的佔位句，網站上不顯示
PLACEHOLDER = [re.compile(p) for p in [
    r'原筆記(未將|的相關內容已保留|未提供|未)', r'待依原文或可靠來源補充', r'依上述操作',
    r'^區域入口：', r'後續可依可靠來源再細化']]
SKIP_TYPES = {'每日知識包索引'}


def parse(path):
    t = open(path, encoding='utf-8').read().replace('\r\n', '\n')
    meta = {}
    m = re.match(r'^---\n(.*?)\n---\n?', t, re.S)
    if m:
        for line in m.group(1).split('\n'):
            mm = re.match(r'^([^:\s][^:]*):\s*(.*)$', line)
            if mm:
                meta[mm.group(1).strip()] = mm.group(2).strip().strip('"')
        t = t[m.end():]
    return meta, t


def level(line):
    m = re.match(r'^(#{2,6}) ', line)
    return len(m.group(1)) if m else 0


def clean(body):
    lines = [l for l in body.split('\n')
             if not (l.strip() and any(p.search(l.strip()) for p in PLACEHOLDER))
             and not re.match(r'^# ', l)]
    res = []
    for i, l in enumerate(lines):  # 拿掉沒有內容的段落標題
        lv = level(l)
        if lv:
            j, has = i + 1, False
            while j < len(lines):
                lj = level(lines[j])
                if lj and lj <= lv:
                    break
                if lines[j].strip() and not lj:
                    has = True
                    break
                j += 1
            if not has:
                continue
        res.append(l)
    txt = re.sub(r'\n{3,}', '\n\n', '\n'.join(res)).strip()
    return re.sub(r'!\[\[(assets/[^\]|]+?\.svg)(\|[^\]]*)?\]\]', lambda m: f'![圖](svg:{m.group(1)})', txt)


def subarea(region, title, en):
    key = (title.split('－', 1)[-1] + ' ' + en)
    if re.search(COMMON[1], key):
        return COMMON[0]
    for name, rx in SUB.get(region, []):
        if re.search(rx, key):
            return name
    return ''


def main():
    notes, byname = [], {}
    for top in sorted(os.listdir(VAULT)):
        if not re.match(r'^0\d_', top) or top == '07_個案紀錄':
            continue
        for root, dirs, files in os.walk(os.path.join(VAULT, top)):
            dirs.sort()
            rel = os.path.relpath(root, VAULT)
            if '每日知識包目錄' in rel:
                continue
            for f in sorted(files):
                if not f.endswith('.md'):
                    continue
                meta, body = parse(os.path.join(root, f))
                ty = meta.get('類型', '')
                if ty in SKIP_TYPES:
                    continue
                name = f[:-3]
                regs = [x.strip() for x in meta.get('區域', '').strip('[]').split(',') if x.strip()]
                en = meta.get('英文名稱', '')
                if '待依' in en:
                    en = ''
                g = STAGE.get(ty, 'idx')
                n = dict(id=len(notes), t=name, ty=ty or '索引', g=g, r=regs, en=en,
                         st=meta.get('狀態', ''), d=meta.get('更新日期', ''), b=clean(body))
                if g != 'idx':
                    n['sa'] = [subarea(r, name, en) for r in regs]
                byname[name] = n['id']
                notes.append(n)
    for n in notes:
        ls = []
        for m in re.finditer(r'(?<!!)\[\[([^\]|#]+)(#[^\]|]*)?(\|[^\]]*)?\]\]', n['b']):
            k = byname.get(m.group(1).strip())
            if k is not None and k != n['id'] and k not in ls:
                ls.append(k)
        n['l'] = ls
    svgs = {}
    for p in sorted(set(re.findall(r'svg:(assets/[^)]+)', '\n'.join(n['b'] for n in notes)))):
        fp = os.path.join(VAULT, p)
        if os.path.exists(fp):
            svgs[p] = re.sub(r'<script.*?</script>', '', open(fp, encoding='utf-8').read(), flags=re.S)
    subs = {r: [COMMON[0]] + [s for s, _ in rules] for r, rules in SUB.items()}

    sha = os.environ.get('GITHUB_SHA', '')[:7]
    date = ''
    try:
        out = subprocess.run(['git', '-C', VAULT, 'log', '-1', '--format=%h|%cd', '--date=format:%Y-%m-%d %H:%M'],
                             capture_output=True, text=True).stdout.strip()
        if out:
            sha2, date = out.split('|', 1)
            sha = sha or sha2
    except OSError:
        pass
    built = f'資料來源：github.com/janice880624/AT-Obsidian（{sha} · {date}）' if sha else ''
    data = dict(notes=notes, svgs=svgs, subs=subs, built=built)

    html = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    marked = open(os.path.join(HERE, 'marked.min.js'), encoding='utf-8').read().replace('</script', '<\\/script')
    html = html.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>',
                        '<script>' + marked + '</script>')
    html = html.replace('/*DATA*/', json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(html)
    c = Counter(n['g'] for n in notes)
    unsorted = sum(1 for n in notes if 'sa' in n and '' in n['sa'])
    print(f'{len(notes)} 篇筆記、{sum(len(n["l"]) for n in notes)} 條連結、{len(svgs)} 張圖 → {OUT} '
          f'({os.path.getsize(OUT)/1e6:.1f} MB)；{dict(c)}；未歸入細分部位 {unsorted} 篇')


if __name__ == '__main__':
    main()
