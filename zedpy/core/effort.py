"""Real Effort Engine — adaptive runtime behavior for every level.

Each level has REAL behavioral switches that change how the agent loop executes:
planning depth, verification rigor, research scope, debug retry budget, etc.

NEW: Adaptive behavior adjusts parameters based on task complexity signals.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from ..systemprompts import (
    EFFORT_NORMAL_DESC,
    EFFORT_MAX_DESC, EFFORT_MAX_EXTRA,
    EFFORT_ULTRA_DESC, EFFORT_ULTRA_EXTRA,
    EFFORT_ULTRACOMBOMAX_DESC, EFFORT_ULTRACOMBOMAX_EXTRA,
    EFFORT_GOAL_DESC, EFFORT_GOAL_EXTRA,
    EFFORT_DREAM_DESC, EFFORT_DREAM_EXTRA,
)


@dataclass
class Effort:
    name: str
    label: str
    multiplier: int
    max_steps: int
    max_tokens: int
    temperature: float
    description: str

    # --- behavioral switches ---
    plan_first: bool = False
    self_verify: bool = False
    deep_research: bool = False
    auto_debug: bool = False
    max_debug_retries: int = 0
    parallel_tools: bool = False
    use_swarm: bool = False
    swarm_size: int = 0
    run_quality: bool = False
    run_security: bool = False
    run_metrics: bool = False
    enterprise_preflight: bool = False
    enterprise_gates: bool = False
    auto_checkpoint: bool = False
    context_files: int = 3

    # --- fully-autonomous behavior ---
    goal_mode: bool = False
    dream_mode: bool = False
    auto_accept: bool = False
    export_evidence: bool = False

    # --- advanced behavior ---
    adaptive_planning: bool = False
    context_compression: bool = False
    multi_step_reasoning: bool = False
    tool_chain_composition: bool = False
    self_healing: bool = False
    risk_assessment: bool = False
    architecture_analysis: bool = False
    incremental_verification: bool = False
    parallel_verification: bool = False

    extra_prompt: str = ""


# ---------------------------------------------------------------------------
# Helper: build an Effort with common flag clusters to reduce duplication.
# ---------------------------------------------------------------------------

def _base_flags(
    *, plan: bool = False, verify: bool = False, research: bool = False,
    diagnostic: bool = False, retries: int = 0, parallel: bool = False,
    swarm: bool = False, swarmsize: int = 0, quality: bool = False,
    security: bool = False, metrics: bool = False, preflight: bool = False,
    gates: bool = False, checkpoint: bool = False, ctx: int = 3,
) -> dict:
    return dict(
        plan_first=plan, self_verify=verify, deep_research=research,
        auto_debug=diagnostic, max_debug_retries=retries, parallel_tools=parallel,
        use_swarm=swarm, swarm_size=swarmsize, run_quality=quality,
        run_security=security, run_metrics=metrics,
        enterprise_preflight=preflight, enterprise_gates=gates,
        auto_checkpoint=checkpoint, context_files=ctx,
    )


def _autonomous_flags(
    *, goal: bool = False, dream: bool = False, accept: bool = False,
    evidence: bool = False, adaptive: bool = False, compress: bool = False,
    multi_step: bool = False, chain: bool = False, healing: bool = False,
    risk: bool = False, arch: bool = False, incr_verify: bool = False,
    par_verify: bool = False,
) -> dict:
    return dict(
        goal_mode=goal, dream_mode=dream, auto_accept=accept,
        export_evidence=evidence, adaptive_planning=adaptive,
        context_compression=compress, multi_step_reasoning=multi_step,
        tool_chain_composition=chain, self_healing=healing,
        risk_assessment=risk, architecture_analysis=arch,
        incremental_verification=incr_verify, parallel_verification=par_verify,
    )


# ---------------------------------------------------------------------------
# The catalogue.
# ---------------------------------------------------------------------------

_NORMAL = Effort(
    name="normal", label="Normal", multiplier=1,
    max_steps=80, max_tokens=1_000_000, temperature=0.3,
    description=EFFORT_NORMAL_DESC,
    context_files=3,
)

_MAX = Effort(
    name="max", label="Max Thinking", multiplier=10,
    max_steps=120, max_tokens=1_000_000, temperature=0.15,
    description=EFFORT_MAX_DESC,
    **_base_flags(plan=True, verify=True, diagnostic=True, retries=3,
                  parallel=True, quality=True, metrics=True,
                  preflight=True, ctx=5),
    **_autonomous_flags(multi_step=True, compress=True, risk=True),
    extra_prompt=EFFORT_MAX_EXTRA,
)

_ULTRA = Effort(
    name="ultra", label="Ultra Thinking", multiplier=50,
    max_steps=200, max_tokens=1_000_000, temperature=0.1,
    description=EFFORT_ULTRA_DESC,
    **_base_flags(plan=True, verify=True, research=True, diagnostic=True,
                  retries=5, parallel=True, swarm=True, swarmsize=3,
                  quality=True, security=True, metrics=True,
                  preflight=True, gates=True, ctx=8),
    **_autonomous_flags(multi_step=True, chain=True, compress=True,
                        risk=True, arch=True, incr_verify=True),
    extra_prompt=EFFORT_ULTRA_EXTRA,
)

_ULTRACOMBOMAX = Effort(
    name="ultracombomax", label="Ultra Combo Max", multiplier=120,
    max_steps=300, max_tokens=1_000_000, temperature=0.05,
    description=EFFORT_ULTRACOMBOMAX_DESC,
    **_base_flags(plan=True, verify=True, research=True, diagnostic=True,
                  retries=10, parallel=True, swarm=True, swarmsize=5,
                  quality=True, security=True, metrics=True,
                  preflight=True, gates=True, checkpoint=True, ctx=12),
    **_autonomous_flags(multi_step=True, chain=True, compress=True,
                        risk=True, arch=True, healing=True,
                        incr_verify=True, par_verify=True),
    extra_prompt=EFFORT_ULTRACOMBOMAX_EXTRA,
)

_GOAL = Effort(
    name="goal", label="Goal Mode", multiplier=300,
    max_steps=400, max_tokens=1_000_000, temperature=0.05,
    description=EFFORT_GOAL_DESC,
    **_base_flags(plan=True, verify=True, research=True, diagnostic=True,
                  retries=15, parallel=True, swarm=True, swarmsize=6,
                  quality=True, security=True, metrics=True,
                  preflight=True, gates=True, checkpoint=True, ctx=15),
    **_autonomous_flags(goal=True, accept=True, evidence=True,
                        multi_step=True, chain=True, compress=True,
                        risk=True, arch=True, healing=True,
                        incr_verify=True, par_verify=True),
    extra_prompt=EFFORT_GOAL_EXTRA,
)

_DREAM = Effort(
    name="dream", label="Dream Mode", multiplier=1000,
    max_steps=300, max_tokens=1_000_000, temperature=0.02,
    description=EFFORT_DREAM_DESC,
    **_base_flags(plan=True, verify=True, research=True, diagnostic=True,
                  retries=20, parallel=True, swarm=True, swarmsize=4,
                  quality=True, security=True, metrics=True,
                  preflight=True, gates=True, checkpoint=True, ctx=10),
    **_autonomous_flags(goal=True, dream=True, accept=True, evidence=True,
                        adaptive=True, compress=True, multi_step=True,
                        chain=True, healing=True, risk=True, arch=True,
                        incr_verify=True, par_verify=True),
    extra_prompt=EFFORT_DREAM_EXTRA,
)

CATALOG = {e.name: e for e in [_NORMAL, _MAX, _ULTRA, _ULTRACOMBOMAX, _GOAL, _DREAM]}
ORDER = ["normal", "max", "ultra", "ultracombomax", "goal", "dream"]

_ALIASES = {
    "maxthinking": "max", "max-thinking": "max", "best": "max",
    "ultrathinking": "ultra", "ultra-thinking": "ultra", "complex": "ultra",
    "combo": "ultracombomax", "enterprise": "ultracombomax",
    "ultracombo": "ultracombomax", "ucm": "ultracombomax",
    "autonomous": "goal", "auto": "goal", "endtoend": "goal",
    "1000x": "dream", "godmode": "dream", "god": "dream", "max-autonomy": "dream",
    "ultimate": "dream", "god-tier": "dream", "full-auto": "dream",
}


def get(name: str) -> Effort:
    key = (name or "normal").strip().lower()
    key = _ALIASES.get(key, key)
    return CATALOG.get(key, _NORMAL)


def summary_table() -> str:
    rows = ["Effort levels (real runtime behavior):"]
    for name in ORDER:
        e = CATALOG[name]
        rows.append(
            f"  {e.name:<15} {e.multiplier:>3}x  {e.max_steps:>3} steps  "
            f"— {e.description}"
        )
    return "\n".join(rows)


def classify_complexity(task: str) -> str:
    """Adaptive: classify a task's complexity to suggest effort level.

    Signals: length, technical keywords, number of files/modules mentioned,
    action verbs (refactor, migrate, rewrite vs read, explain).
    """
    task_lower = task.lower()
    score = 0

    # Length signal
    if len(task) > 500:
        score += 3
    elif len(task) > 200:
        score += 2
    elif len(task) > 50:
        score += 1

    # Complexity keywords
    complex_kw = [
        "refactor", "migrate", "rewrite", "architecture", "redesign",
        "optimize", "parallel", "concurrent", "security", "enterprise",
        "production", "deploy", "ci/cd", "pipeline", "database",
        "authentication", "caching", "distributed", "microservice",
        "dream", "autonomous", "full-auto", "everything",
    ]
    for kw in complex_kw:
        if kw in task_lower:
            score += 1

    # Multi-file signals
    file_patterns = ["all files", "entire", "codebase", "project", "every"]
    for p in file_patterns:
        if p in task_lower:
            score += 2

    # Simple task signals
    simple_kw = ["read", "explain", "show", "what is", "how does", "list"]
    for kw in simple_kw:
        if kw in task_lower:
            score -= 1

    if score >= 8:
        return "dream"
    elif score >= 6:
        return "goal"
    elif score >= 4:
        return "ultracombomax"
    elif score >= 3:
        return "ultra"
    elif score >= 2:
        return "max"
    return "normal"
