# PROJECT_WORKFLOW.md

*Project 5 process conventions, extending Kota's Project 4 workflow with Phase 01 empirical lessons.*

**Author:** Kota
**Project:** Project 5 — Agriculture Risk Monitoring System (`agriculture-risk-monitoring-system`)
**Last updated:** 2026-07-10 (post-Phase 01 s09 closure)
**Antecedent:** `~/Portfolio/PROJECT_WORKFLOW.md` (Kota's Project 4 original, 2026-04-23) — the ancestor document; this file extends its conventions with Project 5–specific practice.
**Reader:** future Kota starting a Phase 02+ session; the AI pair-programming assistant in any Project 5 session.

---

## 0. Positioning of this document

Project 5 maintains its own PROJECT_WORKFLOW.md rather than sharing a single portfolio-wide file. The rationale is Master research-grade discipline: each project's workflow evolves with the lessons discovered during that project's execution, and pretending otherwise (via a single shared document) would collapse per-project epistemic context that is itself a portfolio signal.

Project 5 in particular inherits Kota's Project 4 workflow but adds:

- **Adaptive override examples** from Phase 01 (SILO evappan finding, ABARES per-typical-farm discovery, pyarrow first-use-rule violation).
- **First-use dependency rule** enforcement pattern (§8.2 below).
- **Master research-grade discipline scorecard** as a formal closure-audit tool (Appendix A).
- **Cross-source reconciliation conventions** for empirical findings that require scope revision (§4.3).

Every portfolio project maintains four canonical documents. They answer different questions and must not be conflated:

| Document | Question answered | Scope | Update pattern |
|---|---|---|---|
| **PROJECT_WORKFLOW.md** (this file) | *How* do I run **this** project? | Project 5 | Extended when project-specific lessons emerge |
| `portfolio_finalisation_playbook.md` (Portfolio parent folder) | *How* do I close **any** project at v1.0? | Portfolio-wide | Rare; new lesson from closure |
| `project_scope.md` (this project) | *What* is Project 5 doing? | Project 5 | Structural revision → new version |
| `PROJECT_LOG.md` (this project) | *What happened* in Project 5? | Project 5 | Append-only per decision |

**Guiding rule:** If it is a Project 5–specific process, it lives in this file. If it is a portfolio-wide closure ritual, it lives in `portfolio_finalisation_playbook.md`. If it is Project 5–specific substance, it lives in `project_scope.md`.

Conflicts resolve in the following order (highest authority first):

1. **This file** — for Project 5 **process** conventions.
2. `portfolio_finalisation_playbook.md` — for portfolio-wide **closure** conventions.
3. `docs/project_scope.md` — for Project 5–specific **substance**.
4. `PROJECT_LOG.md` — for **historical anchor** of past decisions.

Scope may override this file *for a specific step or phase* and must log the override; the override does not amend this file.

---

## 1. Phase and Step structure

### 1.1 Phase numbering

Phases are zero-padded, two-digit, and sequential: `phase00`, `phase01`, ..., `phase10`. Project 5 spans 11 phases (`phase00` through `phase10`). The phase plan is fixed at scope time and modified only through logged overrides.

Phase 00 was **Scope & Setup** (scope lock, environment lock, foundational utilities; completed 2026-05-12). Phase 10 is **Communication** (README polish, findings.md, methodology.md, v1.0 tag).

### 1.2 Step numbering within a phase

Steps within a phase are `sYY`, zero-padded, sequential: `s01`, `s02`, ..., `s09`. Each step:

- Has a single narrow goal that one working session can plan, execute, and log in one sitting.
- Produces a named artefact (a script, a data file, a notebook section, a documentation update).
- Ends with a PROJECT_LOG entry describing the decision + outcome.

Typical step count per phase in Project 5: 5–9 (Phase 01 executed s01 through s09).

### 1.3 Kickoff and closure steps within a phase

- **`s01`**: kickoff step. Sets up phase-specific scaffolding, agrees on step plan for the rest of the phase.
- **`sNN` (final step of each phase)**: closure ceremony. Consolidates deliverables, updates `PROJECT_LOG.md`, updates `data/raw/manifest.yaml` if applicable, updates `docs/methodology.md`, writes `docs/phase_summaries/phaseXX_summary.md`, then executes git operations (§9.2 below).

---

## 2. Chat session discipline

### 2.1 Fresh session start

Each new working session begins by reloading context. The recommended kickoff prompt pattern:

```
Phase XX — <phase title> kickoff.

Project: agriculture-risk-monitoring-system (Master research-grade portfolio).
Scope reference: docs/project_scope.md v<version> (updated YYYY-MM-DD).
Previous phase status: <COMPLETE/PARTIAL>, tag <vX.Y-phaseNN-complete>.
Previous phase summary: docs/phase_summaries/phaseNN_summary.md.

Phase XX goal: <single-sentence goal from scope>.
Phase XX exit criterion: <from scope §6.2>.

Please read (in this order):
  1. docs/project_scope.md § <phase-specific section>.
  2. docs/phase_summaries/phaseNN_summary.md § <handoff-task section>.
  3. data/raw/manifest.yaml (or equivalent context).
  4. PROJECT_LOG.md tail (last N entries).

Then propose Step 01 of Phase XX.
```

A worked example lives in the previous phase's summary file (e.g., `phase01_summary.md § 6`).

### 2.2 Handoff between chats

If a phase spans multiple chats (which is common for Phase 06+ analytical phases), each chat ends with:

1. A PROJECT_LOG entry summarising the step outcome.
2. An explicit "handoff to next session" note (which scripts exist, which artefacts are persisted, which step comes next).
3. If applicable, an updated `phaseXX_summary.md` draft.

The next chat session begins with the kickoff prompt from § 2.1 above, pointing at the summary the previous chat produced.

### 2.3 Chat scope discipline

One chat = one step (default). If a step is bigger than a single chat, split into sub-steps (`s08a`, `s08b`, ...). If a step is smaller than a chat, that is fine — do not combine unrelated steps into one chat for the sake of chat efficiency.

The reason: PROJECT_LOG entries are step-granular and should track chat-granular reasoning. Project 5 s08 (OpenWeather ingestion) was intentionally split (s08a for centroid computation approval, s08b/main-run for actual data acquisition, s09 for closure) precisely to keep chat-granular reasoning traceable.

### 2.4 Empirical verification before creation

**Lesson from Phase 01 s09 (twice):** before creating a new file (data manifest, workflow document, etc.), verify empirically whether an equivalent already exists — do not rely solely on memory or chat responses. Use `Get-ChildItem` (Windows) or `find` (Unix) with `-Recurse` across the Portfolio parent folder.

Two Project 5 Phase 01 s09 failures illustrate this rule:

- **manifest.yaml v0.5 first draft** (2026-07-10): initial draft used `document_version:` root-keyed structure inferred from memory; the actual file used `project:` root-keyed with `sources:` as list. Empirical file inspection would have caught the error immediately.
- **PROJECT_WORKFLOW.md initial creation** (2026-07-10): an initial WORKFLOW file was drafted after Kota noted no WORKFLOW existed; Portfolio parent folder in fact contained Kota's Project 4 WORKFLOW at `~/Portfolio/PROJECT_WORKFLOW.md`. This document is the reconciled version.

Both were corrected without data loss because the empirical inspection was performed *before* the wrong version overwrote the correct one. The rule for future work: **verify empirically before creating**, treat chat responses as one signal among many, and never let a memory-based reconstruction overwrite an unread file.

---

## 3. Naming conventions

### 3.1 Scripts

Step scripts in `scripts/`:

```
scripts/phaseXX_sYY_<verb_object>.py
```

Examples: `phase01_s04_ingest_silo.py`, `phase01_s08_ingest_openweather.py`, `phase02_s01_build_region_mapping.py`.

Zero-padded phase and step. `verb_object` in snake_case, imperative form ("build", "ingest", "compute", "aggregate", not "building" or "builder").

### 3.2 Notebooks

Phase-aligned notebooks in `notebooks/`:

```
notebooks/0X_<descriptive_title>.ipynb
```

Examples: `03_exploratory_analysis.ipynb`, `06_climate_yield_statistical.ipynb`.

One notebook per phase for phases producing analytical outputs (typically phases 03 onward). Phase 00–02 usually do not have notebooks (they produce scripts and data).

### 3.3 Modules

Reusable modules in `src/<subpackage>/`:

```
src/ingestion/<source>.py         # Phase 01 data acquisition
src/processing/<transform>.py     # Phase 02+ data transformations
src/indicators/<family>.py        # Phase 04 climate indicators
src/models/<method>.py            # Phase 05–08 analytical methods
src/viz/<component>.py            # Phase 03+ visualisation helpers
```

Module names in snake_case, singular where semantically singular (`aagis_regions.py` — plural because it handles many regions), lowercase.

### 3.4 Phase summaries

```
docs/phase_summaries/phaseXX_summary.md
```

Gitignored. Kickoff prompts drafted mid-phase may also live here as `phaseXX_kickoff_prompt.md`.

### 3.5 Outputs

Figures and tables have **descriptive filenames**, never `fig1.png` or `table_a.csv`:

```
outputs/figures/yield_distribution_by_region.png
outputs/tables/regional_climate_climatology_summary.csv
outputs/models/xgboost_wheat_v1.joblib
```

The filename should let a reader know what the artefact contains without opening it.

---

## 4. Documentation maintenance

### 4.1 PROJECT_LOG.md discipline

- **Append-only.** Never edit historical entries. Corrections are added as new entries pointing back to the entry being corrected.
- **Mid-file edits require a one-off script.** If mid-file editing is unavoidable (e.g., fixing a typo in a header), the edit is performed by a **short Python script that opens the file, modifies it, closes it**, then the script itself is deleted. Never hand-edit PROJECT_LOG.md, because that risks accidentally deleting entries.
- **Entry per material decision.** Every substantive decision (data-source change, method choice, adaptive override, empirical finding, dependency addition) gets its own entry.
- **Sensitive credentials never in cleartext.** API keys, tokens, passwords: mask with the pattern `<first-6-chars>…<last-4-chars>`. Example: `061dc7…9e58`.
- **Entry header format:** `## YYYY-MM-DD — Phase XX, Step YY: <descriptive title>`.

### 4.2 Adaptive override convention

When a step plan must change mid-execution, log the override as a **discrete PROJECT_LOG entry**:

- Reference the original plan.
- Give the empirical evidence that triggered the change.
- State the new plan.
- Note the consequence for downstream phases.

This is an explicit honesty signal in the audit trail, not a deviation to hide. Project 5 Phase 01 canonical examples:

- **s04 SILO evappan effective start = 1970** (not 1961). Retrieval attempts for 1961–1969 returned structurally sparse files; the SPEI computation window is bound accordingly downstream.
- **s06 ABARES per-typical-farm semantics** discovered via triangulation (656 t/farm × ~55,000 broadacre farms ≈ 36 Mt matches ABS national total). Yield remains valid; area and production require farm-count weighting for region totals.
- **s08 pyarrow first-use-rule violation** (corrected in-flight). The dependency was not in requirements.txt when the first Parquet write happened; the correction is documented as an explicit rule violation.
- **s08 HTTP 504 permanent skip → auto-recovery on 52-day-later resume**. Documented in both s08 initial and resume entries.

### 4.3 Scope revisions

Scope is versioned. Substantive revisions bump the version number:

- **Patch** (e.g., v5 → v5.1): correction of factual error, no scope change.
- **Minor** (e.g., v4 → v5): structural revision, added/removed section, reconciled empirical findings.
- **Major** (e.g., v5 → v6): framing pivot, phase plan restructure.

Do not accumulate multiple substantive changes as patches — a patch that grows is a minor. Project 5's v4 → v5 (Post-Phase 01 empirical reconciliation of 7 findings) is the canonical example of a minor revision.

Every scope revision:

- Preserves prior versions in an Appendix (usually Appendix C — Document History).
- Adds an entry to PROJECT_LOG describing what changed and why.
- Is announced in the phase summary for the phase that triggered it.

### 4.4 Methodology.md maintenance

`docs/methodology.md` is a **progressive** document:

- Created at the end of the first phase that has methodological decisions to record (Project 5: Phase 01 s09).
- Phase 01 sections populated; later phases have placeholder headers.
- Each phase's closure step appends its methodological decisions to the corresponding section.
- Polished at Phase 10 for public consumption.

The reason for progressive population: methodological rationale is best captured *while the decision is fresh*, not reconstructed at Phase 10 from memory.

### 4.5 Findings.md

Created at Phase 10 (final phase). Written as the **substantive narrative** of results. Not populated during phases 01–09.

### 4.6 README.md

Regenerated at each phase closure via `scripts/update_readme.py`. Content is derived from the scope + PROJECT_LOG tail + phase summaries.

Do not hand-edit the README between regenerations. If the update_readme script does not produce what is needed, the fix is to improve the script.

---

## 5. `src/` promotion rule

A function or class migrates from `scripts/` to `src/<subpackage>/` when either of the following is true:

- It is called from **more than one script**.
- It is **non-trivial and likely reusable** (rule of thumb: > 20 lines with a clear generic purpose, likely to be called from a later phase).

The promotion is reviewed at each phase boundary. If a script accumulates functions that meet the criteria, promotion happens at the phase's closure step, not mid-phase.

**Anti-pattern to avoid**: leaving reusable logic in `scripts/` because "it works." Downstream phases will duplicate rather than import. Detect via the phase-boundary review.

Documented example from Project 5 Phase 01 → Phase 02:

- `src/processing/region_aggregation.py` — promoted from planned Phase 02 work; will contain AAGIS 3-digit code ↔ FDP text name mapping.
- `src/processing/abares_aggregation.py` — promoted from planned Phase 02 work; will contain farm-count weighting utilities.

---

## 6. Bilingual policy

Project 5 spans English (deliverables, code) and Japanese (working conversation).

| Artefact class | Language |
|---|---|
| Code files, comments, variable names, docstrings | English |
| Commit messages, branch names, git tags | English |
| File names, directory names | English |
| README, `findings.md`, `methodology.md`, `docs/project_scope.md`, `PROJECT_LOG.md`, this file | English |
| Working conversation | Japanese by default |
| Bilingual portfolio-facing summaries (LinkedIn, resume) | EN + JP versions where helpful |

**Rationale:** All artefacts a hiring manager or research reviewer might read are in English. Conversation is in the language Kota thinks fastest in.

Do not mix languages within a single artefact. A Japanese comment inside an English source file, or a Japanese heading inside an English README, breaks the language discipline and looks amateurish to reviewers.

---

## 7. Git workflow

### 7.1 Branch per phase

Every phase is developed on its own branch:

```
phase-00-scope
phase-01-data-acquisition
phase-02-quality-and-crossvalidation
...
phase-10-communication
```

- Branch name format: `phase-XX-<short-topic>` (lowercase, hyphens, descriptive).
- The branch is created from `main` at the start of the phase and merged back at the phase's closure step.

### 7.2 Commit format on phase branches

Two accepted formats:

- **Per-step:** `[Phase XX - Step YY] <imperative verb phrase>`.
- **Consolidated (interim or closure):** `[Phase XX s01-sNN] <summary>`.

Examples:

- `[Phase 01 - Step 04] Ingest SILO gridded climate with cropping mask`.
- `[Phase 01 s01-s07] Data acquisition modules and ingestion scripts (interim snapshot)`.
- `[Phase 01 s09] Closure ceremony: scope v5, manifest, PROJECT_LOG, methodology skeleton, s08 modules (Phase 01 complete)`.

Commit messages are imperative present tense ("Ingest SILO..." not "Ingested SILO..." or "Ingesting SILO...").

### 7.3 Merge to main with `--no-ff`

Phase branches merge to `main` with `--no-ff`:

```
git merge --no-ff phase-XX-<title> -m "Merge phase-XX-<title>: Phase XX complete (<one-line summary>)"
```

`--no-ff` preserves per-phase branch structure in `main`'s history. `git log --oneline --decorate --graph` will show the per-phase development structure, which is a portfolio signal of disciplined development. Without `--no-ff`, branches collapse into linear history and per-phase organisation becomes invisible.

### 7.4 Annotated tags at phase closure

Each phase closure adds an **annotated** tag on the merge commit:

```
git tag -a vX.Y-phaseNN-complete -m "Phase NN complete (YYYY-MM-DD): <substantive summary>"
```

Version pattern:

- `v0.Y-phaseNN-complete`: intermediate phase closures (Y = phase number).
- `v1.0`: final closure at Phase 10 (see `~/Portfolio/portfolio_finalisation_playbook.md`).

Annotated tags carry a message and appear in the GitHub Releases sidebar; lightweight tags do not and are inappropriate for portfolio-grade tagging.

### 7.5 Push discipline

- Push feature branch after each material commit (safety net against local disk failure).
- Push `main` + `--tags` at phase closure.
- Do not force-push to shared branches. If a rewrite is necessary, create a new branch and PR-merge.

### 7.6 Pre-commit hooks

All commits pass:

- `trim-trailing-whitespace`
- `end-of-file-fixer`
- `check-yaml`
- `check-added-large-files`
- `check-merge-conflicts`
- `black` (line-length 88)
- `ruff` (default rule set)

Hook failures are corrected and re-staged before the commit is finalised. Never bypass with `--no-verify` unless the hook itself is broken (in which case fix the hook).

---

## 8. Reproducibility discipline

### 8.1 Environment locking

- Python version locked in `.python-version` (`3.12`).
- Virtual environment at `.venv/` (pip + venv).
- `requirements.txt` **manually composed**, grouped by purpose with comments, `>=` constraints during phases 01–09.
- `requirements-dev.txt` for dev-only tools.
- Never generate `requirements.txt` via `pip freeze` — this pulls in irrelevant dependencies (Project 4 lesson 1).

### 8.2 First-use dependency rule

Every new runtime library is added to `requirements.txt` **in the same commit** that first imports it. If a dependency is discovered mid-execution (e.g., a Parquet write crashes because `pyarrow` was not installed), the correction goes into a discrete commit whose message explicitly names it as a first-use-rule violation for audit.

Anti-pattern to avoid: developing against a library installed via `pip install <lib>` outside of `requirements.txt`, discovering months later that a fresh clone cannot reproduce the environment.

Project 5 Phase 01 additions: `openpyxl>=3.1` (s07 XLSX reading), `python-dotenv>=1.0` (s08 API key loading), `pyarrow>=15` (s08 Parquet persistence; discovered mid-execution, documented as first-use-rule violation).

### 8.3 Random seeds

Every script with a stochastic component uses:

```python
SEED = 42
```

as the project-wide seed. ML training uses `random_state=42`; bootstrap procedures use the same seed; CV splits are deterministic.

### 8.4 Atomic persistence

Data-writing modules use the **`.part` → final path atomic write-and-rename pattern**:

```python
tmp_path = final_path.with_suffix(final_path.suffix + ".part")
df.to_parquet(tmp_path)   # or nc, csv, gpkg, etc.
tmp_path.replace(final_path)
```

This prevents partial-file corruption on interruption. Every ingestion module in Project 5 uses this pattern.

### 8.5 Idempotent ingestion

Every ingestion module is idempotent: re-running skips already-completed items. Per-file, per-record, or per-year depending on the source. This makes resume-after-failure safe and cheap.

Example from Project 5 s08 (OpenWeather): 8h+ ingestion split across two sessions with a 52-day gap resumed cleanly because per-year Parquet files were already persisted and each date was checked before re-fetching.

### 8.6 Secrets management

- API keys, tokens, and credentials live only in `.env`, gitignored.
- `.env.example` (tracked) provides a template documenting required variables.
- `python-dotenv` loads `.env` in scripts that need credentials.
- Logs never print credentials in cleartext; always mask (§4.1).

### 8.7 Encoding and pandas-NA defaults

Per Project 4 lessons 8 and 9 (encoded in `src/io_utils.py`):

- All `pd.read_csv` calls use `keep_default_na=False` and explicit `na_values` for categorical / short columns.
- CSV reader tries `utf-8` → `cp1252` → `latin-1` in fallback.
- Source-specific NA strings (e.g., ABS `..`, `np`, `-`, `nil`) are added per source in the ingestion module.

---

## 9. Closure ceremony convention

Each phase ends with a **closure ceremony** as its final step (typically `sNN` where NN = 09 for a 9-step phase). See `~/Portfolio/portfolio_finalisation_playbook.md` §3 for the final-project version; the per-phase version differs only in tag name.

### 9.1 Closure ceremony deliverables

At each phase closure, produce:

1. **PROJECT_LOG entries** for every step of the phase (append).
2. **Phase summary** at `docs/phase_summaries/phaseXX_summary.md` (gitignored, for handoff to next phase).
3. **Manifest update** at `data/raw/manifest.yaml` if the phase acquired new data sources.
4. **Methodology.md progression**: populate the phase's section in `docs/methodology.md`.
5. **Scope revision** if the phase produced empirical findings that require it (see §4.3).
6. **README regeneration** via `scripts/update_readme.py`.

### 9.2 Closure ceremony git operations

Executed in strict order (each command's output verified before the next):

```bash
# 1. Stage all closure artefacts
git add <listed files>

# 2. Commit on phase branch
git commit -m "[Phase XX sYY] Closure ceremony: <phase deliverable summary>"

# 3. Push feature branch
git push origin phase-XX-<title>

# 4. Switch to main
git checkout main

# 5. Merge with --no-ff
git merge --no-ff phase-XX-<title> -m "Merge phase-XX-<title>: Phase XX complete (<summary>)"

# 6. Annotated tag on the merge commit
git tag -a vX.Y-phaseNN-complete -m "<substantive tag message>"

# 7. Push main + tags
git push origin main
git push origin --tags

# 8. Verify
git log --oneline --decorate --graph -10
git tag -l -n5
```

---

## 10. Knowledge management (session context)

At each phase boundary, the Knowledge section attached to the working session is refreshed. Project 5's Knowledge is intended to hold:

1. **This file** (`PROJECT_WORKFLOW.md`, Project 5 version).
2. `portfolio_finalisation_playbook.md` (copied or referenced from `~/Portfolio/`).
3. `docs/project_scope.md` (current version — Project 5 is at v5 as of 2026-07-09).
4. **The most recent phase summary** (rolling — replace previous phase's summary at each boundary, or keep both if scope evolution context is valuable).
5. `PROJECT_LOG.md` (current state) — practical addition beyond Kota's Project 4 convention because it provides the empirical-decision audit trail needed to reason about next-phase choices.
6. `docs/methodology.md` (skeleton, once created at Phase 01 s09).
7. `requirements.txt` (available libraries are considered when planning scripts).

Optional addition:

- `docs/findings.md` (once populated at Phase 10).

The Knowledge section has finite capacity. Do not attach files that are large and not directly informative for next-phase reasoning. Manifest files, data files, and generated artefacts are examples of files that stay out of Knowledge.

---

## 11. Cross-project reuse

**Per Kota's decision (2026-07-10):** each project maintains its own PROJECT_WORKFLOW.md rather than sharing a single portfolio-wide file. The pattern:

- Portfolio parent folder: `portfolio_finalisation_playbook.md` (shared verbatim across projects; closure ritual is invariant).
- Each project repo root: `PROJECT_WORKFLOW.md` (project-specific; inherits from prior projects but extends with new lessons).

When starting a new project (Project 6 onwards), the recommended flow:

1. Copy the current Project 5 `PROJECT_WORKFLOW.md` into the new project's repository root.
2. Update `§0` to reflect the new project's name and antecedent.
3. Reset `§1.1`, `§1.2` (phase / step numbering) to reflect the new project's phase plan.
4. Preserve `§4.2` adaptive-override examples from Project 5 as portfolio historical record; extend with new-project examples as they arise.
5. Update `Appendix B` document history with a new line noting the extension.

Rationale for per-project WORKFLOW: portfolio evolution is itself a signal. A single central file would hide that Kota's Project 4 workflow (2026-04-23) evolved into Project 5's Phase 01 empirical-lessons-integrated version. Preserving both files (Portfolio parent for Project 4 antecedent + Project 5 repo for the extension) documents Kota's research maturity over portfolio history.

The following files are **shared verbatim** across projects (not extended):

- `~/Portfolio/portfolio_finalisation_playbook.md` — closure ritual applies to every project unchanged.

The following files are **project-specific**, created anew per project and never shared:

- `docs/project_scope.md` (project-specific substance).
- `PROJECT_LOG.md` (project-specific chronology).
- Phase summaries (project-specific handoff).
- Ingestion scripts, notebooks, source modules (project-specific implementation).

---

## Appendix A — Master research-grade discipline scorecard

Used at each phase closure to audit compliance. All items should be ✓ before tagging the phase complete.

| Discipline | Item |
|---|---|
| Observed-vs-derived | Model outputs never substituted for observed ground truth; validation benchmarks kept out of training. |
| Empirical honesty | Findings that contradict prior scope reconciled into a scope revision, not hidden. |
| Adaptive overrides | Mid-execution plan changes logged as discrete PROJECT_LOG entries. |
| Empirical verification before creation | New documents / edits preceded by empirical file-existence and file-content checks; memory-based reconstruction never overwrites unread files (§ 2.4). |
| Reproducibility | Fresh clone can reproduce all outputs via documented scripts (data + API-key caveats acknowledged). |
| First-use dependency rule | Every runtime library added to `requirements.txt` in the same commit as its first import. |
| Idempotent atomic persistence | All data-writing modules resumable; `.part` → final rename pattern. |
| Manifest as source of truth | `data/raw/manifest.yaml` documents every source with provenance + quirks + license. |
| Scope discipline | Structural revisions produce a new version (not accumulated patches). |
| Git per-phase branching | `--no-ff` merge preserves branch structure. |
| Annotated tag with substance | Every phase closure tagged with a meaningful message. |
| Bilingual discipline | English artefacts, Japanese conversation, no mixing within an artefact. |

Project 5 Phase 01 closure audit (2026-07-09): all 12 items ✓.

---

## Appendix B — Document history

| Date | Change |
|---|---|
| 2026-04-23 | Kota's original `PROJECT_WORKFLOW.md` created during Project 4 (Education and Income Inequality cross-country panel analysis). Located at Portfolio parent folder `~/Portfolio/PROJECT_WORKFLOW.md`. Preserved as the ancestor document; Project 4's canonical process reference. |
| 2026-07-10 | **This file — Project 5 extension.** Extends Kota's Project 4 workflow with Phase 01 empirical lessons: adaptive-override examples (SILO evappan, ABARES per-typical-farm, pyarrow first-use-rule violation), empirical-verification-before-creation rule (§ 2.4, from two Phase 01 s09 failures), Master research-grade discipline scorecard (Appendix A). Located at Project 5 repo root `~/Portfolio/project/Project 5/agriculture-risk-monitoring-system/PROJECT_WORKFLOW.md`. Per Kota's decision, each project maintains its own WORKFLOW rather than sharing a single portfolio-wide file (see § 11). |

*End of PROJECT_WORKFLOW.md (Project 5 edition).*
