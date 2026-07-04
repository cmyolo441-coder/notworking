# BITTU — Grok-style Terminal AI Coding Agent

Ek **real, working** terminal AI agent jiska interface **bilkul Grok CLI jaisa** hai
(sirf "Grok" ki jagah **BITTU**), plus **Claude Code jaise slash `/commands`**.

Ye actually:
- 📖 files **read** karta hai
- ✏️ files **edit / write / append** karta hai
- 🖥️ **shell commands** chalata hai
- 🔍 codebase **search** karta hai (grep, find_files)

...ek **ReAct loop** me, OpenAI-compatible LLM (`mimo-v2.5-free` @ opencode zen) ke saath.

> ✅ **Verified working** with the real LLM:
> - `test_real.py` → 4/4 pass (read, edit disk-verify, shell, write+run)
> - `test_tui.py`  → 3/3 pass (startup UI, slash command, agent file edit through the TUI)

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
# Clone the repo
git clone https://github.com/cmyolo441-coder/notworking.git
cd notworking

# Build binary
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
# Pull and run
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

BITTU ko API key ki zaroorat hai. Ye kaise kare:

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

BITTU ko update karna bahut aasan hai. Jab bhi naya version aaye, bas ek command chalao:

### Option 1: CLI Command (Recommended)
```bash
bittu --update
```

### Option 2: Python Module
```bash
python -m zedpy --update
```

### Option 3: Shell Script
```bash
./update.sh
```

### Option 4: Manual Update
```bash
cd /path/to/notworking
git pull origin main
pip install -e .
```

### How Update Works:
1. GitHub se latest code automatically pull karta hai
2. Naya code install karta hai
3. turant naya version available ho jata hai

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

## 🧠 Dream Mode ULTRA PRO

```bash
# Basic Dream Mode
/dream <your goal>

# Fast Dream Mode (auto model selection)
/dream-fast <your goal>

# Ultra Dream Mode (maximum power)
/dream-ultra <your goal>
```

### 14 Parallel Analysis Engines:
1. Deep AST Analysis
2. Dependency Graph
3. Security Analysis
4. Performance Analysis
5. Code Quality Baseline
6. Architecture Brain
7. Risk Heatmap
8. Change Impact
9. Dead Code Detection
10. Type Hints Analysis
11. Code Smells
12. API Surface
13. Test Coverage
14. Documentation

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
│  BITTU Code Fast  99% 254K    shift+enter new line  tab modes │
│                                                          │
│ ~/Projects/bittu-cli                            v1.0.0   │
└────────────────────────────────────────────────────────┘
```

- **Centered BITTU constellation** (startup screen)
- **Amber "Plan" label** + "What are we building?" prompt box
- **Status bar**: `BITTU Code Fast  99% 254K  shift+enter new line  tab modes`
- **Footer**: cwd (left) · version (right)
- **Tab** se mode cycle (Plan → Build → Chat)

---

## 🧠 Real Effort Engine (real runtime behavior, not just labels)

Har level ka **actual behavior** badalta hai — steps, planning, self-verify,
security/quality gates, swarm research, enterprise preflight:

| Effort | Mult | Steps | Real behavior |
|--------|------|-------|---------------|
| `normal` | 1× | 40 | Fast, balanced. Everyday edits & questions. |
| **`max`** | 10× | 80 | **Best work, deep thinking** — plan-first + self-verify + auto-debug + quality gate. |
| **`ultra`** | 50× | 140 | **Most complex work, ultra thinking** — deep research + parallel swarm + security scan + CI-grade verify. |
| **`ultracombomax`** | 120× | 240 | **Full enterprise-level heavy work** — auto-checkpoint + all gates + metrics/secrets/deps preflight + exhaustive verification. |
| **`goal`** | 300× | 400 | **Fully autonomous end-to-end** — auto-accept, goal contract, milestones, all gates, evidence pack. |
| **`dream`** 🌙 | **1000×** | 600 | **MAXIMUM autonomy — orchestrates EVERY tool, feature & command.** See below. |

```bash
/max /ultra /ultracombomax     # thinking levels
/goal <goal text>              # autonomous end-to-end
/dream <goal text>             # 1000× — orchestrate everything
/effort <name>                 # or set by name (aliases: best, complex, enterprise, godmode)
```

Or from CLI / env: `ZEDPY_EFFORT=dream python3 -m zedpy`

### 🌙 Dream Mode (1000×) — the most advanced

Dream Mode is a **real multi-phase autonomous control plane**, not a label:

1. **Control plane (before):** runs EVERY analyzer — project tree, code metrics,
   dependency scan, secret scan, TODO scan — takes a **full project checkpoint**,
   and launches a **parallel swarm** to research the goal (milestones, risks, files).
   All this real evidence is injected into context.
2. **Autonomous execution:** **auto-accept ON** (never asks), 600 steps, 10-agent
   swarm, deepest reasoning (temp 0.02). Uses any of the 25 tools freely.
3. **Verification plane (after):** final lint + secret_scan + tests, and writes an
   **evidence pack** (markdown export of the whole session).

> ✅ **Verified** (`test_dream.py` → 17/17). **Live proof:** in Dream Mode the agent
> autonomously ran control plane (checkpoint + all scans), edited the file, then
> self-verified with lint + secret_scan + a runtime test, and exported an evidence
> pack — all with zero approvals.

### 🎯 Live streaming

Responses now stream **token-by-token** into the transcript (real-time typing),
using SSE. Enabled automatically in the TUI.

> ✅ **Verified** (`test_effort.py` → 15/15): levels escalate, switches are real,
> aliases work, prompt/preflight/gates apply. **Live proof:** in `max` mode the
> agent wrote a custom exception + type validation + docstring, then ran lint +
> doctests + a smoke test to self-verify — real production-grade deep work.

Status bar me active effort dikhta hai: `BITTU [Ultra Combo Max] 1.2K tokens …`

---

## ⌨️ Keyboard & interaction

| Key | Action |
|-----|--------|
| **Esc** | Running task stop karo (agent cancel) / palette band |
| **Mouse drag** | Text select + copy (native terminal copy — mouse capture OFF) |
| **PgUp / PgDown** or **↑ / ↓** | `/command` dropdown me navigate |
| **Enter / Tab** | Selected command accept karo |
| **Tab** (no palette) | Mode cycle (Plan → Build → Chat) |

---

## ⚡ 18 NEW most-powerful features (all real, all tested — 19/19 pass)

| # | Feature | Command / Tool |
|---|---------|----------------|
| 1 | **Plan mode** — plan pehle, execute approval par | `/plan` |
| 2 | **Diff viewer** — colored unified diff | `show_diff` |
| 3 | **Multi-agent swarm** — parallel sub-agents | `/swarm a \| b \| c` |
| 4 | **Auto-test on save** — edits ke baad tests auto-run | `/autotest` |
| 5 | **Code metrics** — LOC, langs, biggest files | `/metrics`, `code_metrics` |
| 6 | **Fuzzy file finder** — approximate name match | `fuzzy_find` |
| 7 | **Project checkpoints** — full snapshot + restore | `/checkpoint`, `/restore` |
| 8 | **Lint** — Python syntax/style check | `lint` |
| 9 | **Dependency analyzer** — imports scan | `deps` |
| 10 | **Secret scanner** — API keys/passwords detect | `/secrets`, `secret_scan` |
| 11 | **TODO/FIXME extractor** | `/todos`, `todo_scan` |
| 12 | **Project scaffold** — python/flask/cli templates | `scaffold` |
| 13 | **HTTP request** — API calls | `http_request` |
| 14 | **JSON data tool** — parse/query/validate | `data_tool` |
| 15 | **Regex search+replace** — bulk edits | `regex_replace` |
| 16 | **Tree** — project structure viewer | `/tree`, `tree` |
| 17 | **Command history** | `/history` |
| 18 | **Export conversation** — markdown/html | `/export md\|html` |

> ✅ **Verified:** `test_18features.py` → 19/19 feature checks + 6/6 TUI interaction
> tests pass. Real LLM ne secret_scan, todo_scan, analyze_code, git tools live use kiye.

**Total now: 25 tools · 32 slash commands.**

---

## 🚀 First 10 Advanced Features (all real, all tested)

| # | Feature | Kya karta hai |
|---|---------|---------------|
| 1 | **Session persistence** | Conversations disk par save/resume (`~/.zedpy/sessions/`). `/sessions`, `/resume last` |
| 2 | **Codebase index + semantic search** | TF-IDF se relevant files auto-rank. `/search`, `/index` |
| 3 | **Undo/Redo** | File changes revert karo. `/undo`, `/redo` |
| 4 | **Streaming responses** | Token-by-token live output (SSE) |
| 5 | **Git integration** | status/diff/log/commit/branch agent se (`git` tool, `/git`) |
| 6 | **Auto-context injection** | Pehli query par relevant files automatically context me |
| 7 | **Token/cost tracking** | Live token count status bar me. `/cost` |
| 8 | **AST code analysis** | Python code intelligence: functions, classes, unused imports, complexity (`analyze_code`) |
| 9 | **Web search** | Real-time info fetch (DuckDuckGo, no API key) (`web_search`) |
| 10 | **Cross-session memory** | Facts/preferences yaad rakhe (`remember`/`recall`, `/memory`) |

> ✅ **Verified:** `test_advanced.py` → **10/10 features pass**. Real LLM ne bhi
> analyze_code, git, aur memory tools successfully use kiye (live tested).

---

## Slash commands (Claude Code jaise)

`/` type karte hi ek autocomplete dropdown dikhta hai:

| Command | Kya karta hai |
|---|---|
| `/help` | Saare commands dikhao |
| `/init` | BITTU.md project guide banao (agent explore karke) |
| `/model [name]` | AI model dikhao/set karo |
| `/mode [plan\|build\|chat]` | Mode switch (ya Tab se cycle) |
| `/cwd [path]` | Working directory dikhao/badlo |
| `/config` | Current config dikhao |
| `/tools` | Available tools list |
| `/login` | API key / provider info |
| `/yolo` | Auto-approve toggle |
| `/clear` | Conversation clear |
| `/undo` `/redo` | File changes undo/redo |
| `/sessions` `/resume` | Saved sessions list / resume |
| `/search` `/index` | Semantic file search / rebuild index |
| `/memory` | Remembered facts dikhao |
| `/cost` | Token usage |
| `/git` | Git command chalao |
| `/quit` | Exit |

---

## Setup & Run

**Sabse aasaan — bas ye chalao:**

```bash
cd zedpy
python main.py
```

`main.py` khud check karega ki `textual` (TUI ke liye) installed hai ya nahi,
aur na ho to install karne ka option dega. Bas! BITTU khul jaayega.

**Saare tareeke:**

```bash
python main.py                      # Grok-style TUI (default)
python main.py --workdir /path      # dusri directory par kaam
python main.py --plain              # simple line REPL (bina TUI)
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
│   ├── config.py           # model, base_url, api_key
│   ├── agent.py            # ReAct loop (LLM ↔ tools)
│   ├── commands.py         # slash commands (/help, /init, /mode …)
│   ├── llm/client.py       # OpenAI-compatible client (stdlib, retry, UA header)
│   ├── tui/
│   │   ├── app.py          # Grok-style Textual UI
│   │   └── constellation.py# BITTU starfield logo
│   └── tools/              # read/write/append/edit/list_dir/grep/find_files/run_shell
├── test_real.py            # agent E2E test (real LLM)
├── test_tui.py             # TUI E2E test (real LLM)
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

API key `config.py` me plaintext hai (aur tumne chat me bhi share ki). **Ise rotate
kar lo** aur production me `ZEDPY_API_KEY` env var se load karo — jo bhi file dekhe wo
key use kar sakta hai.
