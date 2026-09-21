"""
crs_view.py — CRS Markdown 階層ビュー生成（HTML ビューア／CLI ツリー）

Usage:
    python3 crs_view.py <CRS_MD> --format {html|tree} [--out PATH] [--status "..."]

`xddp-crs-view` スキルが呼び出す決定的処理スクリプト。CRS Markdown のパースは
`xddp-common/scripts/crs_model.py`（`xddp-md2excel` と共有する共通パーサ）に委譲する。
標準ライブラリのみに依存する（`openpyxl` を必要としない）。

`--format html`（既定）は自己完結の単一 HTML ファイルを生成する。ステータス絞り込み・全文検索・
レビュー指摘のコメント入力に対応し、コメントは `/xddp-revise req` が読む
`## 2. 指摘事項と対応内容` テーブル（`#`／`重要度`／`場所`／`指摘内容`／`対応内容`／`対応状況`の6列）と
同一形式の Markdown として書き出せる。
`--format tree` は色付き CLI ツリーを標準出力（または `--out` 指定時はファイル）へ出力する。
"""

import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xddp-common" / "scripts"))
from crs_model import parse_crs_md  # noqa: E402

STATUS_ORDER = ['❓ 未決', '⚠️ 懸念あり', '🔍 要検討', '確定', '']


def _norm_status(s):
    s = (s or '').strip()
    for known in STATUS_ORDER:
        if known and known in s:
            return known
    return s


def _extract_meta(md_path):
    """先頭の `**key：** value` 行（最初の `## ` 見出しより前）から文書メタ情報を抽出する。"""
    meta = {}
    for raw in Path(md_path).read_text(encoding='utf-8').splitlines():
        line = raw.rstrip()
        if re.match(r'^## ', line):
            break
        m = re.match(r'^\*\*(.+?)：\*\*\s*(.*)', line)
        if m:
            meta[m.group(1)] = m.group(2).strip()
    return meta


def iter_sps(data):
    """categories を辿って (category, ur, sr_or_None, sp) を yield する。"""
    for cat in data['categories']:
        for ur in cat.ur_list:
            for sp in ur.direct_sp_list:
                yield cat, ur, None, sp
            for sr in ur.sr_list:
                for sp in sr.sp_list:
                    yield cat, ur, sr, sp


def status_counts(data):
    counts = {}
    for _, _, _, sp in iter_sps(data):
        s = _norm_status(sp.status) or '(未記入)'
        counts[s] = counts.get(s, 0) + 1
    return counts


# ── 案B: CLI ツリー ───────────────────────────────────────────────────────────

BADGE = {'確定': '\033[32m● 確定\033[0m', '🔍 要検討': '\033[33m◐ 要検討\033[0m',
         '⚠️ 懸念あり': '\033[31m◑ 懸念\033[0m', '❓ 未決': '\033[35m○ 未決\033[0m'}


def render_tree(data, meta, color=True, only_status=None):
    def badge(s):
        s = _norm_status(s)
        if not color:
            return f'[{s}]' if s else ''
        return BADGE.get(s, f'[{s}]' if s else '')

    def dim(t):
        return f'\033[2m{t}\033[0m' if color else t

    out = [f"{meta.get('タイトル', '(no title)')}  "
           f"({meta.get('対象CR', '?')}  v{meta.get('版数', '?')})"]
    c = status_counts(data)
    out.append(dim('  SP: ' + ('  '.join(f'{k} {v}' for k, v in sorted(c.items())) or '0')))
    out.append('')

    for cat in data['categories']:
        out.append(f"━━ ＜{cat.name}＞ " + '━' * 40)
        for ur in cat.ur_list:
            out.append('')
            out.append(f"▼ {ur.ur_id}  {ur.title}  {badge(ur.status)}")
            if ur.reason:
                out.append(dim('   理由: ' + ur.reason))
            if ur.kenen:
                out.append(dim('   ⚠ ' + ur.kenen))

            prev_spec_group = None
            for sp in ur.direct_sp_list:
                if only_status and _norm_status(sp.status) not in only_status:
                    continue
                if sp.spec_group != prev_spec_group:
                    prev_spec_group = sp.spec_group
                    if prev_spec_group:
                        out.append(f"   ＜{prev_spec_group}＞")
                out.append(f"   • {sp.sp_id}  {sp.title}  {badge(sp.status)}")

            prev_req_group = None
            for sr in ur.sr_list:
                if sr.req_group != prev_req_group:
                    prev_req_group = sr.req_group
                    axis = f"  {dim('[' + sr.axis + ']')}" if sr.axis else ''
                    if prev_req_group:
                        out.append(f"   ＜{prev_req_group}＞{axis}")
                out.append(f"   ├ {sr.sr_id}  {sr.title}  {badge(sr.status)}")
                prev_spec_group = None
                for sp in sr.sp_list:
                    if only_status and _norm_status(sp.status) not in only_status:
                        continue
                    if sp.spec_group != prev_spec_group:
                        prev_spec_group = sp.spec_group
                        if prev_spec_group:
                            out.append(f"   │    ＜{prev_spec_group}＞")
                    out.append(f"   │    • {sp.sp_id}  {sp.title}  {badge(sp.status)}")
        out.append('')
    return '\n'.join(out)


# ── 案A: 単一ファイル HTML ───────────────────────────────────────────────────

def e(s):
    return html.escape(s or '')


CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#1b1f24;--sub:#5b6572;--line:#dfe3e8;
--ur:#dbe6f6;--sr:#eceef1;--before:#fff6dd;--after:#e6f4e6;--accent:#2f5eb3;
--ok:#1a7f37;--warn:#b26a00;--risk:#b3261e;--open:#7b3fb3;
--step:30px;--rail-ur:#9dbbe6;--rail-sr:#b9c3cf;--rail-sp:#d6dbe1;}
@media (prefers-color-scheme:dark){:root{--bg:#15181c;--card:#1e2227;--ink:#e6e9ee;--sub:#9aa4b1;
--line:#333a42;--ur:#22303f;--sr:#262b31;--before:#332b1c;--after:#1d2b1c;--accent:#7aa5ea;
--ok:#5dbb74;--warn:#e0a03a;--risk:#f08b83;--open:#c39ae6;
--rail-ur:#3f5a7d;--rail-sr:#414a55;--rail-sp:#39414a;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.65 -apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP",sans-serif;}
.wrap{max-width:1180px;margin:0 auto;padding:0 16px 80px}
header{background:var(--card);border-bottom:1px solid var(--line);padding-block:14px}
header .wrap{padding-bottom:0}
h1{font-size:18px;margin:0 0 4px}
.meta{color:var(--sub);font-size:12.5px}
.bar{position:sticky;top:0;z-index:20;background:var(--card);border-bottom:1px solid var(--line);
padding:8px 0;margin-bottom:14px}
.bar .row{max-width:1180px;margin:0 auto;padding:0 16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
input[type=search]{flex:1 1 220px;min-width:0;padding:7px 10px;border:1px solid var(--line);
border-radius:7px;background:var(--bg);color:var(--ink)}
.chip{border:1px solid var(--line);border-radius:999px;padding:4px 11px;cursor:pointer;
background:var(--bg);color:var(--sub);font-size:12.5px;user-select:none}
.chip[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:#fff}
button.act{border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:7px;
padding:6px 11px;cursor:pointer;font-size:12.5px}
button.act:hover{border-color:var(--accent)}
.cat{margin:26px 0 10px;font-size:13px;letter-spacing:.06em;color:var(--sub)}
details.ur{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:12px;
overflow:hidden}
details.ur>summary{background:var(--ur);padding:11px 14px;cursor:pointer;font-weight:700;
display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸";color:var(--sub);font-weight:400;margin-right:2px}
details[open]>summary::before{content:"▾"}
.id{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;color:var(--accent)}
.body{padding:12px 16px 16px calc(var(--step) - 3px);border-left:3px solid var(--rail-ur)}
.kv{color:var(--sub);font-size:13px;margin:2px 0}
.kv b{color:var(--ink);font-weight:600}
.grp{margin:16px 0 6px;font-size:12.5px;color:var(--sub);font-weight:600}
.grp::before{content:"";display:inline-block;width:calc(var(--step) - 16px);height:1px;
background:var(--rail-sr);vertical-align:middle;margin-right:7px}
.grp.lv2{margin-left:var(--step)}
details.sr{border:1px solid var(--line);border-radius:8px;margin:8px 0 14px var(--step);
background:var(--card);border-left:3px solid var(--rail-sr)}
details.sr>summary{background:var(--sr);padding:9px 12px;cursor:pointer;font-weight:600;
display:flex;gap:9px;align-items:baseline;flex-wrap:wrap;list-style:none}
details.sr>.kv{padding:10px 12px 0 var(--step)}
.sp{border:1px solid var(--line);border-radius:8px;margin:10px 12px 10px var(--step);
background:var(--card);border-left:3px solid var(--rail-sp)}
.sp>.head{display:flex;gap:9px;align-items:baseline;flex-wrap:wrap;padding:9px 12px;
border-bottom:1px solid var(--line)}
.ba{display:grid;grid-template-columns:1fr;gap:1px;background:var(--line)}
.ba>div{padding:9px 12px}
.ba .b{background:var(--before)}
.ba .a{background:var(--after)}
.ba .lab{font-size:11.5px;color:var(--sub);display:block;margin-bottom:2px;letter-spacing:.04em}
.ba .arrow{background:var(--card);color:var(--sub);text-align:center;padding:0;
line-height:1;font-size:13px;padding-block:1px}
.sp .extra{padding:8px 12px;font-size:13px;color:var(--sub);border-top:1px solid var(--line)}
.st{font-size:11.5px;padding:2px 9px;border-radius:999px;white-space:nowrap;font-weight:600}
.st.ok{background:color-mix(in srgb,var(--ok) 16%,transparent);color:var(--ok)}
.st.chk{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.st.risk{background:color-mix(in srgb,var(--risk) 16%,transparent);color:var(--risk)}
.st.open{background:color-mix(in srgb,var(--open) 16%,transparent);color:var(--open)}
.cmt{border-top:1px dashed var(--line);padding:8px 12px;display:flex;gap:8px;align-items:flex-start;
flex-wrap:wrap}
.cmt select{padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}
.cmt textarea{flex:1 1 320px;min-width:0;min-height:34px;padding:6px 9px;border:1px solid var(--line);
border-radius:6px;background:var(--bg);color:var(--ink);font:inherit;resize:vertical}
.cmt.has{background:color-mix(in srgb,var(--accent) 7%,transparent)}
.count{color:var(--sub);font-weight:400;font-size:12.5px}
.hidden{display:none!important}
.toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:var(--accent);
color:#fff;padding:9px 16px;border-radius:8px;font-size:13px;opacity:0;transition:.2s;pointer-events:none}
.toast.show{opacity:1}
@media print{.bar,.cmt select,button.act{display:none}details{page-break-inside:avoid}
details>summary{list-style:none}.sp{page-break-inside:avoid}}
@media (max-width:820px){:root{--step:16px}}
@media (max-width:640px){:root{--step:10px}}
"""

JS = r"""
const $=s=>document.querySelectorAll(s);
const KEY='crs-review:'+document.body.dataset.cr;
let active=new Set();
function apply(){
  const q=document.getElementById('q').value.trim().toLowerCase();
  document.querySelectorAll('.sp').forEach(sp=>{
    const okS=active.size===0||active.has(sp.dataset.status);
    const okQ=!q||sp.innerText.toLowerCase().includes(q);
    sp.classList.toggle('hidden',!(okS&&okQ));
  });
  document.querySelectorAll('.grp[data-grp]').forEach(g=>{
    let n=0;
    for(let el=g.nextElementSibling;el&&!el.matches('.grp');el=el.nextElementSibling)
      if(el.matches('.sp')&&!el.classList.contains('hidden'))n++;
    g.classList.toggle('hidden',n===0);
  });
  document.querySelectorAll('details.sr').forEach(sr=>{
    const n=sr.querySelectorAll('.sp:not(.hidden)').length;
    sr.classList.toggle('hidden',n===0);
    if(n>0&&(q||active.size))sr.open=true;
    const c=sr.querySelector('summary .count');
    if(c)c.textContent=(n===+c.dataset.total?'SP '+n+'件':'SP '+n+'/'+c.dataset.total+'件');
  });
  document.querySelectorAll('details.ur').forEach(ur=>{
    const n=ur.querySelectorAll('.sp:not(.hidden)').length;
    ur.classList.toggle('hidden',n===0);
    if(n>0&&(q||active.size))ur.open=true;
    const c=ur.querySelector('summary .count');
    if(c)c.textContent=(n===+c.dataset.total?'SP '+n+'件':'SP '+n+'/'+c.dataset.total+'件');
  });
}
$('.chip').forEach(c=>c.onclick=()=>{
  const s=c.dataset.status,on=c.getAttribute('aria-pressed')==='true';
  c.setAttribute('aria-pressed',!on); on?active.delete(s):active.add(s); apply();
});
document.getElementById('q').oninput=apply;
document.getElementById('expand').onclick=()=>$('details').forEach(d=>d.open=true);
document.getElementById('collapse').onclick=()=>$('details.sr,details.ur').forEach(d=>d.open=false);

function load(){try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){return{}}}
function save(o){try{localStorage.setItem(KEY,JSON.stringify(o))}catch(e){}}
const store=load();
$('.cmt').forEach(box=>{
  const id=box.dataset.sp,rec=store[id]||{};
  const sel=box.querySelector('select'),ta=box.querySelector('textarea');
  if(rec.sev)sel.value=rec.sev; if(rec.text)ta.value=rec.text;
  const mark=()=>box.classList.toggle('has',!!ta.value.trim());
  mark();
  const upd=()=>{store[id]={sev:sel.value,text:ta.value};save(store);mark();
    document.getElementById('n').textContent=Object.values(store).filter(r=>(r.text||'').trim()).length;};
  sel.onchange=upd; ta.oninput=upd;
});
document.getElementById('n').textContent=Object.values(store).filter(r=>(r.text||'').trim()).length;

// レビュー指摘の書き出し（/xddp-revise req が読む形式に合わせた6列: #／重要度／場所／指摘内容／対応内容／対応状況）
function buildMd(){
  const rows=[];
  document.querySelectorAll('.cmt').forEach(box=>{
    const id=box.dataset.sp,title=box.dataset.title,
          sev=box.querySelector('select').value,
          ta=box.querySelector('textarea').value.trim();
    if(!ta)return;  // コメント欄が空欄なら指摘テーブルには出力しない
    rows.push({id,title,sev:sev||'🟡 軽微',text:ta});
  });
  let md='## 2. 指摘事項と対応内容\n\n';
  md+='| # | 重要度 | 場所 | 指摘内容 | 対応内容 | 対応状況 |\n';
  md+='|---|---|---|---|---|---|\n';
  rows.forEach((r,i)=>{
    const loc=(r.id+' '+r.title).replace(/\|/g,'\\|');
    const text=r.text.replace(/\|/g,'\\|').replace(/\n/g,'<br>');
    md+='| '+(i+1)+' | '+r.sev+' | '+loc+' |  '+text+' |  | ⬜ 未対応 |\n';
  });
  return md;
}
function toast(t){const el=document.getElementById('toast');el.textContent=t;el.classList.add('show');
  setTimeout(()=>el.classList.remove('show'),1800);}
document.getElementById('copy').onclick=async()=>{
  try{await navigator.clipboard.writeText(buildMd());toast('指摘事項をコピーしました');}
  catch(e){toast('コピー失敗。ダウンロードを使ってください');}};
document.getElementById('dl').onclick=()=>{
  const b=new Blob([buildMd()],{type:'text/markdown'}),u=URL.createObjectURL(b),a=document.createElement('a');
  a.href=u;a.download='CRS-'+document.body.dataset.cr+'-human-review.md';a.click();URL.revokeObjectURL(u);
  toast('ダウンロードしました');};
document.getElementById('clr').onclick=()=>{
  if(!confirm('入力したレビューコメントをすべて消去します。よろしいですか？'))return;
  localStorage.removeItem(KEY);location.reload();};
"""

ST_CLASS = {'確定': 'ok', '🔍 要検討': 'chk', '⚠️ 懸念あり': 'risk', '❓ 未決': 'open'}


def _st(s):
    s = _norm_status(s)
    if not s:
        return ''
    return f'<span class="st {ST_CLASS.get(s, "")}">{e(s)}</span>'


def _sp_html(sp):
    st = _norm_status(sp.status)
    parts = [f'<div class="sp" id="{e(sp.sp_id)}" data-status="{e(st)}">',
             f'<div class="head"><span class="id">{e(sp.sp_id)}</span>'
             f'<span>{e(sp.title)}</span>{_st(st)}</div>']
    if sp.before or sp.after:
        parts.append('<div class="ba">'
                     f'<div class="b"><span class="lab">BEFORE</span>{e(sp.before) or "—"}</div>'
                     '<div class="arrow">↓</div>'
                     f'<div class="a"><span class="lab">AFTER</span>{e(sp.after) or "—"}</div>'
                     '</div>')
    elif sp.spec:
        parts.append(f'<div class="ba"><div class="a">'
                     f'<span class="lab">仕様</span>{e(sp.spec)}</div></div>')
    for label, val in (('理由', sp.reason), ('備考', sp.biko), ('懸念・検討事項', sp.kenen)):
        if val:
            parts.append(f'<div class="extra"><b>{label}：</b>{e(val)}</div>')
    parts.append(f'<div class="cmt" data-sp="{e(sp.sp_id)}" data-title="{e(sp.title)}">'
                 '<select><option value="">重要度…</option>'
                 '<option>🔴 重大</option><option>🟡 軽微</option><option>🔵 提案</option></select>'
                 '<textarea placeholder="レビュー指摘（空欄なら出力されません）"></textarea></div>')
    parts.append('</div>')
    return '\n'.join(parts)


def render_html(data, meta, cr_name):
    counts = status_counts(data)
    total = sum(counts.values())
    total_ur = sum(len(cat.ur_list) for cat in data['categories'])

    chips = ''.join(
        f'<button class="chip" data-status="{e(k)}" aria-pressed="false">{e(k)} {counts[k]}</button>'
        for k in STATUS_ORDER if k in counts)

    o = []
    o.append(f'<title>CRS {e(cr_name)} レビュービュー</title>')
    o.append(f'<style>{CSS}</style>')
    o.append(f'<body data-cr="{e(cr_name)}">')
    o.append('<header><div class="wrap">'
             f'<h1>{e(meta.get("タイトル", cr_name))}</h1>'
             f'<div class="meta">{e(meta.get("文書番号", ""))}　版数 {e(meta.get("版数", ""))}　'
             f'作成日 {e(meta.get("作成日", ""))}　UR {total_ur}件／SP {total}件　'
             '<b>未反映の指摘 <span id="n">0</span>件</b></div>'
             '</div></header>')
    o.append('<div class="bar"><div class="row">'
             '<input type="search" id="q" placeholder="全文検索（ID・仕様・Before/After・懸念）">'
             f'{chips}'
             '<button class="act" id="expand">全展開</button>'
             '<button class="act" id="collapse">全折畳</button>'
             '<button class="act" id="copy">指摘をコピー</button>'
             '<button class="act" id="dl">指摘を.md出力</button>'
             '<button class="act" id="clr">指摘を消去</button>'
             '</div></div>')
    o.append('<div class="wrap">')

    for cat in data['categories']:
        o.append(f'<div class="cat" data-category="{e(cat.name)}">＜{e(cat.name)}＞</div>')
        for ur in cat.ur_list:
            nsp = len(ur.direct_sp_list) + sum(len(sr.sp_list) for sr in ur.sr_list)
            o.append('<details class="ur" open>')
            o.append(f'<summary id="{e(ur.ur_id)}"><span class="id">{e(ur.ur_id)}</span>'
                     f'<span>{e(ur.title)}</span>{_st(ur.status)}'
                     f'<span class="count" data-total="{nsp}">SP {nsp}件</span></summary><div class="body">')
            o.append(f'<div class="kv"><b>理由：</b>{e(ur.reason)}</div>')
            if ur.explanation:
                o.append(f'<div class="kv"><b>説明：</b>{e(ur.explanation)}</div>')
            if ur.kenen:
                o.append(f'<div class="kv"><b>懸念・検討事項：</b>{e(ur.kenen)}</div>')

            prev_spec_group = None
            for sp in ur.direct_sp_list:
                if sp.spec_group != prev_spec_group:
                    prev_spec_group = sp.spec_group
                    if prev_spec_group:
                        o.append(f'<div class="grp" data-grp="1">＜{e(prev_spec_group)}＞</div>')
                o.append(_sp_html(sp))

            prev_req_group = None
            for sr in ur.sr_list:
                if sr.req_group != prev_req_group:
                    prev_req_group = sr.req_group
                    axis = f'（{e(sr.axis)}）' if sr.axis else ''
                    if prev_req_group:
                        o.append(f'<div class="grp" data-req-group="{e(prev_req_group)}">'
                                 f'＜{e(prev_req_group)}＞{axis}</div>')
                o.append('<details class="sr" open>')
                o.append(f'<summary id="{e(sr.sr_id)}"><span class="id">{e(sr.sr_id)}</span>'
                         f'<span>{e(sr.title)}</span>{_st(sr.status)}'
                         f'<span class="count" data-total="{len(sr.sp_list)}">SP {len(sr.sp_list)}件</span></summary>')
                o.append(f'<div class="kv"><b>理由：</b>{e(sr.reason)}</div>')
                if sr.kenen:
                    o.append(f'<div class="kv"><b>懸念・検討事項：</b>{e(sr.kenen)}</div>')
                prev_spec_group = None
                for sp in sr.sp_list:
                    if sp.spec_group != prev_spec_group:
                        prev_spec_group = sp.spec_group
                        if prev_spec_group:
                            o.append(f'<div class="grp lv2" data-grp="1">＜{e(prev_spec_group)}＞</div>')
                    o.append(_sp_html(sp))
                o.append('</details>')
            o.append('</div></details>')

    o.append('</div><div class="toast" id="toast"></div>')
    o.append(f'<script>{JS}</script>')
    return '\n'.join(o)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('md')
    ap.add_argument('--format', choices=['html', 'tree'], default='html')
    ap.add_argument('--out')
    ap.add_argument('--status', help='tree のみ: カンマ区切りで SP を絞り込む（例: "🔍 要検討,❓ 未決"）')
    ap.add_argument('--no-color', action='store_true')
    a = ap.parse_args()

    data = parse_crs_md(a.md)
    meta = _extract_meta(a.md)
    cr_name = meta.get('対象CR') or re.sub(r'^CRS-', '', Path(a.md).stem)

    if a.format == 'tree':
        only = set(s.strip() for s in a.status.split(',')) if a.status else None
        text = render_tree(data, meta, color=not a.no_color and (a.out is None), only_status=only)
    else:
        text = render_html(data, meta, cr_name)

    if a.out:
        Path(a.out).write_text(text, encoding='utf-8')
        print(f'wrote {a.out} ({len(text)} bytes)')
    else:
        sys.stdout.write(text + '\n')


if __name__ == '__main__':
    main()
