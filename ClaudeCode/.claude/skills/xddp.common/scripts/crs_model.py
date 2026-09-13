"""
crs_model.py — CRS（変更要求仕様書）Markdown 共通パーサ

`xddp.md2excel/scripts/crs_md2excel.py` と `xddp.crs-view/scripts/crs_view.py` が共有する
CRS Markdown パーサ。カテゴリ・要求グループ（分割軸含む）・仕様グループ・UR/SR の
懸念・検討事項・1階層パターン（UR→仕様グループ→SP、SR なし）を欠落なく保持する。

Expected CRS Markdown structure (USDM Canonical heading system — H1〜H6 のみ使用):
  ## 2. USDM 要求仕様
    ### ＜カテゴリ名＞                          (H3。機能要求／非機能要求)
      #### {CR}-UR-xxx タイトル                (H4。形式 B: CR 名前空間先頭)
        ##### ＜要求グループ名＞                (H5)
          - **分割軸：** ...                    (要求グループ見出し直後の子リスト)
          ###### {CR}-SR-xxx-yyy タイトル      (H6)
            **＜仕様グループ名＞**              (太字行)
            - **{CR}-SP-xxx-yyy.zzz**: タイトル (リスト項目。属性は2スペース子リスト)
              - **Before：** ...
              - **After：** ...
              - **懸念・検討事項：** ...
  ## 5. 未決事項          (Markdown table)
  ## 6. 気づき・提案メモ  (Markdown table)
  ## 付記A. スコープ外事項              (Markdown table, optional)
  ## 付記B. 前提条件・実装参考情報      (Markdown table, optional)
  ## 付記C. 関連する既存処理            (Markdown table, optional)
  ## 7. 変更履歴          (Markdown table)

1階層パターン（`03_change-req-spec-template.md`「階層パターンの使い分け」）では要求グループ（H5）・
SR（H6）を省略し、UR の直後に仕様グループ・SP が続く。この場合 SP は `URItem.direct_sp_list` に
格納される（`URItem.sr_list` には現れない）。
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class SPItem:
    sp_id: str
    title: str
    status: str = ""
    before: str = ""
    after: str = ""
    spec: str = ""  # DEVELOPMENT_MODE=new の単一「仕様：」記述（Before/After と排他）
    reason: str = ""
    biko: str = ""
    kenen: str = ""
    spec_group: str = ""  # 直近の仕様グループ名（太字行）


@dataclass
class SRItem:
    sr_id: str
    title: str
    status: str = ""
    reason: str = ""
    explanation: str = ""
    kenen: str = ""  # SR の懸念・検討事項
    req_group: str = ""  # 直近の要求グループ名（H5）
    axis: str = ""  # 要求グループの分割軸
    sp_list: List[SPItem] = field(default_factory=list)


@dataclass
class URItem:
    ur_id: str
    title: str
    status: str = ""
    reason: str = ""
    explanation: str = ""
    kenen: str = ""  # UR の懸念・検討事項
    sr_list: List[SRItem] = field(default_factory=list)
    direct_sp_list: List[SPItem] = field(default_factory=list)  # 1階層パターン用


@dataclass
class CategoryItem:
    name: str
    ur_list: List[URItem] = field(default_factory=list)


def _get_field(line, *markers):
    """Extract the value after '- **marker：** ' or '- **marker:** '. Returns None if not matched."""
    for marker in markers:
        for sep in ('：', ':'):
            m = re.match(rf'^\s*-\s+\*\*{re.escape(marker)}{sep}\*\*\s*(.*)', line)
            if m:
                return m.group(1).strip()
    return None


def _parse_table(lines):
    """Parse a Markdown table from a list of lines.
    Returns data rows (list of cell-string lists), skipping the header and separator rows.
    """
    rows = []
    phase = 'header'
    for line in lines:
        s = line.strip()
        if not s.startswith('|'):
            continue
        if phase == 'header':
            phase = 'sep'
            continue
        if phase == 'sep':
            phase = 'data'
            continue
        cols = [c.strip() for c in s.split('|')[1:-1]]
        if cols:
            rows.append(cols)
    return rows


def _extract_cr_name(md_path: str) -> str:
    """ファイル名（例: CRS-CR-2026-970.md）から CR 名を抽出する。判別できない場合は stem を返す。"""
    stem = Path(md_path).stem
    m = re.match(r'^CRS-(.+)$', stem)
    return m.group(1) if m else stem


def _register_ur(urs: List[URItem], cur_category: Optional[CategoryItem], ur: URItem,
                  md_path: str, line_no: int) -> None:
    """UR を後方互換フラットリストに追加し、カレントカテゴリの ur_list へネストする。
    カテゴリが未確定（H3 見出しが一度も出現していない）場合は fail-loud する
    （カテゴリに属さない UR が categories から静かに欠落したまま処理を継続しないための検査）。
    """
    urs.append(ur)
    if cur_category is None:
        cr_name = _extract_cr_name(md_path)
        label = ur.ur_id or ur.title
        raise ValueError(
            f"UR '{label}' has no parent category (H3 '### ＜…＞' heading) in {cr_name} "
            f"CRS Markdown ({md_path}), line {line_no}. Every UR must appear under a category "
            f"heading — fix the Markdown heading structure."
        )
    cur_category.ur_list.append(ur)


def parse_crs_md(md_path: str) -> dict:
    """CRS Markdown を読み込み、カテゴリ〜UR/SR/SP 階層と付記セクションを構造化して返す。

    Return dict keys:
      urs        : list[URItem]  — UR/SR/SP の3層ネスト構造（カテゴリ非依存の後方互換フラットビュー）
      categories : list[CategoryItem]  — カテゴリ配下に UR をネストした構造
      pending    : list[tuple]   — (no, title, content, deadline)
      notes      : list[tuple]   — (no, kind, content, policy)
      scope_out  : list[tuple]   — (no, target, reason, cr_text)
      impl_ref   : list[tuple]   — (no, kind, content, cr_text)
      exist_proc : list[tuple]   — (no, module_path, entry_point, behavior, req_id)
      history    : list[tuple]   — (版数, 日付, 変更者, 変更内容)
    """
    with open(md_path, encoding='utf-8') as f:
        lines = f.readlines()

    urs: List[URItem] = []
    categories: List[CategoryItem] = []
    pending = []
    notes = []
    scope_out = []
    impl_ref = []
    exist_proc = []
    history = []

    cur_category: Optional[CategoryItem] = None
    cur_ur: Optional[URItem] = None
    cur_sr: Optional[SRItem] = None
    cur_sp: Optional[SPItem] = None
    cur_req_group = ""
    cur_axis = ""
    cur_spec_group = ""
    section = None  # 'usdm' | 'pending' | 'notes' | 'scope_out' | 'impl_ref' | 'exist_proc' | 'history'

    i = 0
    while i < len(lines):
        stripped = lines[i].rstrip('\n')

        # ── Section heading detection (## level only) ──────────────────────
        if re.match(r'^## ', stripped):
            if re.match(r'^## 付記A\.', stripped):
                section = 'scope_out'
            elif re.match(r'^## 付記B\.', stripped):
                section = 'impl_ref'
            elif re.match(r'^## 付記C\.', stripped):
                section = 'exist_proc'
            elif '要求仕様' in stripped or re.match(r'^## 2\.', stripped):
                section = 'usdm'
            elif '未決' in stripped:
                section = 'pending'
            elif '気づき' in stripped or '提案メモ' in stripped:
                section = 'notes'
            elif '変更履歴' in stripped:
                section = 'history'
            else:
                section = None
            i += 1
            continue

        # ── USDM hierarchy parsing ─────────────────────────────────────────
        if section == 'usdm':
            # カテゴリ見出し (h3): ### ＜カテゴリ名＞
            m = re.match(r'^### ＜(.+)＞', stripped)
            if m:
                cur_category = CategoryItem(name=m.group(1).strip())
                categories.append(cur_category)
                cur_ur = None
                cur_sr = None
                cur_sp = None
                cur_req_group = ""
                cur_axis = ""
                cur_spec_group = ""
                i += 1
                continue

            # SP list item: - **SP-xxx-yyy.zzz**: タイトル
            # 属性 field 行（- **理由：** 等）と同じ `- **…**` 構文形のため、field 行の判定より
            # 先に評価する（cur_sp を検出するまで直前要素へ属性が誤帰属するのを防ぐ #26）。
            m = re.match(r'^\s*-\s+\*\*(\S+-SP-\d\S*)\*\*[：:]\s*(.*)', stripped)
            if m:
                cur_sp = SPItem(sp_id=m.group(1), title=m.group(2).strip(), spec_group=cur_spec_group)
                if cur_sr is not None:
                    cur_sr.sp_list.append(cur_sp)
                elif cur_ur is not None:
                    # 1階層パターン（UR→仕様グループ→SP、SR なし）。握りつぶさず UR 直下へ格納する。
                    cur_ur.direct_sp_list.append(cur_sp)
                i += 1
                continue

            # UR heading (h4): #### {CR}-UR-xxx タイトル（形式 B: CR 名前空間先頭）
            m = re.match(r'^#### (\S+-UR-\d\S*)\s+(.*)', stripped)
            if m:
                cur_ur = URItem(ur_id=m.group(1), title=m.group(2).strip())
                _register_ur(urs, cur_category, cur_ur, md_path, i + 1)
                cur_sr = None
                cur_sp = None
                cur_req_group = ""
                cur_axis = ""
                cur_spec_group = ""
                i += 1
                continue

            # 親URを持たないSRグループの開始（h4だがUR-prefixedでない見出し。USDMの例外パターン：
            # 「対象外の宣言」等、形式的な親URを持たずSRを直接記載するケース）。
            # cur_ur を「UR行を出力しないプレースホルダ」に切り替え、以降のSR見出しが
            # 直前の実在URに誤って収録されるのを防ぐ。
            m = re.match(r'^#### (.*)', stripped)
            if m:
                cur_ur = URItem(ur_id="", title=m.group(1).strip())
                _register_ur(urs, cur_category, cur_ur, md_path, i + 1)
                cur_sr = None
                cur_sp = None
                cur_req_group = ""
                cur_axis = ""
                cur_spec_group = ""
                i += 1
                continue

            # 要求グループ見出し (h5): ##### ＜要求グループ名＞
            m = re.match(r'^##### ＜(.+)＞', stripped)
            if m:
                cur_req_group = m.group(1).strip()
                cur_axis = ""
                cur_sr = None
                cur_sp = None
                cur_spec_group = ""
                i += 1
                continue

            # 括弧なしの要求グループ見出し（旧フォーマット・互換フォールバック）。
            # Excel には出力しない（プレースホルダUR化せずスキップする。#10 の回帰防止）ため
            # 名前は保持せずコンテキストのみリセットする。
            m = re.match(r'^##### ', stripped)
            if m:
                cur_req_group = ""
                cur_axis = ""
                cur_sr = None
                cur_sp = None
                cur_spec_group = ""
                i += 1
                continue

            # SR heading (h6): ###### {CR}-SR-xxx-yyy タイトル（形式 B: CR 名前空間先頭）
            m = re.match(r'^###### (\S+-SR-\d\S*)\s+(.*)', stripped)
            if m:
                cur_sr = SRItem(sr_id=m.group(1), title=m.group(2).strip(),
                                 req_group=cur_req_group, axis=cur_axis)
                if cur_ur is not None:
                    cur_ur.sr_list.append(cur_sr)
                cur_sp = None
                cur_spec_group = ""
                i += 1
                continue

            # 仕様グループの太字行: **＜仕様グループ名＞**（見出しではない。行頭が `- ` でない点で
            # field 行と区別できる）
            m = re.match(r'^\*\*＜(.+)＞\*\*\s*$', stripped)
            if m:
                cur_spec_group = m.group(1).strip()
                i += 1
                continue

            # 要求グループ直後の分割軸行。cur_sr が確定する前（要求グループ直下）にのみ現れる想定。
            axis_v = _get_field(stripped, '分割軸')
            if axis_v is not None:
                cur_axis = axis_v
                i += 1
                continue

            # Field lines
            if cur_sp is not None:
                for attr, markers in [
                    ('before',  ('Before',)),
                    ('after',   ('After',)),
                    ('spec',    ('仕様',)),
                    ('reason',  ('理由',)),
                    ('biko',    ('備考',)),
                    ('kenen',   ('懸念・検討事項',)),
                    ('status',  ('ステータス',)),
                ]:
                    v = _get_field(stripped, *markers)
                    if v is not None:
                        setattr(cur_sp, attr, v)
                        break
            elif cur_sr is not None:
                for attr, markers in [
                    ('reason',      ('理由',)),
                    ('explanation', ('説明',)),
                    ('kenen',       ('懸念・検討事項',)),
                    ('status',      ('ステータス',)),
                ]:
                    v = _get_field(stripped, *markers)
                    if v is not None:
                        setattr(cur_sr, attr, v)
                        break
            elif cur_ur is not None:
                for attr, markers in [
                    ('reason',      ('理由',)),
                    ('explanation', ('説明',)),
                    ('kenen',       ('懸念・検討事項',)),
                    ('status',      ('ステータス',)),
                ]:
                    v = _get_field(stripped, *markers)
                    if v is not None:
                        setattr(cur_ur, attr, v)
                        break

        # ── Table section parsing ──────────────────────────────────────────
        elif section in ('pending', 'notes', 'scope_out', 'impl_ref', 'exist_proc', 'history'):
            if stripped.strip().startswith('|'):
                # Collect all consecutive table lines
                j = i
                table_lines = []
                while j < len(lines) and lines[j].strip().startswith('|'):
                    table_lines.append(lines[j])
                    j += 1
                rows = _parse_table(table_lines)
                if section == 'pending':
                    for row in rows:
                        if len(row) >= 4:
                            pending.append((row[0], row[1], row[2], row[3]))
                elif section == 'notes':
                    for row in rows:
                        if len(row) >= 4:
                            notes.append((row[0], row[1], row[2], row[3]))
                elif section == 'scope_out':
                    for row in rows:
                        if len(row) >= 4:
                            scope_out.append((row[0], row[1], row[2], row[3]))
                elif section == 'impl_ref':
                    for row in rows:
                        if len(row) >= 4:
                            impl_ref.append((row[0], row[1], row[2], row[3]))
                elif section == 'exist_proc':
                    for row in rows:
                        if len(row) >= 5:
                            exist_proc.append((row[0], row[1], row[2], row[3], row[4]))
                elif section == 'history':
                    for row in rows:
                        if len(row) >= 4:
                            history.append((row[0], row[1], row[2], row[3]))
                i = j
                continue

        i += 1

    return {
        'urs':        urs,
        'categories': categories,
        'pending':    pending,
        'notes':      notes,
        'scope_out':  scope_out,
        'impl_ref':   impl_ref,
        'exist_proc': exist_proc,
        'history':    history,
    }
