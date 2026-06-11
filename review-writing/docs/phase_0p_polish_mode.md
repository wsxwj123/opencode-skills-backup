# Phase 0-P: Polish Mode

> **Prerequisites (Polish Mode entry path):**
> Complete **Phase 0.1–0.5** first (parameter collection → environment detection → project init).
> Phase 0-P begins *after* `outline.md` and `state.json` exist and scripts are copied.
> If resuming across sessions and `outline.md` already has `os:` field → skip environment detection.

## Step 0: Verify Parameters (already collected in Phase 0.1)

Phase 0.1 has already collected all parameters (title, journal, language, etc.) and Phase 0.5 has written them to `outline.md`.
**Do NOT re-ask parameters.** Read `outline.md` Parameters section and confirm it is complete.
If any field is missing (e.g., cross-session resume with a partial `outline.md`) → ask only the missing fields.

- If `outline.md` already exists and has `os:` field → skip environment detection (already done).  
- Otherwise → run Phase 0.2 Steps 0–3 (OS + Python version + Git + Zotero check) before continuing.
- **Format-specific dependency probes** (run only for the format the user is actually importing). Each probe is **machine-checked, then HALT-on-miss with explicit consent prompt** — never silently degrade:

  - `.docx` →
    ```bash
    python3 -c "import docx; print('✅ python-docx')" 2>/dev/null \
      || echo "❌ python-docx missing"
    ```
    If ❌ → **HALT.** Ask user:
    > "python-docx is not installed. Install it now (`pip install python-docx`)? (yes / no / convert externally)"
    - On `yes` → run `python3 -m pip install python-docx` → **MANDATORY re-probe** with the
      same one-liner above. If re-probe still shows ❌:
      - Check `which python3` matches pip's interpreter; force-match with
        `python3 -m pip install python-docx` (already shown above) rather than bare `pip`.
      - If still failing, suggest `python3 -m pip install --user python-docx` to bypass
        permission/venv issues.
      - Loop until ✅ OR user switches to `convert externally`.
    - On `no` / `convert externally` → ask user to save the document as .md (Word: File →
      Save As → Markdown / Plain text) and restart Step 1.

  - `.pdf` → run all three probes once, collect the available set.

    **Cross-platform invocation** (pick the one that matches your shell):
    ```bash
    # Mac/Linux/WSL bash/zsh — heredoc directly to python3:
python3 << 'PYEOF'
import shutil, subprocess, sys
results = {}
for mod in ['pdfplumber', 'pypdf']:
    r = subprocess.run([sys.executable, '-c', f'import {mod}'],
                       capture_output=True)
    results[mod] = (r.returncode == 0)
results['pdftotext'] = bool(shutil.which('pdftotext'))
available = [k for k, v in results.items() if v]
missing   = [k for k, v in results.items() if not v]
print('AVAILABLE:', available if available else 'NONE')
print('MISSING:', missing)
sys.exit(0 if available else 2)  # exit 2 = nothing available
PYEOF
    ```
    ```powershell
    # Windows PowerShell — here-string + Out-File. NOTE: probe runs BEFORE Phase 0.5
    # creates tmp/, so write the probe file to CWD instead of tmp\:
    @'
    import shutil, subprocess, sys
    results = {}
    for mod in ['pdfplumber', 'pypdf']:
        r = subprocess.run([sys.executable, '-c', f'import {mod}'], capture_output=True)
        results[mod] = (r.returncode == 0)
    results['pdftotext'] = bool(shutil.which('pdftotext'))
    available = [k for k, v in results.items() if v]
    missing   = [k for k, v in results.items() if not v]
    print('AVAILABLE:', available if available else 'NONE')
    print('MISSING:', missing)
    sys.exit(0 if available else 2)
    '@ | Out-File -Encoding utf8 _probe.py
    python _probe.py
    Remove-Item _probe.py  # clean up
    # Read exit code: $LASTEXITCODE  (0 = at least one available; 2 = all missing)
    ```
    ```cmd
    REM Windows CMD — no heredoc/here-string; create the file IN CWD (tmp\ not yet
    REM created; Phase 0.5 will create it later):
    python -c "open('_probe.py','w',encoding='utf-8').write('import shutil,subprocess,sys\nresults={}\nfor mod in [\"pdfplumber\",\"pypdf\"]:\n    r=subprocess.run([sys.executable,\"-c\",f\"import {mod}\"],capture_output=True)\n    results[mod]=(r.returncode==0)\nresults[\"pdftotext\"]=bool(shutil.which(\"pdftotext\"))\navail=[k for k,v in results.items() if v]\nmiss=[k for k,v in results.items() if not v]\nprint(\"AVAILABLE:\",avail if avail else \"NONE\")\nprint(\"MISSING:\",miss)\nsys.exit(0 if avail else 2)\n')"
    python _probe.py
    del _probe.py
    REM Read exit code: %ERRORLEVEL%
    ```
    Decision rule:
    - **At least one ✅** → use the highest-priority available tool (pdfplumber > pypdf > pdftotext) for Step 1. Do NOT prompt the user — proceed silently.
    - **All ❌** → **HALT.** Show this exact menu to the user and wait for explicit choice:
      ```
      No PDF extractor found. Pick one to install:
        [1] pdfplumber  (recommended; handles academic multi-column layouts best)
             → pip install pdfplumber
        [2] pypdf       (lighter, faster, less accurate on complex layouts)
             → pip install pypdf
        [3] pdftotext   (CLI tool; best for plain-text PDFs)
             Mac:    brew install poppler
             Linux:  sudo apt install poppler-utils
             Windows: download poppler binaries → unzip → add bin/ to PATH
                     https://github.com/oschwartz10612/poppler-windows/releases
        [4] None — I'll convert the PDF to .docx/.md externally and retry
      Your choice? (1/2/3/4)
      ```
    - After the user picks 1/2/3:
      ```bash
      # Install whichever was chosen, then RE-RUN the probe block above to confirm.
      # Do NOT skip the re-probe — installation can silently fail (network, permissions,
      # wrong Python interpreter, binary not added to PATH).
      # If re-probe still shows AVAILABLE: NONE:
      #   - For pip installs: check `which python3` matches the interpreter used by pip;
      #     try `python3 -m pip install <pkg>` to force the same interpreter
      #   - For pdftotext: confirm the install path is in PATH.
      #       Mac/Linux/WSL: `command -v pdftotext` and `echo $PATH`
      #       Windows (PowerShell/CMD): `where pdftotext` and `echo %PATH%`
      #     If not found:
      #       Mac/Linux/WSL → `export PATH="<install-bin-dir>:$PATH"` for current session;
      #         persist by appending to `~/.zshrc` or `~/.bashrc` and `source` it.
      #       Windows → System Properties → Environment Variables → edit PATH → add the
      #         poppler `bin\` directory → **open a NEW terminal window** (PATH changes
      #         only apply to new processes) → re-run the probe.
      ```
    Only after the re-probe returns at least one ✅, advance to Step 1. Otherwise loop back to the menu (the user may pick option 4 to bail out).

Then run Phase 0.5 initialization (create folder structure + copy scripts), same as Write Mode.

## Step 1: Accept Draft

> **Placeholder convention:** `[FILE]` in the commands below = absolute or
> project-relative path to the user-provided draft (e.g. `~/Downloads/my_review.pdf`).
> AI MUST substitute it before executing. Path quoting must handle spaces — wrap with
> single quotes in bash/zsh, double quotes in PowerShell, or escape per shell rules.

```
Accepted formats (Step 0 has already validated the required tool is available):
  .md / .txt  → read directly into tmp/draft_import.md (UTF-8)
  .docx       → python3 -c "import docx; d=docx.Document('[FILE]'); open('tmp/draft_import.md','w',encoding='utf-8').write('\n'.join(p.text for p in d.paragraphs))"
  .pdf        → use the tool Step 0 confirmed available (preference: pdfplumber > pypdf > pdftotext):
               (a) pdfplumber:
python3 -c "
import pdfplumber
with pdfplumber.open('[FILE]') as pdf:
    txt = '\n\n'.join((p.extract_text() or '') for p in pdf.pages)
open('tmp/draft_import.md','w',encoding='utf-8').write(txt)
"
               (b) pypdf:
python3 -c "
from pypdf import PdfReader
txt = '\n\n'.join((p.extract_text() or '') for p in PdfReader('[FILE]').pages)
open('tmp/draft_import.md','w',encoding='utf-8').write(txt)
"
               (c) pdftotext:
                   pdftotext -layout -enc UTF-8 '[FILE]' tmp/draft_import.md
               ⚠️  PDF extraction usually LOSES heading hierarchy (markdown `#` markers
                   are not present in the source). Step 2 must use the fallback path
                   "no clear heading hierarchy → ask user to manually assign section IDs".
               ⚠️  Scanned PDFs (image-only) yield empty text — the post-extraction sanity
                   check below detects this (n < 200 chars → hard HALT with OCR guidance).
  pasted text → write to tmp/draft_import.md (UTF-8)
```

> **Why explicit `encoding='utf-8'`:** Python's default text mode encoding is platform-dependent
> (Mac/Linux: utf-8; Windows: cp1252). Without an explicit encoding, Chinese/Japanese reviews and
> Unicode-rich academic PDFs will either raise `UnicodeEncodeError` mid-write or produce mojibake
> in `tmp/draft_import.md`. Always pass `encoding='utf-8'` on every read/write touching the draft.

Save raw text as `tmp/draft_import.md`.

**Post-extraction sanity check (MANDATORY after .docx / .pdf extraction — fail-safe on missing file, hard HALT on suspicious length):**
```python
python3 -c "
import pathlib, sys
p = pathlib.Path('tmp/draft_import.md')
if not p.exists():
    sys.exit('❌ Extraction produced no output file. Check: (1) [FILE] path correct? (2) PDF password-protected or corrupt? (3) Run with the next probe tool in Step 0 priority order, or convert externally.')
text = p.read_text(encoding='utf-8', errors='replace')
n = len(text.strip())
print(f'Extracted {n} chars, {len(text.splitlines())} lines')
if n < 200:
    sys.exit('❌ Suspiciously short (<200 chars) — likely scanned PDF (image-only, no text layer) or extraction failure. Run OCR (ocrmypdf / Adobe Acrobat) or convert to .docx first, then retry Step 1.')
elif n < 2000:
    sys.exit('⚠️ HALT: only {} chars extracted — very short for a full review. Verify with user that this is the complete document before continuing to Step 2 (the user may have uploaded an abstract-only file or extraction may have dropped pages).'.format(n))
print('✅ Text length looks reasonable for a review draft — safe to proceed to Step 2.')
"
```
> **Hard HALT semantics:** non-zero exit from this check **blocks Step 2 entirely**. Do NOT proceed to atomic split if any branch above triggers — first resolve the underlying extraction problem with the user.

## Step 2: Atomic Split by Heading Hierarchy

> **⚠️ MANDATORY — do NOT write any file to `drafts/` until user explicitly confirms the proposed structure. This gate cannot be skipped.**

> **PDF-imported drafts:** PDF text extraction strips markdown markers, so the heading
> detection in Step 1 below will almost always come up empty for `.pdf` sources. **Skip
> directly to the fallback flow at the end of this section** (semantic boundary detection +
> user confirmation) rather than reporting "no sections found" and stalling. `.docx`
> imports preserve headings via paragraph styles ONLY if the original document used
> Word's heading-level styles — many do not, so the same fallback may also apply.

Execute in this exact order:

1. Detect heading structure in `tmp/draft_import.md`: `#` (H1) / `##` (H2) / `###` (H3).
   For PDF-extracted text where `#` markers are absent, treat ALL-CAPS lines, lines
   matching `^\d+(\.\d+)?\s+[A-Z]` (e.g. "2.1 Delivery Systems"), and short isolated
   lines followed by paragraph blocks as candidate section boundaries.
2. Build the proposed split map: heading text → zero-padded section filename (e.g., `## 2.1 Delivery Systems` → `section_02_01.md`)
3. **STOP. Show the user a confirmation table:**
   ```
   section_01_01.md  ←  ## 1.1 Introduction (820 words)
   section_02_01.md  ←  ## 2.1 Delivery Systems (310 words)
   section_03_01.md  ←  ## 3.1 Clinical Outcomes (0 words — missing)
   ...
   Confirm this split? (yes / adjust)
   ```
4. **Wait for explicit "yes" or adjustment instructions. Do not proceed until received.**
5. Only after confirmation: write each section to `drafts/section_XX_XX.md` (zero-padded, identical naming to Write Mode)
6. Rebuild `outline.md` Outline section from detected headings.
   > **Section ID is what matters, not heading depth.** `zotero_manager.py --init` parses
   > by ID pattern (`N.` → level 1; `N.M` → level 2) and accepts any `##` or deeper heading.
   > Either of these is acceptable:
   > ```markdown
   > ## 1. Introduction          ### 1. Introduction
   > ### 1.1 Background      OR  #### 1.1 Background
   > ```
   > **Do NOT** drop the numeric prefix (`## Introduction` is ignored — no ID = invisible to --init).

**Fallback (no clear heading hierarchy):** Display detected paragraph blocks with estimated boundaries → ask user to manually assign section IDs → write files only after user confirmation.

**Completion gate:** Step 2 is complete ONLY when `drafts/section_XX_XX.md` files physically exist on disk. If no files were written, do NOT advance to Step 3.

## Step 3: Diagnosis Report (per section — no external script needed)

Run `python3 scripts/word_counter.py --file drafts/section_XX_XX.md` for each section.  
Scan each file for banned words from the Anti-AI Writing Style section.  
Count inline `[N]` citation occurrences per 500 words.

Display:
```
Section     | Words (EN) | Citations/500w | AI-flags | Recommendation
1.1 Bg      |  820       |  3.2           | 0        | ✅ keep
2.1 Del Sys |  180       |  0.8           | 2        | ⚠️ polish
3.1 Clin    |  0         |  —             | —        | ❌ write from scratch
```

Classification:
- **keep** — EN ≥500w (CN ≥1,500 chars) AND citations ≥2/500w AND AI-flags = 0
- **polish** — below any one threshold but has substantial content
- **rewrite** — below two or more thresholds  
- **missing** — section absent or <50 words

## Step 4: User Priority Assignment (Hard Block)

Show the diagnosis table. Ask user to label each section: `rewrite / polish / keep`.  
Accept flexible responses: "rewrite 2.1 and 3.1, polish 1.1, keep the rest."  
**Do not proceed to Step 5 until every non-missing section has an explicit label.**

## Step 5: Citation Import (Review-Specific)

```
0. Detect citation style in the imported draft:
   - Numeric style: inline [N] (or [1,2] or [1-3]) + numbered reference list at end
   - Author-year style: inline (Smith et al., 2020) + bibliography at end
   - Mixed / none: treat as "no reference list" and skip to item 5

   ⚠️ Author-year style: inform user that inline citations must be converted to [N]
   format before atomic split files can be used. Two options:
     a) Ask user to convert manually and re-upload
     b) AI converts during Step 2 split: assign [N] numbers in document order,
        rewrite inline (Author, Year) → [N] in each atomic draft file,
        build a mapping table: N → (Author, Year, Title) for Step 5 import

1. Extract reference list from tmp/draft_import.md (numbered list or bibliography).
   Parse each entry into a JSON record with these fields:
     `global_id` (int, MUST equal the original [N] number — see step 2),
     `title` (str), `authors` (list[str]), `year` (int/str),
     `journal` (str, optional), `doi` (str, optional), `pmid` (str, optional)
   Write the resulting list of records to **`tmp/existing_refs.json`** — this filename is
   consumed by step 3 below and the optional escape-hatch `--add-batch` call. Example:
   ```json
   [
     {"global_id": 1, "title": "...", "authors": ["Smith J","Lee K"], "year": 2021, "doi": "10.1038/..."},
     {"global_id": 2, "title": "...", "authors": ["..."], "year": 2020, "pmid": "31234567"}
   ]
   ```

2. ⚠️ PRESERVE original [N] numbering as gid:N — do NOT renumber.
   Renumbering would break all inline citations in the split section files.
   (If author-year conversion was done in Step 2, the assigned [N] numbers are already final.)

3. Write extracted references to data/literature_index.json (ALL modes — this is the canonical store):
     ⚠️ Every record in `tmp/existing_refs.json` MUST have a `global_id` field set to its
        original [N] number from the imported draft. Without it, Phase 3 `--add-batch` will
        re-assign a fresh gid via `_next_gid`, breaking every inline `[N]` reference in the
        atomic split files. The inline Python below hard-blocks on missing gid and reports
        the offending indices so you can fix `tmp/existing_refs.json` before retrying.

python3 -c "
import json, pathlib, sys
# encoding='utf-8' is mandatory: Windows default cp1252 will UnicodeDecodeError on UTF-8 refs
refs = json.load(open('tmp/existing_refs.json', encoding='utf-8'))
missing_gid = [i for i, r in enumerate(refs) if not isinstance(r.get('global_id'), int) or r.get('global_id') <= 0]
if missing_gid:
  more = '...' if len(missing_gid) > 5 else ''
  sys.exit(f'❌ {len(missing_gid)} refs missing valid global_id (indices: {missing_gid[:5]}{more}). Fix tmp/existing_refs.json: every entry needs an integer global_id matching its original [N] in the draft.')
idx = pathlib.Path('data/literature_index.json')
exist = json.loads(idx.read_text(encoding='utf-8')) if idx.exists() else []
known_dois = {e.get('doi','').strip().lower() for e in exist if e.get('doi','')}
known_gids = {e.get('global_id') for e in exist if isinstance(e.get('global_id'), int)}
added = skipped_dup = skipped_gid_collision = 0
for ref in refs:
  doi = ref.get('doi','').strip().lower()
  if doi and doi in known_dois:
      skipped_dup += 1
      continue
  if ref['global_id'] in known_gids:
      _g = ref['global_id']
      print(f'⚠️  gid:{_g} already in index — skipping (use --dedup repair if intentional)')
      skipped_gid_collision += 1
      continue
  # Preserve original gid (DO NOT renumber); ensure related_sections is present (empty until mapping confirmed)
  ref.setdefault('related_sections', [])
  ref.setdefault('verified', False)
  exist.append(ref)
  known_gids.add(ref['global_id'])
  if doi: known_dois.add(doi)
  added += 1
idx.write_text(json.dumps(exist, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Imported {added} references (skipped {skipped_dup} duplicate DOI, {skipped_gid_collision} gid collision)')
"

   **Git Checkpoint:** `git add -A && git commit -m "[review] Phase 0-P: citations imported"`

   [Zotero] **Default: do NOT sync to Zotero yet.** Imported references stay in `data/literature_index.json`
            with original gid preserved. Zotero items will be created **per-section** as each pending section
            gets a confirmed mapping — `--add-batch` is called inside Phase 3 (rewrite/polish branch) with the
            real section ID, using the local index as the source of truth (3-branch upsert handles back-fill of
            `zotero_key` automatically; see `cmd_add_batch` branch ②).

            Run `--init` only if the project's Zotero collection tree does not yet exist.
            Use the machine-readable `--find-root-title` probe to avoid fragile text parsing:
              python3 scripts/zotero_manager.py --status --find-root-title "[TITLE]" \
                --lib-id LIB_ID --api-key API_KEY
              # exit 0 → root exists; stdout is the key (capture and reuse as ROOT_KEY)
              # exit 3 → no match; run --init to create the collection tree:
              #          python3 scripts/zotero_manager.py --init --title "[TITLE]" \
              #            --outline outline.md --lib-id LIB_ID --api-key API_KEY
              # exit 4 → ambiguous (multiple top-level collections with same name);
              #          ask the user to pick from the printed key list

            ⚠️ Do NOT create a fake "imported" subcollection. Do NOT call --add-batch with a placeholder section
            name. Section mapping happens during Phase 3 per-section work.

            **Opt-in escape hatch** — if the user explicitly wants imported refs visible in Zotero immediately
            (e.g. for manual triage in Zotero UI), only then call --add-batch against a real, already-confirmed
            section ID from the outline:
              python3 scripts/zotero_manager.py --add-batch \
                --section "<real-section-id>" --papers tmp/existing_refs.json \
                --root-key ROOT_KEY --index data/literature_index.json \
                --lib-id LIB_ID --api-key API_KEY

4. Run citation guard:
              python3 scripts/citation_guard.py \
                --index data/literature_index.json \
                --log data/citation_guard_report.json
   → Unverifiable entries: mark verified:false, add to manual_review_queue
   → Do NOT force-fix at this stage; user decides during rewrite

5. If no reference list found → skip, set "citations_imported": false in state.json.
   Phase 3 will prompt for Round 2 search to fill gaps.
```

## Step 6: Initialize State + Route to Revision

Overwrite `state.json` (Phase 0.5's placeholder is replaced wholesale here — this is the
first time Polish Mode has enough info to construct the full record):
```python
python3 -c "
import json, pathlib
state = {
  'mode': 'polish',
  'phase': 3,
  'completed_sections': [],            # populated with the 'keep' list from Step 4
  'pending_sections': {
    'rewrite':  [],                    # filled from Step 4 user priority assignment
    'polish':   [],
    'missing':  [],
  },
  'zotero_root_key': '',               # captured from --find-root-title (Step 5) or --init
  'citations_imported': True,          # set False if Step 5 found no reference list
}
# AI: fill the four list/string fields above with real values from Steps 4-5 BEFORE running this command.
pathlib.Path('state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
print('✅ state.json initialized for Polish Mode (phase=3)')
"
```

**Git Checkpoint:** `git add -A && git commit -m "[review] Phase 0-P: polish mode initialized"`

Routing after Step 6:
| Section type | Path |
|---|---|
| `missing` | Phase 3 handles internally: run Phase 2 Round 1 search for this section, then write from scratch (do NOT leave Phase 3 to go back to Phase 2) |
| `rewrite` | Phase 3 (Round 2 search optional) |
| `polish` | Phase 3 (skip search; revise existing atomic file) |
| `keep` | Skip entirely (already in completed_sections) |

All sections complete → Phase 4 (export + compile).
