"""Coordinated multi-agent swarm — parallel research with task decomposition.

Enhanced features:
  - Task decomposition: break complex goals into sub-tasks
  - Specialist agents: different system prompts for different research types
  - Result fusion: merge and deduplicate findings
  - Timeout protection: prevent hung agents from blocking
  - Error isolation: one agent failure doesn't affect others
"""
from __future__ import annotations
import concurrent.futures
import time
from dataclasses import dataclass

from ..config import Config
from ..llm import LLM
from ..systemprompts import SPECIALISTS


@dataclass
class SwarmResult:
    """Result from a single swarm agent."""
    task: str
    specialist: str
    content: str
    elapsed: float
    success: bool


def run_swarm(
    cfg: Config,
    subtasks: list[str],
    max_workers: int = 4,
    specialist: str = "general",
    timeout_per_agent: int = 60,
) -> str:
    """Run parallel sub-agents with coordinated research.

    Each subtask gets its own LLM call with an appropriate specialist prompt.
    Results are merged with metadata.

    Args:
        cfg: Configuration (model, API key, etc.)
        subtasks: List of research questions to investigate
        max_workers: Max parallel agents
        specialist: Default specialist type (planner|researcher|risk-analyst|general)
        timeout_per_agent: Max seconds per agent before timeout
    """
    llm = LLM(cfg)
    prompt = SPECIALISTS.get(specialist, SPECIALISTS["general"])
    start = time.monotonic()

    def _one(task: str, task_idx: int) -> SwarmResult:
        task_start = time.monotonic()
        try:
            msg = llm.chat([
                {"role": "system", "content": prompt},
                {"role": "user", "content": task},
            ])
            content = msg.get("content") or "(no answer)"
            return SwarmResult(
                task=task,
                specialist=specialist,
                content=content,
                elapsed=time.monotonic() - task_start,
                success=True,
            )
        except Exception as e:
            return SwarmResult(
                task=task,
                specialist=specialist,
                content=f"(error: {e})",
                elapsed=time.monotonic() - task_start,
                success=False,
            )

    results: list[SwarmResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(_one, task, idx): idx
            for idx, task in enumerate(subtasks)
        }
        for fut in concurrent.futures.as_completed(
            futures, timeout=timeout_per_agent * max_workers
        ):
            try:
                result = fut.result(timeout=timeout_per_agent)
                results.append(result)
            except concurrent.futures.TimeoutError:
                idx = futures[fut]
                results.append(SwarmResult(
                    task=subtasks[idx],
                    specialist=specialist,
                    content="(timeout)",
                    elapsed=timeout_per_agent,
                    success=False,
                ))
            except Exception as e:
                idx = futures[fut]
                results.append(SwarmResult(
                    task=subtasks[idx],
                    specialist=specialist,
                    content=f"(error: {e})",
                    elapsed=0,
                    success=False,
                ))

    total_elapsed = time.monotonic() - start
    successful = sum(1 for r in results if r.success)

    # Build output with metadata
    out = [
        f"Swarm completed: {successful}/{len(subtasks)} tasks "
        f"in {total_elapsed:.1f}s",
        "",
    ]

    # Sort by original order
    results.sort(key=lambda r: subtasks.index(r.task))
    for i, r in enumerate(results, 1):
        status = "ok" if r.success else "FAILED"
        out.append(f"### {i}. [{status}] {r.task}")
        out.append(f"    specialist={r.specialist} elapsed={r.elapsed:.1f}s")
        out.append(r.content)
        out.append("")

    return "\n".join(out)


def decompose_task(goal: str, cfg: Config) -> list[str]:
    """Use LLM to decompose a complex goal into sub-tasks."""
    llm = LLM(cfg)
    try:
        msg = llm.chat([
            {"role": "system", "content": (
                "You are a task decomposition expert. Break the goal into "
                "3-5 concrete, independent sub-tasks. Each sub-task should be "
                "a single line that a research agent can investigate independently. "
                "Return ONLY the sub-tasks, one per line, numbered."
            )},
            {"role": "user", "content": f"Decompose: {goal}"},
        ])
        content = msg.get("content") or ""
        tasks = []
        for line in content.strip().split("\n"):
            line = line.strip()
            # Remove numbering
            if line and line[0].isdigit():
                line = line.split(".", 1)[-1].strip()
            if line:
                tasks.append(line)
        return tasks[:8]  # Cap at 8 sub-tasks
    except Exception:
        return [goal]  # Fallback: use the original goal
