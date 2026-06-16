# Utility Toolkit Overhaul — Design

**Date:** 2026-06-16
**Status:** Approved-pending-review

## Goal

Refactor the existing Windows CLI utility suite for cross-platform readiness (Windows now,
Linux/macOS later), eliminate the heavy duplication between the project-context tools, modernize
the dated embedded LLM prompts, retire the Fortnite-specific tooling, and add five new tools:
`check-port`, `stop-port`, `ports`, `connect-server`, and `extract`.

Language stays **Python 3** specifically to keep one codebase portable to Linux/macOS later.
The tools that need PowerShell-only behavior (port lookups on Windows) shell out to PowerShell
via `subprocess`; they do **not** spawn separate windows. Output stays inline regardless of
whether the tool is invoked from `cmd`, PowerShell, or a future Unix terminal.

## Constraints & Context

- `source/` is on the user's Windows `PATH`. Each tool is a `<name>.py` + thin `<name>.bat`
  launcher (`python "%~dp0<name>.py" %*`). Command names must stay stable (muscle memory).
- The suite must remain runnable from both `cmd` and PowerShell.
- Cross-platform is a stated future goal: avoid Windows-only Python idioms where a portable one
  exists; isolate the unavoidable Windows-specific parts behind a platform check.
- Clipboard via `pyperclip` (already a dependency).

## Architecture

### Shared core (new)

Introduce a small shared package so the context tools stop copy-pasting ~40 lines each.

```
source/
  utilkit/                  # shared library, imported by the tools
    __init__.py
    config.py               # single source of truth for ignore rules + settings
    walk.py                 # project walking, tree rendering, binary detection, should_ignore
    collate.py              # XML <file> collation + prompt assembly
    clipboard.py            # copy/paste wrapper with one consistent pyperclip error path
    platform_ps.py          # run a PowerShell command portably (powershell.exe / pwsh), capture output
    ports.py                # port -> owning process lookup (PowerShell on Win, ss/lsof on Unix)
    prompts.py              # the modernized embedded LLM prompts, one place
    sessions.py             # connect-server JSON store (load/save/list/add/touch)
```

Every tool becomes a thin entry point that imports from `utilkit`. No tool re-declares ignore
sets or re-implements the directory walk.

### config.py — the one ignore/config file

Holds what is currently duplicated across `analyze-project`, `summarize-project`, `copy-files`,
and `project-structure`:

- `IGNORED_DIRECTORIES`, `IGNORED_EXTENSIONS`, `IGNORED_FILENAMES` (merged superset of today's
  lists; Fortnite/`.ignore` data removed).
- Config file location for `connect-server` sessions: `~/.config/utilkit/servers.json`
  (via `Path.home()`; works on all three OSes).
- Reads optional user overrides from `~/.config/utilkit/config.toml` if present (extra ignore
  entries), so the user can extend ignores without editing source. Falls back to defaults if absent.

## Components

### Context tools (kept as separate commands, shared engine)

| Command | Behavior after refactor |
| --- | --- |
| `analyze-project` | Tree + XML file collation + **analysis** system prompt → clipboard. |
| `summarize-project` | Tree + XML file collation + **generation/edit** system prompt → clipboard. |
| `generate-project` | Parse `<file>/<delete>/<rename>` from clipboard, apply to filesystem (unchanged behavior; refactored to use `utilkit` for safe-path + reporting). |
| `copy-files` | XML collation only (no tree), extension-filter prompt → clipboard. |
| `project-structure` | Tree only → clipboard (and stdout). |

All five call into `utilkit.walk` / `utilkit.collate` / `utilkit.prompts`. The only difference
between `analyze-project` and `summarize-project` becomes which prompt constant they pass in.

### Modernized prompts (`prompts.py`)

Rewrite the embedded prompts to drop the dated framing ("recalibrate", "world-class Principal
Engineer", "ALERT_RECALL_PROTOCOL", the all-caps override language). New prompts keep the genuinely
useful parts — the `<file path="...">` I/O contract and the full-file-output rule — in clean,
current phrasing. `get-format-prompt`, `get-programming-prompt`, `get-remember-prompt` keep their
command names but emit the modernized text.

### New tools

**`check-port <PORT>`** — read-only. Prints what is listening on the port: process name, PID,
state, and (where available) the command line. Exit 0 if found, 1 if nothing on that port. No kill.

**`stop-port <PORT>`** — action. Finds the owning process(es), terminates them, then **reports what
was killed** (name + PID + port). No pre-confirmation (per decision). Optional `--dry-run` maps to
`check-port`'s output. Handles multiple owners and "nothing listening" cleanly.

**`ports`** — lists *all* listening ports with owning process name + PID, sorted by port. Same
backend as `check-port`.

Backend (`utilkit/ports.py`): on Windows, call
`Get-NetTCPConnection -State Listen` + `Get-Process` via `platform_ps.py` and parse. On
Linux/macOS, use `ss -ltnp` / `lsof -iTCP -sTCP:LISTEN` (stubbed now, implemented when porting).
A single internal function returns `[{port, pid, process_name, state, cmdline}]`; the three tools
just format it.

**`connect-server [target]`** — SSH session manager.
- `connect-server user@host` (optionally `-p PORT`, `-i KEYFILE`): launches the system `ssh`
  client with those args, and on success records/updates the entry in `servers.json`
  (fields: `host`, `user`, `port`, `identity_file`, `label`, `last_used`). **No passwords ever
  stored** — auth is delegated to `ssh` (keys/agent/its own prompt).
- `connect-server` with no args: prints a numbered, most-recently-used-first list of saved servers;
  user types a number to reconnect. `ssh` replaces/!-execs as a child process so the interactive
  session works normally.
- Cheap extras if low-cost: `--list`, `--remove <n|label>`.

**`extract <archive>`** — universal unarchiver. Detects type by extension/magic and unpacks into a
folder named after the archive: `.zip` (zipfile), `.tar/.tar.gz/.tgz/.tar.bz2/.tar.xz` (tarfile),
`.gz` standalone (gzip). `.7z`/`.rar` → attempt via the `7z`/`unrar` binary if on PATH, else a clear
"install X" message. Pure stdlib for the common cases → cross-platform, no new deps. Guards against
path-traversal entries in archives (zip-slip).

### Retired

- `get-fortnite-prompt.py` + `.bat`, and the `fortnite_documentation.txt.ignore` /
  `fortnite_projects.txt.ignore` data files — removed from the toolkit.

### Bug fixes folded in

- `ls.py:119` — `target_path = sys.argv` → `sys.argv[1]` (currently passes the whole list).
- `sh.py` — remove unreachable code after `sys.exit` (lines ~168-170); fix the `len(sys.argv) < 2`
  branch ordering so a missing script is reported correctly.

## Data flow

```
context tool ──> utilkit.walk (respect config.py ignores) ──> utilkit.collate (XML)
            └──> utilkit.prompts (system prompt) ──> utilkit.clipboard.copy

port tool   ──> utilkit.ports.list_listening() ─(Windows)─> platform_ps.run("Get-NetTCPConnection…")
                                                └─(Unix)──> ss/lsof   ──> format ──> stdout

connect-server ──> utilkit.sessions (servers.json) ──> exec system `ssh`
extract        ──> stdlib zipfile/tarfile/gzip ──> ./<archive-name>/
```

## Error handling

- Clipboard failures: one consistent path in `utilkit.clipboard` — on copy failure for large
  payloads, print to stdout and exit non-zero (preserves current behavior).
- `check-port`/`ports` with nothing found: friendly message, exit 1 (check) / 0 (ports list empty).
- `stop-port`: if PowerShell/permission denies the kill, report the failure per-PID, exit non-zero.
- `connect-server`: missing `ssh` binary → clear install hint; bad/missing `servers.json` →
  start fresh, never crash.
- `extract`: unknown type or missing helper binary → explicit message naming what to install;
  reject archive members with absolute or `..` paths.

## Testing

- Unit tests under `tests/` for the pure logic that doesn't need a live system:
  `walk.should_ignore`, collation XML shape, `extract` path-traversal rejection (build a temp zip),
  `sessions` load/save/list round-trip, ports-output **parser** (feed it captured sample text).
- Manual/once: `check-port`, `stop-port`, `ports` against a real listening port; `connect-server`
  against a reachable host.
- Existing `tests/` sample project (config/, drawing/, gui) is reused as fixture input for the
  context tools.

## Out of scope (future ideas, captured so we don't lose them)

`serve`/`run` (managed dev server registry), `mkcd`, standalone `tree` command, `gclone`,
encrypted-password storage for `connect-server`, real Linux/macOS implementations of the port
backend (stubbed now), packaging as standalone executables.

## Migration / compatibility

- All current command names keep working. `.bat` launchers unchanged in form (`python … %*`); new
  tools get matching `.bat` launchers.
- `pyperclip` remains the only third-party dependency; everything else is stdlib.
- README updated to document the new tools and the new `utilkit` layout; `README_SH_RUNNER.md`
  left as-is.
