# BITTU v2.0.0 — Enterprise Terminal AI Coding Agent

Ek **real, working** terminal AI agent jiska interface **bilkul Grok CLI jaisa** hai
(sirf "Grok" ki jagah **BITTU**), plus **Claude Code jaise slash `/commands`**.

Ye actually:
- 📖 files **read** karta hai
- ✏️ files **edit / write / append** karta hai
- 🖥️ **shell commands** chalata hai
- 🔍 codebase **search** karta hai (grep, find_files)
- 🌙 **Dream Mode** — bounded, resumable autonomous development with verification gates
- 🌐 **Real-time web search** — live public search, citations, page fetch और SSRF protection
- 📊 **Live telemetry** — input/output token usage, streamed estimates, latency, tool steps और web references

...ek **ReAct loop** me, OpenAI-compatible LLM (`mimo-v2.5-free` @ opencode zen) ke saath.

> ✅ **Locally verified** without requiring an API key:
> - `test_18features.py` → 19/19 feature checks plus TUI interaction checks
> - `test_advanced.py` → 10/10 advanced features
> - `test_dream.py` → 17/17 dream/goal/streaming checks
> - `test_effort.py` → 15/15 effort checks
> - `test_ledger.py` → 22/22 ledger checks
> - `test_palette.py` → grouped palette, hidden tool commands, live filtering, Tab/Esc checks
>
> `test_real.py` and the TUI live-edit path require a configured provider API key.

---

## 🆕 v2.1.0 — What's New

### 🌙 Dream Mode — Bounded Autonomous Development
- **1,000 bounded steps** per autonomous run, with **80 continuations** available across resumable runs
- **Stall detection** stops a run after 12 rounds without measurable progress
- **Safe autonomy** — long jobs remain resumable instead of running without a hard ceiling
- **All file types tracked** — `.py .json .md .yaml .toml .html .css` sab changes detect
- **Parallel preflight** — metrics + security + deps ek saath chalte hain (3x faster startup)
- **Cached fake-scan** — repeated codebase walks eliminate (60s TTL cache)

### 🛡️ Reliability & Security Hardening
- Path jail rejects `..` traversal and symlink escapes for file tools.
- Text writes are UTF-8, size-bounded, atomic, and preserve existing permissions.
- Shell and git output is bounded; destructive git/helper overrides are rejected.
- LLM cache is thread-safe, tool-aware, TTL-bound, and returns defensive copies.
- Provider requests validate URLs, cap retries/timeouts, and handle malformed responses.
- TUI mutating tools require approval by default, and worker threads shut down cleanly.
- Session saves report errors instead of silently dropping state.

### 🐛 Bug Fixes
- Streaming retry loop — fresh headers har retry par (stale headers bug fix)
- Context compression — consecutive user messages bug fix (model rejection fix)
- Work journal — tool name extraction fixed (name field se)
- Effort gates — ab saari Python files lint hoti hain, sirf pehli nahi
- Swarm — local `/tmp` workdir pe skip nahi hota, sirf real CI mein
- Verification plane — per-future timeout (60s) — infinite blocking fix
- TUI `_finish` — dream mode verification section display fix

### ✨ New Commands
- `/web <query>` — live public web search with numbered citations
- `/fetch <url>` — safely fetch a public page after SSRF validation
- `/cost` — live input/output tokens, estimates, requests, tools and latency
- `/stats` — LLM cache hit rate + token usage
- `/clear-cache` — LLM response cache clear karo

These technical commands remain available when explicitly typed, but they are intentionally **not shown in the default `/` palette**. The palette is reserved for controls that change the workspace or execution state: model, mode, workdir, effort, Dream/Goal modes, approvals, sessions, checkpoints, undo/redo, help, and settings.

### Natural-Language-First TUI
Type a normal request such as “find why the tests fail and verify the fix” or “research the current API and update this client.” BITTU's system policy allows the agent to choose real `web_search`, page fetch, file, shell, git, lint, and test tools when the task requires them; `/web` and `/fetch` are compatibility escape hatches, not prerequisites for research.

Typing `/` opens a grouped command palette. The list updates live as the prefix is typed, and `PgUp`/`PgDown` move the highlight, while `Enter` or `Tab` inserts the selected command and `Esc` closes the palette. Input/output tokens, live streamed estimates, request latency, current tool step, tool count, and web-reference count stay in the background telemetry strip rather than appearing as separate primary commands.

---

## 🚀 Quick Install

### Option 1: pip install (Recommended)
```bash
# Install directly from GitHub
pip install git+https://github.com/cmyolo441-coder/notworking.git

# Or clone and install
git clone https://github.com/cmyolo441-coder/notworking.git
cd notworking
pip install .
```

### Option 2: Build Binary (No Python needed after build)
```bash
git clone https://github.com/cmyolo441-coder/notworking.git
cd notworking
make build
# OR
./build.sh
# Binary will be in dist/bittu/
./dist/bittu/bittu
```

### Option 3: Quick Install Script
```bash
git clone https://github.com/cmyolo441-coder/notworking.git
cd notworking
./install.sh
```

### Option 4: Development Mode
```bash
git clone https://github.com/cmyolo441-coder/notworking.git
cd notworking
pip install -e .
```

### Option 5: Docker (Cloud Ready)
```bash
docker pull bittu:latest
docker run -it --rm bittu:latest

# Or with workspace mount
docker run -it --rm -v $(pwd)/workspace:/workspace bittu:latest

# Or build locally
git clone https://github.com/cmyolo441-coder/notworking.git
cd notworking
docker build -t bittu .
docker run -it --rm bittu
```

---

## 🔑 API Key Setup

### Option 1: Environment Variable (Recommended)
```bash
# Linux/Mac
export ZEDPY_API_KEY='your-api-key-here'

# Windows
set ZEDPY_API_KEY=your-api-key-here
```

### Option 2: Config File
```bash
mkdir -p ~/.config/zedpy
echo "your-api-key-here" > ~/.config/zedpy/api_key
```

### Option 3: Login Command
```bash
bittu
# Then type: /login
```

### Available API Keys:
- **OpenCode**: `mimo-v2.5-free` (free tier)
- **NVIDIA**: `nvapi-...` (free tier)
- **Cloudflare**: `cfut_...` (free tier)

---

## 🔄 Updating BITTU

### Option 1: CLI Command (Recommended)
```bash
bittu --update
```

### Option 2: Manual Update
```bash
cd /path/to/notworking
git pull origin main
pip install -e .
```

---

## 🎯 Usage

```bash
# Launch TUI (default)
bittu

# Plain REPL mode
bittu --plain

# One-shot prompt
bittu -p "read README"

# Auto-approve mode
bittu --yolo

# Different directory
bittu --workdir /path/to/project
```

---

## 🌙 Dream Mode ULTRA PRO — Enterprise Bounded Autonomy

```bash
# Basic Dream Mode
/dream <your goal>

# Fast Dream Mode (auto model selection)
/dream-fast <your goal>

# Ultra Dream Mode (maximum bounded autonomy with verification)
/dream-ultra <your goal>
```

### Long-Running Work:
- `/dream-ultra` selects the strongest bounded effort profile.
- Each run has a hard step ceiling and a stall detector.
- Work is checkpointed and resumable instead of running without limits.
- Mutating actions still follow the configured approval policy unless explicitly overridden.

### 15 Parallel Analysis Engines (Control Plane):
1. Deep AST Analysis — cyclomatic + cognitive complexity
2. Dependency Graph — circular detection, orphan modules
3. Security Analysis — secrets, SQL injection, path traversal
4. Performance Analysis — N+1 queries, string concat in loops
5. Code Quality Baseline — maintainability index, technical debt
6. Architecture Brain — module coupling, cohesion
7. Risk Heatmap — quantified risk per directory
8. Change Impact — blast radius estimation
9. Dead Code Detection — unused imports, unreachable functions
10. Type Hints Analysis — coverage percentage
11. Code Smells — god classes, long params, feature envy
12. API Surface — public API analysis
13. Test Coverage — test ratio analysis
14. Documentation — docstring coverage
15. Fake/Simulated Code — stubs, NotImplementedError, fake returns

### Bounded Autonomy Logic:
```
Agent actively calling tools? → Continue within the hard step cap
Files changed since last check? → Reset the stall counter
Stall for 12 checks with no progress? → Stop and report
All verified (no fakes, no errors, tests pass)? → Done ✓
```

---

## Interface (Grok CLI jaisa)

```
┌────────────────────────────────────────────────────────┐
│ ● ● ●                  📁 bun run dev                    │
│                                                          │
│                    ·  *      ·    *                      │
│              *          ✦        ·    ✦                  │
│                        BITTU        ·                    │
│           ✦     ·              *          *              │
│                      ˙        ✦     ˙                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐│
│  │ Plan   What are we building?                        ││
│  └────────────────────────────────────────────────────┘│
│  BITTU [Dream Mode] 1.2K tokens    enter send  tab modes │
│                                                          │
│ ~/Projects/bittu-cli                            v2.0.0   │
└────────────────────────────────────────────────────────┘
```

---

## 🧠 Real Effort Engine

| Effort | Mult | Steps | Real behavior |
|--------|------|-------|---------------|
| `normal` | 1× | 80 | Fast, balanced. Everyday edits & questions. |
| **`max`** | 10× | 120 | **Best work, deep thinking** — plan-first + self-verify + auto-debug + quality gate. |
| **`ultra`** | 50× | 140 | **Most complex work** — deep research + parallel swarm + security scan + CI-grade verify. |
| **`ultracombomax`** | 120× | 300 | **Full enterprise-level** — auto-checkpoint + all gates + exhaustive verification. |
| **`goal`** | 300× | 400 | **Fully autonomous end-to-end** — auto-accept, goal contract, milestones, all gates. |
| `dream` 🌙 | **1000×** | **1,000 hard-capped** | **Deep bounded autonomy — checkpointed, resumable, verification-gated and stall-aware.** |

```bash
/max /ultra /ultracombomax     # thinking levels
/goal <goal text>              # autonomous end-to-end
/dream <goal text>             # 1000× — orchestrate everything
/dream-ultra <goal text>       # deepest bounded mode with verification + checkpoints
/effort <name>                 # set by name
```

---

## ⌨️ Keyboard & interaction

| Key | Action |
|-----|--------|
| **Esc** | Running task stop karo / palette band |
| **Mouse drag** | Text select + copy (native terminal copy) |
| **PgUp / PgDown** | `/command` dropdown navigate |
| **Enter / Tab** | Selected command accept karo |
| **Tab** (no palette) | Mode cycle (Plan → Build → Chat) |
| **Ctrl+K / Ctrl+J** | Transcript scroll up/down |
| **Ctrl+U / Ctrl+D** | Page up/down |

---

## ⚡ All Features (27 tools · 34 slash commands)

| # | Feature | Command / Tool |
|---|---------|----------------|
| 1 | **Plan mode** | `/plan` |
| 2 | **Diff viewer** | `show_diff` |
| 3 | **Multi-agent swarm** | `/swarm a \| b \| c` |
| 4 | **Auto-test on save** | `/autotest` |
| 5 | **Code metrics** | `/metrics`, `code_metrics` |
| 6 | **Fuzzy file finder** | `fuzzy_find` |
| 7 | **Project checkpoints** | `/checkpoint`, `/restore` |
| 8 | **Lint** | `lint` |
| 9 | **Dependency analyzer** | `deps` |
| 10 | **Secret scanner** | `/secrets`, `secret_scan` |
| 11 | **TODO/FIXME extractor** | `/todos`, `todo_scan` |
| 12 | **Project scaffold** | `scaffold` |
| 13 | **HTTP request** | `http_request` |
| 14 | **JSON data tool** | `data_tool` |
| 15 | **Regex search+replace** | `regex_replace` |
| 16 | **Tree** | `/tree`, `tree` |
| 17 | **Command history** | `/history` |
| 18 | **Export conversation** | `/export md\|html` |
| 19 | **LLM cache stats** | `/stats` |
| 20 | **Clear LLM cache** | `/clear-cache` |
| 21 | **Live web search** | `/web`, `web_search` |
| 22 | **Public page fetch** | `/fetch`, `web_search(fetch)` |
| 23 | **Live token telemetry** | `/cost`, TUI telemetry strip |

---

## Slash Commands

| Command | Kya karta hai |
|---|---|
| `/help` | Saare commands dikhao |
| `/init` | BITTU.md project guide banao |
| `/model [name]` | AI model dikhao/set karo |
| `/mode [plan\|build\|chat]` | Mode switch |
| `/cwd [path]` | Working directory dikhao/badlo |
| `/config` | Current config dikhao |
| `/tools` | Available tools list |
| `/login` | API key / provider info |
| `/setkey` | API key save karo |
| `/yolo` | Auto-approve toggle |
| `/clear` | Conversation clear |
| `/undo` `/redo` | File changes undo/redo |
| `/sessions` `/resume` | Saved sessions list / resume |
| `/search` `/index` | Semantic file search / rebuild index |
| `/memory` | Remembered facts dikhao |
| `/cost` | Live input/output token usage, estimates, requests, tools and latency |
| `/stats` | LLM cache hit rate + token stats |
| `/clear-cache` | LLM response cache clear |
| `/git` | Git command chalao |
| `/plan` | Plan-first mode toggle |
| `/autotest` | Auto-test after edits toggle |
| `/checkpoint` | Project snapshot |
| `/restore` | Checkpoint restore |
| `/swarm` | Parallel sub-agents |
| `/export` | Chat export (md\|html) |
| `/metrics` | Code metrics |
| `/secrets` | Secret scan |
| `/todos` | TODO/FIXME scan |
| `/tree` | Project tree |
| `/history` | Command history |
| `/effort` | Effort level show/set |
| `/max` `/ultra` `/ultracombomax` | Thinking levels |
| `/goal` | Autonomous end-to-end goal |
| `/dream` | 1000× bounded orchestration with verification gates |
| `/dream-fast` | Dream with automatic fast-model selection |
| `/dream-ultra` | Dream ULTRA PRO — deepest bounded, checkpointed and verification-gated mode |
| `/quit` | Exit BITTU |

---

## Setup & Run

```bash
cd notworking
python main.py                      # Grok-style TUI (default)
python main.py --workdir /path      # dusri directory par kaam
python main.py --plain              # simple line REPL
python main.py -p "read README"     # ek prompt, phir exit
python main.py --yolo               # sabhi actions auto-approve
```

<details><summary>Module ki tarah bhi chala sakte ho</summary>

```bash
pip install textual
python3 -m zedpy
python3 -m zedpy --workdir /path/to/project
python3 -m zedpy --plain
python3 -m zedpy -p "read README and summarize"
python3 -m zedpy --yolo
```
</details>

> Config pehle se set hai (`config.py`): model `mimo-v2.5-free`, endpoint
> `https://opencode.ai/zen/v1/chat/completions`. Env se override: `ZEDPY_API_KEY`,
> `ZEDPY_BASE_URL`, `ZEDPY_MODEL`.

---

## Structure

```
zedpy/
├── zedpy/
│   ├── __main__.py         # entry: TUI (default) ya plain REPL
│   ├── config.py           # model, base_url, api_key, model profiles
│   ├── agent.py            # ReAct loop — bounded, resumable Dream engine
│   ├── commands.py         # full slash registry + focused grouped palette
│   ├── systemprompts.py    # all system prompts centralized
│   ├── llm/
│   │   ├── client.py       # LRU cache + retry + exponential backoff
│   │   └── streaming.py    # SSE streaming with cancel support
│   ├── core/
│   │   ├── dream.py        # 15 parallel analysis engines + control/verification plane
│   │   ├── effort.py       # 6 effort levels with real behavioral switches
│   │   ├── swarm.py        # parallel multi-agent swarm
│   │   ├── checkpoint.py   # project snapshots
│   │   ├── session.py      # conversation persistence
│   │   ├── memory.py       # cross-session memory
│   │   ├── undo.py         # file change undo/redo
│   │   ├── index.py        # TF-IDF semantic search
│   │   └── export.py       # markdown/html export
│   ├── tui/
│   │   ├── app.py          # Grok-style Textual UI
│   │   └── constellation.py# BITTU starfield logo
│   └── tools/              # 27 tools: files/shell/git/search/analyze/web/memory/...
├── test_real.py
├── test_tui.py
├── test_palette.py         # grouped palette + keyboard UX regression checks
├── test_dream.py
├── test_effort.py
└── README.md
```

---

## Safety

- **Path jail**: working dir ke bahar file nahi (`../../etc/passwd` block).
- **Blocked commands**: `rm -rf /`, fork bomb, `mkfs`, `dd of=/dev/…`, `shutdown`, `reboot`.
- **Approval gate**: write/edit/append/shell default me confirm (jab tak `--yolo` na ho).
- **Undo snapshots**: har file change se pehle purana content save.

---

## ⚠️ Security note

API key `config.py` me plaintext hai. **Ise rotate kar lo** aur production me
`ZEDPY_API_KEY` env var se load karo.
