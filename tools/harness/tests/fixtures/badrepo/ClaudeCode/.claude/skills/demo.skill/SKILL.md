---
name: demo.skill
---

# demo.skill

## 検査A: apply 見出し

Read `~/.claude/skills/demo.common/SKILL.md`, apply "## Good Heading" with: X: 1
Read `~/.claude/skills/demo.common/SKILL.md`, apply "## Numbered Section" with: X: 2
Read `~/.claude/skills/demo.common/SKILL.md`, apply "## Missing Heading" with: X: 3

## 検査B: subagent

Use the **Agent tool** with `subagent_type=demo-good-agent` and pass:
```
CR_NUMBER: {CR}
OUTPUT_FILE: out.md
BOGUS_KEY: xxx
```

Use the **Agent tool** with `subagent_type=demo-missing-agent` and pass:
```
CR_NUMBER: {CR}
```

## 検査D: スクリプト結線

`PY=$(command -v python3) && "$PY" ~/.claude/skills/demo.tool/scripts/demo_tool.py run --path {P} --mode fast`
`demo_tool.py stat --path {P}`
`demo_tool.py bogus-sub --path {P}`
`demo_tool.py run --badflag x`
