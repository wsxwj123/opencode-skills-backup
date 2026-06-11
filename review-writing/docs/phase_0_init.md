# Phase 0 详细执行：环境检测 + 项目初始化

> 本文件是 SKILL.md Phase 0 的详细执行代码，**仅首次初始化时读取一次**。
> 跨会话 resume（state.json 已存在）时不需要读本文件。

---

## 0.2 Full Environment Check

Run all checks sequentially. Display ✅/❌ per item. All must be ✅ before proceeding.

**Step 0: Detect OS + Python version (always)**
```python
python3 -c "
import sys, platform
ver = sys.version_info
assert ver >= (3, 7), f'Python 3.7+ required — found {ver.major}.{ver.minor}. Upgrade at python.org'
print(f'✅ Python {ver.major}.{ver.minor}.{ver.micro}')
print(f'OS: {platform.system()}')  # Darwin | Linux | Windows
"
```
Record `os: Darwin/Linux/Windows` — written to `outline.md` later in Phase 0.5. All subsequent platform-specific commands branch on this value.
- Python < 3.7 → abort; guide user to upgrade (python.org / `brew install python` / `winget install Python.Python.3`)

**Step 1: Base dependencies (always)**
```bash
curl --version      # ❌ → system-level issue (Windows: curl available in PowerShell 5.1+)
```

**Step 2: Git availability (always — enables auto-checkpoint for rollback)**
```bash
git --version 2>/dev/null && echo "✅ git available" || echo "⚠️ git not found (auto-checkpoint disabled; no rollback)"
```
Record `git_available: true / false` — written to `outline.md` later in Phase 0.5.
Git not available → **not blocking** — all checkpoint operations silently skip. Recommend user install git for rollback capability.

**Step 3: Zotero (Zotero mode only)**
```python
# Desktop app installed? (cross-platform)
python3 -c "
import platform, pathlib, sys
s = platform.system()
paths = {
  'Darwin':  pathlib.Path('/Applications/Zotero.app'),
  'Linux':   pathlib.Path('/usr/bin/zotero'),
  'Windows': pathlib.Path(r'C:/Program Files/Zotero/Zotero.exe'),
}
p = paths.get(s)
print('✅ Zotero found' if p and p.exists() else f'❌ Zotero not found at {p}')
"

# PyZotero library
python3 -c "import pyzotero; print('✅')" 2>/dev/null || echo "❌ run: pip install pyzotero"
```

**Step 4: PubMed edirect (Medical/Bio discipline)**
```python
# edirect detection (cross-platform)
python3 -c "
import shutil, platform
if shutil.which('esearch'):
    print('✅ edirect found')
elif platform.system() == 'Windows':
    print('❌ edirect not available on native Windows')
    print('   Options: (1) install WSL then run edirect inside WSL bash')
    print('            (2) skip edirect → use paper-search MCP as primary tool')
else:
    print('❌ edirect not installed')
"
```
If missing (Mac/Linux — run in bash):
```bash
sh -c "$(curl -fsSL https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect/install-edirect.sh)"
source ~/.bashrc  # or ~/.zshrc
```
If missing (Windows) → install WSL (`wsl --install` in PowerShell as Admin), then install edirect inside WSL; or auto-fallback to paper-search MCP (write `search_fallback: paper-search-mcp` to outline.md).

**Step 5: Proxy + PubMed connectivity**
```bash
PUBMED_TEST="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=test"
DIRECT=$(curl -s --max-time 4 "$PUBMED_TEST" 2>/dev/null | grep -c "Count" || echo 0)
PROXY_PORT=""
if [ "$DIRECT" -eq 0 ]; then
  for port in 7897 7890 1080 8080 8888; do
    R=$(curl -s --proxy "http://127.0.0.1:$port" --max-time 4 "$PUBMED_TEST" 2>/dev/null | grep -c "Count" || echo 0)
    if [ "$R" -gt 0 ]; then PROXY_PORT=$port; break; fi
  done
fi
# → write to outline.md: pubmed_proxy: none / http://127.0.0.1:XXXX
# → if both fail: fallback to paper-search MCP, notify user
```

**Step 6: NCBI API Key (optional, improves rate limit)**
```bash
echo ${NCBI_API_KEY:-"not set (rate limit 3 req/s; recommended to set)"}
# To set: export NCBI_API_KEY=your_key >> ~/.bashrc
```

**Step 7: paper-search MCP availability**
```
Check if tool list includes search_pubmed / search_arxiv:
  ✅ → paper-search MCP available
  ❌ → PubMed CLI only; inform user they may optionally configure paper-search MCP
```

**Step 8: Required scripts exist (always — verify SKILL_DIR is correct first)**
```python
python3 -c "
import pathlib, sys
# SKILL_DIR common locations:
#   Claude Code:  ~/.claude/skills/review-writing/
#   Cursor:       ~/.cursor/skills/review-writing/  (or project .cursor/skills/)
#   Windsurf:     ~/.windsurf/skills/review-writing/
#   Other:        the directory from which this SKILL.md was loaded
skill_dir = pathlib.Path('[SKILL_DIR]')  # AI substitutes actual path
required = ['zotero_manager.py','export_bibtex.py',
            'matrix_manager.py','word_counter.py','citation_guard.py',
            'validate_citations.py','check_global_citation_sequence.py',
            'citation_utils.py','state_manager.py']  # keep aligned with Phase 0.5 REQUIRED_SCRIPTS
missing = [s for s in required if not (skill_dir/'scripts'/s).exists()]
if missing:
    print(f'❌ Missing scripts: {missing}')
    print(f'   Check SKILL_DIR is correct: {skill_dir}')
    sys.exit(1)
print(f'✅ All {len(required)} required scripts found in {skill_dir}/scripts/')
"
```
If any script is missing → abort; verify SKILL_DIR path or re-install the skill.

---

## 0.3 Zotero First-Time Setup (Zotero mode only)

Note: PyZotero uses **Zotero Web API** (cloud). Desktop app does NOT need to run during API operations — but install it for local sync of created items.

**Step-by-step guide (show this to user if they haven't done it before):**

```
① Register / log in
   → https://www.zotero.org/user/register  (if no account)
   → https://www.zotero.org/user/login

② Get your Library ID (numeric user ID)
   → https://www.zotero.org/settings
   → Scroll to the bottom of the page
   → Look for: "Your user ID for use in API calls is: [NUMBER]"
   → Copy that number — this is your lib_id

③ Create an API key
   → https://www.zotero.org/settings/keys
   → Click "Create new private key"
   → Key Description: e.g. "review-writing-skill"
   → Permissions — check ALL of the following:
       ✅ Allow library access
       ✅ Allow write access           ← required for creating items/collections
       ✅ Allow notes access           ← required for abstract child notes
       ✅ Allow file access            ← required for PDF attachments
   → Click "Save Key"
   → Copy the generated key immediately (shown only once)

④ Test connection
   python3 scripts/zotero_manager.py --status --lib-id [NUMBER] --api-key [KEY]
   Expected output: ✅ Connected to Zotero library ...

⑤ Security rules
   - Write lib_id to outline.md (safe, not secret)
   - NEVER write api_key to any file — ask user at each new session start
   - If 403 Forbidden error: re-ask user for api_key; re-run --status before continuing
```

If `--status` lists multiple libraries (personal + group), show the list and ask user which to use. Write chosen `lib_id` to `outline.md`.

---

## 0.5 Initialize Project Files

After all checks pass. All file operations use **Python** (cross-platform: Mac/Linux/Windows).

> **Cross-platform shell note:** the `python3 << 'PYEOF' ... PYEOF` block below uses bash
> heredoc syntax (works in bash/zsh/WSL). On native Windows PowerShell or CMD, save the
> body between `PYEOF` markers to `_init.py` and run `python _init.py` instead — same effect.
> The Python code itself is platform-agnostic; only the *how-you-invoke-it* differs.

> **⚠️ AI: resolve placeholders before executing.** Replace `[PROJECT_BASE]` and `[SKILL_DIR]` with actual paths:
>
> | Client | `[SKILL_DIR]` (Mac/Linux) | `[SKILL_DIR]` (Windows) |
> |--------|--------------------------|------------------------|
> | Claude Code | `~/.claude/skills/review-writing` | `C:\Users\<name>\.claude\skills\review-writing` |
> | Cursor | `~/.cursor/skills/review-writing` or project `.cursor/skills/review-writing` | `C:\Users\<name>\.cursor\skills\review-writing` |
> | Windsurf | `~/.windsurf/skills/review-writing` | `C:\Users\<name>\.windsurf\skills\review-writing` |
> | Other | Auto-detect (run one-liner below) | same |
>
**"Other" client — auto-detect SKILL_DIR** (run from anywhere; uses `zotero_manager.py` as a stable cross-mode marker):

```bash
python3 -c "
import pathlib
dirs = [pathlib.Path.home()/p for p in [
    '.claude/skills/review-writing',
    '.cursor/skills/review-writing',
    '.windsurf/skills/review-writing',
    '.config/opencode/skills/review-writing']]
found = next((str(d) for d in dirs if (d/'scripts'/'zotero_manager.py').exists()), None)
print(found if found else 'NOT FOUND — run: find ~ -name zotero_manager.py -path */review-writing/*')
"
```

> `[PROJECT_BASE]` = location confirmed in Phase 0.1 (default: current working directory = `pathlib.Path.cwd()`).

```python
# PROJECT_BASE = project location confirmed in Phase 0.1 (default: current working directory)
# SKILL_DIR    = directory containing this SKILL.md (see lookup table above)
#   Claude Code: ~/.claude/skills/review-writing/   (Mac/Linux)
#                C:\Users\<name>\.claude\skills\review-writing\  (Windows)
#   Cursor:      ~/.cursor/skills/review-writing/   (Mac/Linux)
#   Windsurf:    ~/.windsurf/skills/review-writing/ (Mac/Linux)
#   Other:       the directory from which this SKILL.md was loaded

python3 << 'PYEOF'
import os, shutil, pathlib, sys, subprocess

TITLE     = "[review title]"         # replace with actual title
BASE      = pathlib.Path("[PROJECT_BASE]").expanduser().resolve()  # or pathlib.Path.cwd()
SKILL_DIR = pathlib.Path("[SKILL_DIR]").expanduser().resolve()

proj = BASE / TITLE
for d in ["drafts", "exports", "scripts", "data", "tmp", "figures"]:
    (proj / d).mkdir(parents=True, exist_ok=True)

# Initialize figures index (needed by Phase 3 Step 3 in ALL modes)
fig_index = proj / "figures" / "figure_index.md"
if not fig_index.exists():
    fig_index.write_text("# Figure Index\n\n", encoding="utf-8")

# Whitelist: copy ONLY the scripts the SKILL.md workflow actively calls.
REQUIRED_SCRIPTS = [
    "zotero_manager.py",
    "export_bibtex.py",
    "matrix_manager.py",
    "word_counter.py",
    "citation_guard.py",
    "validate_citations.py",
    "check_global_citation_sequence.py",
    "citation_utils.py",
    "state_manager.py",  # used in Phase 2.5 None Mode (reindex subcommand only)
]
missing = []
for name in REQUIRED_SCRIPTS:
    src = SKILL_DIR / "scripts" / name
    if not src.exists():
        missing.append(name)
        continue
    shutil.copy(src, proj / "scripts" / name)
if missing:
    sys.exit(f"❌ Missing scripts in SKILL_DIR: {missing}. Verify SKILL_DIR={SKILL_DIR}")

print(f"✅ Project created at: {proj}")
print(f"   Copied {len(REQUIRED_SCRIPTS)} active scripts")

# Git auto-checkpoint init (skip if git not available)
if shutil.which('git'):
    subprocess.run(['git', 'init'], cwd=str(proj), check=True)
    gitignore = proj / '.gitignore'
    gitignore.write_text('.DS_Store\nThumbs.db\n__pycache__/\n*.pyc\nlogs/\n*.lock\n', encoding='utf-8')
    subprocess.run(['git', 'add', '-A'], cwd=str(proj), check=True)
    subprocess.run(['git', 'commit', '-m', '[review] Phase 0: project initialized'], cwd=str(proj), check=True)
    print('✅ Git repo initialized with initial commit')
else:
    print('ℹ️  Git not found — auto-checkpoint disabled (no rollback)')
PYEOF
```

> **⚠️ Working directory rule:** All commands in Phase 1–4 are run from inside `[PROJECT_BASE]/[TITLE]/`.
> After initialization: `os.chdir(proj)` in Python, or `cd "[PROJECT_BASE]/[TITLE]"` in shell.
>
> **Note:** Phase 0.5 only creates folder structure + copies scripts. Zotero collection tree (`--init`) is NOT run here — it runs in Phase 1 (Write Mode) or Phase 0-P Step 5 (Polish Mode).

Then write `state.json` + `outline.md` and commit (templates in SKILL.md Phase 0.5).
