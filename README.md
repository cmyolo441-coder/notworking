# BITTU v2.0.0 — Enterprise Terminal AI Coding Agent

Ek **real, working** terminal AI agent jiska interface **bilkul Grok CLI jaisa** hai
(sirf "Grok" ki jagah **BITTU**), plus **Claude Code jaise slash `/commands`**.

Ye actually:
- 📖 files **read** karta hai
- ✏️ files **edit / write / append** karta hai
- 🖥️ **shell commands** chalata hai
- 🔍 codebase **search** karta hai (grep, find_files)
- 🌙 **Dream Ultra Mode** — 19K-40K files tak end-to-end autonomous development

...ek **ReAct loop** me, OpenAI-compatible LLM (`mimo-v2.5-free` @ opencode zen) ke saath.

> ✅ **Verified working** with the real LLM:
> - `test_real.py` → 4/4 pass (read, edit disk-verify, shell, write+run)
> - `test_tui.py`  → 3/3 pass (startup UI, slash command, agent file edit through the TUI)

---

## 🆕 v2.0.0 — What's New

### 🌙 Enterprise Dream Ultra Mode (Never-Stop)
- **50,000 steps** (was 600) — 19K-40K file projects ke liye
- **5,000 continuations** (was 25) — jab tak kaam complete na ho tab tak nahi rukta
- **Never stops mid-work** — agent actively tool calls kar raha ho to kabhi nahi rokta
- **All file types tracked** — `.py .json .md .yaml .toml .html .css` sab changes detect
- **Parallel preflight** — metrics + security + deps ek saath chalte hain (3x faster startup)
- **Cached fake-scan** — repeated codebase walks eliminate (60s TTL cache)

### 🐛 Bug Fixes
- Streaming retry loop — fresh headers har retry par (stale headers bug fix)
- Context compression — consecutive user messages bug fix (model rejection fix)
- Work journal — tool name extraction fixed (name field se)
- Effort gates — ab saari Python files lint hoti hain, sirf pehli nahi
- Swarm — local `/tmp` workdir pe skip nahi hota, sirf real CI mein
- Verification plane — per-future timeout (60s) — infinite blocking fix
- TUI `_finish` — dream mode verification section display fix

### ✨ New Commands
- `/stats` — LLM cache hit rate + token usage
- `/clear-cache` — LLM response cache clear karo

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

## 🌙 Dream Mode ULTRA PRO — Enterprise Never-Stop

```bash
# Basic Dream Mode
/dream <your goal>

# Fast Dream Mode (auto model selection)
/dream-fast <your goal>

# Ultra Dream Mode (maximum power — NEVER stops until done)
/dream-ultra <your goal>
```

### Enterprise Scale:
- Ek baar `/dream-ultra` select karo aur bolo "mujhe 19000 files develop karne hain"
- BITTU **tab tak nahi rukta** jab tak EVERY file end-to-end complete na ho
- Auto-accept ON — koi permission nahi maangta
- 50,000 steps, 5,000 continuations — unlimited-style operation

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

### Never-Stop Logic:
```
Agent actively calling tools? → NEVER STOP (keep going)
Files changed since last check? → NEVER STOP (reset stall counter)
Stall for 25+ checks with no progress? → Stop (real stall)
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
| **`dream`** 🌙 | **1000×** | **50,000** | **ENTERPRISE NEVER-STOP — 19K-40K files, jab tak done na ho tab tak nahi rukta.** |

```bash
/max /ultra /ultracombomax     # thinking levels
/goal <goal text>              # autonomous end-to-end
/dream <goal text>             # 1000× — orchestrate everything
/dream-ultra <goal text>       # maximum power, never stops
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
| `/cost` | Token usage |
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
| `/dream` | 1000× — orchestrate EVERYTHING |
| `/dream-fast` | Dream + auto fast model |
| `/dream-ultra` | Dream ULTRA PRO — enterprise never-stop |
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
│   ├── agent.py            # ReAct loop — enterprise never-stop dream engine
│   ├── commands.py         # 34 slash commands
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
