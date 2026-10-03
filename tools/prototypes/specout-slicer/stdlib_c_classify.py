"""試作（最初の検証）: C 向けの決定的分類（標準ライブラリのみ・tree-sitter 不要）と、過去 CR の LLM 分類
（wave-*-chunk-*-class.json）の一致率を測る。使い方: python3 stdlib_c_classify.py <repo> <04_specout/{repo} ディレクトリ>"""
import json, re, sys, os
REPO, D = sys.argv[1], sys.argv[2]
KW = {'if','for','while','switch','return','sizeof','do','else'}

def strip_c(src):
    """コメント・文字列を同じ長さの空白に置換（行番号保持）。コメント位置も返す。"""
    out = list(src); i = 0; n = len(src); cmt = [False]*n
    while i < n:
        c = src[i]; nx = src[i+1] if i+1 < n else ''
        if c == '/' and nx == '*':
            j = src.find('*/', i+2); j = n if j < 0 else j+2
            for k in range(i, j):
                cmt[k] = True
                if out[k] != '\n': out[k] = ' '
            i = j
        elif c == '/' and nx == '/':
            j = src.find('\n', i); j = n if j < 0 else j
            for k in range(i, j): cmt[k] = True; out[k] = ' '
            i = j
        elif c in '"\'':
            j = i+1
            while j < n and src[j] != c:
                j += 2 if src[j] == '\\' else 1
            for k in range(i+1, min(j, n)):
                if out[k] != '\n': out[k] = ' '
            i = j+1
        else: i += 1
    return ''.join(out), cmt

cache = {}
def analyze(path):
    if path in cache: return cache[path]
    src = open(os.path.join(REPO, path), errors='replace').read()
    code, cmt = strip_c(src)
    # 行頭オフセット
    starts = [0] + [m.end() for m in re.finditer('\n', src)]
    # 関数定義: 深さ0 で  name(...) { の形
    funcs = []  # (body_start_off, body_end_off, name)
    depth = 0; i = 0; n = len(code); body_start = None; cand = None
    while i < n:
        ch = code[i]
        if ch == '{':
            if depth == 0:
                head = code[max(0, i-600):i]
                head = re.sub(r'#[^\n]*', '', head)
                m = re.search(r'([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:__attribute__\s*\(\(.*?\)\))?\s*$', head, re.S)
                cand = m.group(1) if m and m.group(1) not in KW else None
                body_start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and cand: funcs.append((body_start, i, cand)); cand = None
        i += 1
    cache[path] = (src, code, cmt, starts, funcs)
    return cache[path]

def classify(hit):
    src, code, cmt, starts, funcs = analyze(hit['file'])
    ln = hit['line_no']; off0 = starts[ln-1]; off1 = starts[ln] if ln < len(starts) else len(src)
    line_code = code[off0:off1]; sym = hit['symbol']
    if not re.search(r'\b%s\b' % re.escape(sym), line_code):
        return 'false-positive', []
    for s, e, name in funcs:
        if s <= off0 <= e:
            return 'propagation-direct', [name]
    # 関数外: 宣言・#define・プロトタイプ。ヘッダのプロトタイプは自分自身を返す LLM 例もあり
    return 'propagation-direct', []

agree = tot = 0; diffs = []
for w in range(0, 10):
    import glob
    hp = os.path.join(D, f'wave-{w}-hits.json')
    cps = glob.glob(os.path.join(D, f'wave-{w}-chunk-*-class.json'))
    if not (os.path.exists(hp) and cps): continue
    hits = json.load(open(hp))['hits']; cl = []
    for cp in cps:
        x = json.load(open(cp)); cl += x if isinstance(x, list) else x['classification']
    llm = {e['line_id']: e for e in cl}
    for h in hits:
        c, ns = classify(h); e = llm[h['line_id']]
        ns_llm = set(e['next_symbols']) - {h['symbol']}  # 自己再投入は visited で無害なので除外して比較
        ok = (set(ns) - {h['symbol']} == ns_llm)
        tot += 1; agree += ok
        if not ok: diffs.append((h['line_id'], h['file'], h['line_no'], h['matched_text'].strip()[:70], (c, ns), (e['classification'], e['next_symbols'])))
print(f'一致 {agree}/{tot}')
for d in diffs: print(d)
