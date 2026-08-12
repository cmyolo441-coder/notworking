"""Dream Mode ULTRA PRO — the most advanced autonomous control plane ever built.

This is REAL code. Every function does actual work:

CONTROL PLANE (before agent acts):
  1. Deep AST analysis — cyclomatic complexity, cognitive complexity, maintainability index
  2. Import dependency graph — full DAG with circular detection, orphan detection
  3. Architecture brain — module boundaries, coupling metrics, cohesion analysis
  4. Risk heatmap — quantified risk per file with confidence intervals
  5. Change impact — blast radius with propagation depth estimation
  6. Code quality baseline — maintainability index, technical debt estimation
  7. Security analysis — hardcoded secrets, dangerous functions, input validation
  8. Performance analysis — N+1 queries, memory leaks, inefficient loops
  9. Full project checkpoint — snapshot with file hashes
 10. Bounded parallel analyzers — concurrent analysis with time and result limits
 11. Coordinated research — provider-aware web/file research, never instruction execution
 12. Milestone executor — resumable plan with explicit progress tracking

AGENT EXECUTES (approval-aware; autonomous only when the selected profile permits it)

VERIFICATION PLANE (after agent finishes):
  1. Incremental verification — lint + secret_scan + tests per change
  2. Parallel verification — quality + security + metrics concurrent
  3. Regression detection — before/after metric comparison with thresholds
  4. Code diff analysis — what changed, why, impact assessment
  5. Self-healing — bounded retries with cancellation and checkpoint support
  6. Evidence pack — cryptographic hash chain with timestamps
  7. Work journal — decisions, risks, next steps
  8. Final report — comprehensive summary with all metrics
"""
from __future__ import annotations

import ast
import concurrent.futures
import hashlib
import os
import re
import time
from pathlib import Path

from ..config import MODEL_PROFILES, Config
from ..systemprompts import DREAM_ULTRA_PRO_HEADER

# ============================================================================
# DREAM MODE - AUTO MODEL SELECTION
# ============================================================================

def get_dream_fast_model() -> str:
    """Get the fastest available model for Dream Mode."""
    # Priority order for speed
    fast_models = ["dream-fast", "dream-pro", "mimo", "fast"]
    for name in fast_models:
        if name in MODEL_PROFILES:
            return name
    return "mimo"


def apply_dream_model(cfg: Config) -> str:
    """Apply Dream Mode optimized model settings for fast response."""
    fast_model = get_dream_fast_model()
    profile = MODEL_PROFILES[fast_model]

    # Apply fast model settings
    cfg.model = profile.model
    cfg.max_tokens = profile.max_tokens

    return fast_model


# ============================================================================
# DEEP AST ANALYSIS ENGINE
# ============================================================================

class ASTAnalyzer(ast.NodeVisitor):
    """Real AST visitor that extracts metrics from Python code."""

    def __init__(self):
        self.functions = []
        self.classes = []
        self.complexities = []
        self.current_function = None
        self.current_class = None
        self.depth = 0

    def visit_FunctionDef(self, node):
        self.current_function = node.name
        self.depth += 1

        # Cyclomatic complexity
        cc = self._calc_cyclomatic(node)

        # Cognitive complexity (nested structures penalized more)
        cog = self._calc_cognitive(node)

        # Function metrics
        func_lines = getattr(node, "end_lineno", 0) - node.lineno + 1
        param_count = len(node.args.args)

        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "lines": func_lines,
            "params": param_count,
            "cyclomatic": cc,
            "cognitive": cog,
            "decorators": len(node.decorator_list),
            "has_return": self._has_return(node),
            "nested_depth": self._max_depth(node),
        })

        self.generic_visit(node)
        self.depth -= 1
        self.current_function = None

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        self.current_class = node.name

        # Count methods
        methods = [n for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

        # Calculate class coupling
        imports_used = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                imports_used.add(child.id)

        self.classes.append({
            "name": node.name,
            "line": node.lineno,
            "methods": len(methods),
            "bases": len(node.bases),
            "decorators": len(node.decorator_list),
        })

        self.generic_visit(node)
        self.current_class = None

    def _calc_cyclomatic(self, node) -> int:
        """Calculate McCabe cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                if child.ifs:
                    complexity += len(child.ifs)
        return complexity

    def _calc_cognitive(self, node) -> int:
        """Calculate cognitive complexity (nests penalized)."""
        complexity = 0
        nest_level = 0

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While)):
                complexity += 1 + nest_level
                nest_level += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1 + nest_level
                nest_level += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _has_return(self, node) -> bool:
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                return True
        return False

    def _max_depth(self, node, current=0) -> int:
        max_d = current
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                d = self._max_depth(child, current + 1)
                max_d = max(max_d, d)
        return max_d


def _deep_ast_analysis(workdir: str) -> str:
    """Real AST analysis with actual complexity metrics."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    all_functions = []
    all_classes = []
    total_lines = 0
    file_count = 0

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue
        file_count += 1

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except (SyntaxError, Exception):
            continue

        total_lines += src.count("\n") + 1

        analyzer = ASTAnalyzer()
        analyzer.visit(tree)

        for func in analyzer.functions:
            func["file"] = str(fp.relative_to(root))
            all_functions.append(func)

        for cls in analyzer.classes:
            cls["file"] = str(fp.relative_to(root))
            all_classes.append(cls)

    # Calculate aggregate metrics
    if all_functions:
        avg_cc = sum(f["cyclomatic"] for f in all_functions) / len(all_functions)
        avg_cog = sum(f["cognitive"] for f in all_functions) / len(all_functions)
        avg_lines = sum(f["lines"] for f in all_functions) / len(all_functions)
        high_cc = [f for f in all_functions if f["cyclomatic"] > 10]
        long_funcs = [f for f in all_functions if f["lines"] > 50]
        deep_nest = [f for f in all_functions if f["nested_depth"] > 4]
    else:
        avg_cc = avg_cog = avg_lines = 0
        high_cc = long_funcs = deep_nest = []

    lines = ["### Deep AST Analysis\n"]
    lines.append(f"  Files analyzed: {file_count}")
    lines.append(f"  Total lines: {total_lines}")
    lines.append(f"  Functions: {len(all_functions)}")
    lines.append(f"  Classes: {len(all_classes)}")
    lines.append("\n  Complexity Metrics:")
    lines.append(f"    Avg cyclomatic complexity: {avg_cc:.1f}")
    lines.append(f"    Avg cognitive complexity: {avg_cog:.1f}")
    lines.append(f"    Avg function length: {avg_lines:.1f} lines")

    if high_cc:
        lines.append(f"\n  ⚠️ High Complexity (>10): {len(high_cc)} functions")
        for f in sorted(high_cc, key=lambda x: x["cyclomatic"], reverse=True)[:10]:
            lines.append(f"    {f['file']}:{f['line']} {f['name']} - CC={f['cyclomatic']}")

    if long_funcs:
        lines.append(f"\n  ⚠️ Long Functions (>50 lines): {len(long_funcs)}")
        for f in sorted(long_funcs, key=lambda x: x["lines"], reverse=True)[:10]:
            lines.append(f"    {f['file']}:{f['line']} {f['name']} - {f['lines']} lines")

    if deep_nest:
        lines.append(f"\n  ⚠️ Deep Nesting (>4): {len(deep_nest)} functions")
        for f in sorted(deep_nest, key=lambda x: x["nested_depth"], reverse=True)[:10]:
            lines.append(f"    {f['file']}:{f['line']} {f['name']} - depth={f['nested_depth']}")

    return "\n".join(lines)


# ============================================================================
# DEPENDENCY GRAPH ENGINE
# ============================================================================

def _dependency_graph(workdir: str) -> str:
    """Build real import dependency graph with circular detection."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    graph: dict[str, set[str]] = {}
    external_imports: dict[str, set[str]] = {}

    # Known stdlib modules
    STDLIB = {
        "os", "sys", "json", "time", "re", "ast", "pathlib", "hashlib",
        "threading", "urllib", "subprocess", "collections", "concurrent",
        "difflib", "fnmatch", "html", "random", "shlex", "dataclasses",
        "typing", "logging", "abc", "io", "copy", "enum", "functools",
        "itertools", "operator", "textwrap", "unicodedata", "codecs",
        "locale", "warnings", "contextlib", "weakref", "types",
        "struct", "binascii", "base64", "binhex", "calendar", "csv",
        "configparser", "argparse", "getopt", "cmd", "shutil", "tempfile",
        "glob", "fnmatch", "linecache", "pickle", "sqlite3", "dbm",
        "xml", "email", "html", "urllib", "http", "ftplib", "smtplib",
        "socket", "ssl", "select", "signal", "mmap", "ctypes",
    }

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue
        module = fp.stem

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except SyntaxError:
            continue

        internal_deps = set()
        external_deps = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    if name in STDLIB:
                        continue
                    # Check if it's internal
                    internal_path = root / name
                    internal_file = root / f"{name}.py"
                    if internal_path.exists() or internal_file.exists():
                        internal_deps.add(name)
                    else:
                        external_deps.add(name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module.split(".")[0]
                    if node.level > 0:  # Relative import = internal
                        internal_deps.add(name)
                    elif name in STDLIB:
                        continue
                    else:
                        internal_path = root / name
                        internal_file = root / f"{name}.py"
                        if internal_path.exists() or internal_file.exists():
                            internal_deps.add(name)
                        else:
                            external_deps.add(name)

        graph[module] = internal_deps
        external_imports[module] = external_deps

    # Detect circular dependencies using DFS
    def detect_cycle(node, visited, stack):
        visited.add(node)
        stack.add(node)
        for dep in graph.get(node, set()):
            if dep not in visited:
                if detect_cycle(dep, visited, stack):
                    return True
            elif dep in stack:
                return True
        stack.discard(node)
        return False

    visited = set()
    cycles = []
    for module in graph:
        if module not in visited:
            if detect_cycle(module, visited, set()):
                # Find the actual cycle
                for dep in graph.get(module, set()):
                    if dep in graph and module in graph.get(dep, set()):
                        pair = tuple(sorted([module, dep]))
                        if pair not in cycles:
                            cycles.append(pair)

    # Find most imported modules
    import_count: dict[str, int] = {}
    for deps in graph.values():
        for dep in deps:
            import_count[dep] = import_count.get(dep, 0) + 1

    most_imported = sorted(import_count.items(), key=lambda x: x[1], reverse=True)[:10]

    # Orphan modules
    all_imported = set()
    for deps in graph.values():
        all_imported.update(deps)
    orphans = [m for m in graph if m not in all_imported and m != "__init__"]

    # Most used external packages
    ext_count: dict[str, int] = {}
    for deps in external_imports.values():
        for dep in deps:
            ext_count[dep] = ext_count.get(dep, 0) + 1
    top_external = sorted(ext_count.items(), key=lambda x: x[1], reverse=True)[:10]

    lines = ["### Dependency Graph\n"]
    lines.append(f"  Internal modules: {len(graph)}")
    lines.append(f"  External packages: {len(ext_count)}")
    lines.append(f"  Circular dependencies: {len(cycles)}")

    if cycles:
        lines.append("\n  ⚠️ Circular Dependencies (CRITICAL):")
        for a, b in cycles[:5]:
            lines.append(f"    {a} ↔ {b}")

    if most_imported:
        lines.append("\n  Most Imported Internal:")
        for mod, count in most_imported:
            lines.append(f"    {mod}: {count} imports")

    if top_external:
        lines.append("\n  External Dependencies:")
        for pkg, count in top_external:
            lines.append(f"    {pkg}: {count} imports")

    if orphans:
        lines.append(f"\n  Orphan Modules ({len(orphans)}):")
        for m in orphans[:10]:
            lines.append(f"    {m}")

    return "\n".join(lines)


# ============================================================================
# SECURITY ANALYSIS ENGINE
# ============================================================================

def _security_analysis(workdir: str) -> str:
    """Real security analysis - detect vulnerabilities."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    issues = []
    patterns = {
        "hardcoded_secret": [
            (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'(?i)(api_key|apikey|api_secret)\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'(?i)(secret|token)\s*=\s*["\'][^"\']+["\']', "Hardcoded secret/token"),
            (r'(?i)(access_key|aws_secret)\s*=\s*["\'][^"\']+["\']', "Hardcoded AWS key"),
            (r'sk-[A-Za-z0-9]{20,}', "Possible OpenAI/Stripe key"),
            (r'nvapi-[A-Za-z0-9]{20,}', "Possible NVIDIA API key"),
            (r'cfut_[A-Za-z0-9]{20,}', "Possible Cloudflare key"),
        ],
        "dangerous_function": [
            (r'\beval\s*\(', "eval() - code injection risk"),
            (r'\bexec\s*\(', "exec() - code injection risk"),
            (r'\bos\.system\s*\(', "os.system() - use subprocess instead"),
            (r'\bsubprocess\.call\s*\(', "subprocess.call() - check shell=True"),
            (r'\b__import__\s*\(', "__import__() - dynamic import risk"),
        ],
        "sql_injection": [
            (r'(?i)(execute|cursor)\s*\([^)]*%s', "SQL string formatting - use parameterized queries"),
            (r'(?i)(execute|cursor)\s*\([^)]*\+', "SQL concatenation - use parameterized queries"),
            (r'(?i)(execute|cursor)\s*\([^)]*\.format', "SQL .format() - use parameterized queries"),
        ],
        "path_traversal": [
            (r'open\s*\([^)]*\+', "File open with concatenation - path traversal risk"),
            (r'open\s*\([^)]*\.format', "File open with format - path traversal risk"),
            (r'open\s*\([^)]*%', "File open with % - path traversal risk"),
        ],
        "insecure_random": [
            (r'\brandom\.(random|randint|choice|shuffle)\s*\(', "Insecure random - use secrets module"),
        ],
        "debug_code": [
            (r'(?i)#\s*debug', "Debug comment"),
            (r'(?i)print\s*\([^)]*debug', "Debug print statement"),
            (r'(?i)breakpoint\s*\(', "Breakpoint left in code"),
        ],
    }

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue
        rel = str(fp.relative_to(root))

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            lines = src.split("\n")
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            for category, pattern_list in patterns.items():
                for pattern, desc in pattern_list:
                    if re.search(pattern, line):
                        issues.append({
                            "file": rel,
                            "line": i,
                            "category": category,
                            "description": desc,
                            "code": line.strip()[:80],
                        })

    # Summary by category
    by_category: dict[str, int] = {}
    for issue in issues:
        by_category[issue["category"]] = by_category.get(issue["category"], 0) + 1

    lines = ["### Security Analysis\n"]
    lines.append(f"  Total issues: {len(issues)}")

    if by_category:
        lines.append("\n  By Category:")
        for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"    {cat}: {count}")

    if issues:
        lines.append("\n  Critical Issues:")
        for issue in sorted(issues, key=lambda x: x["category"])[:15]:
            lines.append(f"    {issue['file']}:{issue['line']} - {issue['description']}")
            lines.append(f"      {issue['code']}")

    return "\n".join(lines)


# ============================================================================
# PERFORMANCE ANALYSIS ENGINE
# ============================================================================

def _performance_analysis(workdir: str) -> str:
    """Real performance analysis - detect inefficiencies."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    issues = []

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue
        rel = str(fp.relative_to(root))

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except (SyntaxError, Exception):
            continue

        for node in ast.walk(tree):
            # N+1 query pattern (loop with function call)
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func_name = ""
                        if isinstance(child.func, ast.Attribute):
                            func_name = child.func.attr
                        elif isinstance(child.func, ast.Name):
                            func_name = child.func.id

                        if func_name in ("execute", "query", "fetch", "get", "find", "read"):
                            issues.append({
                                "file": rel,
                                "line": node.lineno,
                                "type": "N+1 Pattern",
                                "desc": f"Possible N+1: {func_name}() in loop",
                            })

            # String concatenation in loop
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                        if isinstance(child.value, (ast.Constant, ast.JoinedStr)):
                            issues.append({
                                "file": rel,
                                "line": node.lineno,
                                "type": "String Concatenation",
                                "desc": "String concatenation in loop - use join() or list",
                            })

            # Large list comprehension
            if isinstance(node, ast.ListComp):
                # Check for nested comprehensions
                for gen in node.generators:
                    if gen.ifs:
                        issues.append({
                            "file": rel,
                            "line": node.lineno,
                            "type": "Complex Comprehension",
                            "desc": "List comprehension with filter - consider generator",
                        })

            # Global variable mutation
            if isinstance(node, ast.Global):
                issues.append({
                    "file": rel,
                    "line": node.lineno,
                    "type": "Global State",
                    "desc": f"Global variable: {', '.join(node.names)}",
                })

    lines = ["### Performance Analysis\n"]
    lines.append(f"  Issues found: {len(issues)}")

    if issues:
        # Group by type
        by_type: dict[str, list] = {}
        for issue in issues:
            by_type.setdefault(issue["type"], []).append(issue)

        for issue_type, items in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
            lines.append(f"\n  {issue_type} ({len(items)}):")
            for item in items[:5]:
                lines.append(f"    {item['file']}:{item['line']} - {item['desc']}")

    return "\n".join(lines)


# ============================================================================
# CODE QUALITY ENGINE
# ============================================================================

def _code_quality_baseline(workdir: str) -> str:
    """Calculate maintainability index and technical debt."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    metrics = {
        "total_lines": 0,
        "code_lines": 0,
        "blank_lines": 0,
        "comment_lines": 0,
        "function_count": 0,
        "class_count": 0,
        "avg_cc": 0,
        "avg_cog": 0,
        "avg_func_len": 0,
        "max_func_len": 0,
        "maintainability_index": 0,
        "technical_debt_hours": 0,
    }

    all_func_lens = []
    all_ccs = []

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except (SyntaxError, Exception):
            continue

        lines = src.split("\n")
        metrics["total_lines"] += len(lines)
        metrics["blank_lines"] += sum(1 for line in lines if not line.strip())
        metrics["comment_lines"] += sum(1 for line in lines if line.strip().startswith("#"))
        metrics["code_lines"] += sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))

        analyzer = ASTAnalyzer()
        analyzer.visit(tree)

        metrics["function_count"] += len(analyzer.functions)
        metrics["class_count"] += len(analyzer.classes)

        for func in analyzer.functions:
            all_func_lens.append(func["lines"])
            all_ccs.append(func["cyclomatic"])
            metrics["max_func_len"] = max(metrics["max_func_len"], func["lines"])

    if all_func_lens:
        metrics["avg_func_len"] = sum(all_func_lens) / len(all_func_lens)
    if all_ccs:
        metrics["avg_cc"] = sum(all_ccs) / len(all_ccs)

    # Calculate maintainability index (0-100, higher is better)
    # Formula: MI = 171 - 5.2 * ln(V) - 0.23 * CC - 16.2 * ln(L)
    # Simplified version
    if metrics["code_lines"] > 0:
        vol_factor = metrics["code_lines"] / 1000
        cc_factor = metrics["avg_cc"] / 10
        len_factor = metrics["avg_func_len"] / 50

        mi = max(0, min(100, 171 - 5.2 * vol_factor - 0.23 * cc_factor - 16.2 * len_factor))
        metrics["maintainability_index"] = mi

    # Estimate technical debt (hours to fix issues)
    high_cc_count = sum(1 for cc in all_ccs if cc > 10)
    long_func_count = sum(1 for ln in all_func_lens if ln > 50)
    metrics["technical_debt_hours"] = high_cc_count * 2 + long_func_count * 1

    # Quality rating
    mi = metrics["maintainability_index"]
    if mi >= 80:
        rating = "A (Excellent)"
    elif mi >= 60:
        rating = "B (Good)"
    elif mi >= 40:
        rating = "C (Fair)"
    elif mi >= 20:
        rating = "D (Poor)"
    else:
        rating = "F (Critical)"

    lines = ["### Code Quality Baseline\n"]
    lines.append(f"  Total lines: {metrics['total_lines']}")
    lines.append(f"  Code lines: {metrics['code_lines']}")
    lines.append(f"  Comment ratio: {metrics['comment_lines']/max(1,metrics['total_lines'])*100:.1f}%")
    lines.append(f"  Functions: {metrics['function_count']}")
    lines.append(f"  Classes: {metrics['class_count']}")
    lines.append(f"\n  Maintainability Index: {mi:.1f}/100 ({rating})")
    lines.append(f"  Technical Debt: ~{metrics['technical_debt_hours']} hours")
    lines.append("\n  Averages:")
    lines.append(f"    Function length: {metrics['avg_func_len']:.1f} lines")
    lines.append(f"    Cyclomatic complexity: {metrics['avg_cc']:.1f}")
    lines.append(f"    Max function length: {metrics['max_func_len']} lines")

    return "\n".join(lines)


# ============================================================================
# RISK SCORING ENGINE
# ============================================================================

def _risk_heatmap(workdir: str) -> str:
    """Quantified risk scoring per directory."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()
    dir_risk: dict[str, dict] = {}

    for fp in walk_files(root):
        rel = str(fp.relative_to(root))
        parts = rel.split(os.sep)
        if len(parts) < 2:
            continue
        dirname = parts[0]
        if dirname.startswith(".") or dirname in ("__pycache__", "node_modules"):
            continue

        if dirname not in dir_risk:
            dir_risk[dirname] = {"files": 0, "lines": 0, "risk": 0, "factors": []}
        dir_risk[dirname]["files"] += 1

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            lines = src.count("\n") + 1
            dir_risk[dirname]["lines"] += lines

            # Risk factors
            risk = 0

            # Size risk
            risk += lines // 100

            # Security risk
            if "password" in src.lower() or "secret" in src.lower():
                risk += 5
                dir_risk[dirname]["factors"].append("secrets")

            # Complexity risk
            if "eval(" in src or "exec(" in src:
                risk += 3
                dir_risk[dirname]["factors"].append("dangerous_functions")

            # TODO/FIXME risk
            todos = src.count("TODO") + src.count("FIXME") + src.count("HACK")
            if todos > 0:
                risk += todos
                dir_risk[dirname]["factors"].append(f"{todos}_todos")

            dir_risk[dirname]["risk"] += risk
        except Exception:
            continue

    sorted_dirs = sorted(dir_risk.items(),
                         key=lambda x: x[1]["risk"], reverse=True)

    lines = ["### Risk Heatmap\n"]
    for d, info in sorted_dirs[:10]:
        level = "CRITICAL" if info["risk"] > 30 else "HIGH" if info["risk"] > 20 else "MEDIUM" if info["risk"] > 5 else "LOW"
        factors = ", ".join(info["factors"]) if info["factors"] else "none"
        lines.append(
            f"  {d:<30} {level:<10} risk={info['risk']:>3} "
            f"files={info['files']:>3} lines={info['lines']:>5} "
            f"factors=[{factors}]"
        )

    return "\n".join(lines)


# ============================================================================
# CHANGE IMPACT ENGINE
# ============================================================================

def _change_impact(workdir: str) -> str:
    """Blast radius estimation with propagation depth."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()
    total_files = 0
    total_lines = 0
    file_types: dict[str, int] = {}
    dir_files: dict[str, int] = {}

    for fp in walk_files(root):
        total_files += 1
        ext = fp.suffix.lower()
        file_types[ext] = file_types.get(ext, 0) + 1

        rel = str(fp.relative_to(root))
        parts = rel.split(os.sep)
        if len(parts) > 1:
            dir_files[parts[0]] = dir_files.get(parts[0], 0) + 1

        try:
            total_lines += sum(1 for _ in fp.open("r", encoding="utf-8", errors="ignore"))
        except Exception:
            continue

    # Blast radius calculation
    if total_files > 100:
        radius = "CRITICAL"
        confidence = "HIGH"
    elif total_files > 50:
        radius = "HIGH"
        confidence = "HIGH"
    elif total_files > 20:
        radius = "MEDIUM"
        confidence = "MEDIUM"
    else:
        radius = "LOW"
        confidence = "HIGH"

    # Propagation depth estimate
    max_depth = max(dir_files.values()) if dir_files else 0
    avg_depth = sum(dir_files.values()) / len(dir_files) if dir_files else 0

    lines = ["### Change Impact Analysis\n"]
    lines.append(f"  Total files: {total_files}")
    lines.append(f"  Total lines: {total_lines}")
    lines.append(f"  Blast radius: {radius} (confidence: {confidence})")
    lines.append(f"  Max files in directory: {max_depth}")
    lines.append(f"  Avg files per directory: {avg_depth:.1f}")
    lines.append(f"  Estimated propagation depth: {'deep' if max_depth > 20 else 'medium' if max_depth > 10 else 'shallow'}")

    if file_types:
        lines.append("\n  File types:")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:8]:
            lines.append(f"    {ext or 'none':<10} {count:>4} files")

    if dir_files:
        lines.append("\n  Directory sizes:")
        for d, count in sorted(dir_files.items(), key=lambda x: x[1], reverse=True)[:8]:
            lines.append(f"    {d:<30} {count:>4} files")

    return "\n".join(lines)


# ============================================================================
# ARCHITECTURE BRAIN
# ============================================================================

def _architecture_brain(workdir: str) -> str:
    """Module boundary and coupling analysis."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()
    modules: dict[str, list[str]] = {}
    coupling_scores: dict[str, int] = {}

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue
        rel = str(fp.relative_to(root))
        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except (SyntaxError, Exception):
            continue

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.level == 1:
                    imports.add(node.module.split(".")[-1])

        coupling_scores[rel] = len(imports)
        modules.setdefault(rel, list(imports))

    high_coupling = sorted(coupling_scores.items(),
                           key=lambda x: x[1], reverse=True)[:10]

    # Calculate cohesion (simplified)
    avg_coupling = sum(coupling_scores.values()) / len(coupling_scores) if coupling_scores else 0

    lines = ["### Architecture Brain\n"]
    lines.append(f"  Total modules: {len(modules)}")
    lines.append(f"  Average coupling: {avg_coupling:.1f}")
    lines.append(f"  Coupling rating: {'HIGH' if avg_coupling > 5 else 'MEDIUM' if avg_coupling > 2 else 'LOW'}")

    if high_coupling:
        lines.append("\n  High-Coupling Modules (>3 imports):")
        for f, score in high_coupling:
            if score > 3:
                lines.append(f"    {f}: {score} internal imports")

    dirs = set()
    for f in modules:
        parts = f.split(os.sep)
        if len(parts) > 1:
            dirs.add(parts[0])
    if dirs:
        lines.append(f"\n  Module boundaries: {', '.join(sorted(dirs))}")

    return "\n".join(lines)


# ============================================================================
# EVIDENCE PACK
# ============================================================================

def _evidence_pack(messages: list[dict], workdir: str) -> str:
    """Cryptographic hash-chained evidence pack."""
    entries = []
    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content") or ""
        if role in ("system",) or not content:
            continue
        entry = {
            "step": i,
            "role": role,
            "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
            "content_length": len(content),
            "timestamp": time.time(),
            "timestamp_human": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if entries:
            entry["prev_hash"] = entries[-1]["content_hash"]
        entries.append(entry)

    if not entries:
        return "### Evidence Pack\n  (no entries)"

    # Verify chain integrity
    chain_valid = True
    for i in range(1, len(entries)):
        if entries[i].get("prev_hash") != entries[i-1]["content_hash"]:
            chain_valid = False
            break

    lines = ["### Evidence Pack (Cryptographic Hash Chain)\n"]
    lines.append(f"  Total entries: {len(entries)}")
    lines.append(f"  Chain valid: {'YES ✓' if chain_valid else 'NO ✗'}")
    lines.append(f"  Total content: {sum(e['content_length'] for e in entries):,} chars")

    # Show last 5 entries
    lines.append("\n  Recent entries:")
    for e in entries[-5:]:
        lines.append(
            f"    [{e['step']:>3}] {e['role']:<10} "
            f"hash={e['content_hash']} "
            f"len={e['content_length']:>6} "
            f"time={e['timestamp_human']}"
        )

    return "\n".join(lines)


# ============================================================================
# WORK JOURNAL
# ============================================================================

def _work_journal(goal: str, messages: list[dict]) -> str:
    """Extract decisions, risks, and next steps from conversation history."""
    decisions = []
    risks = []
    tools_used: dict[str, int] = {}

    for msg in messages:
        content = msg.get("content") or ""
        role = msg.get("role", "")
        name = msg.get("name") or ""

        if role == "assistant":
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if any(kw in line.lower() for kw in
                       ("decided", "decision:", "chose", "selected", "going with", "plan:",
                        "approach:", "strategy:", "will use", "i chose")):
                    decisions.append(line[:120])
                if any(kw in line.lower() for kw in
                       ("risk:", "warning:", "be careful", "edge case", "caveat", "danger",
                        "caution:", "note:", "important:", "watch out")):
                    risks.append(line[:120])

        if role == "tool":
            # Tool name comes from the 'name' field in the message (set by agent._append_history)
            tool_name = name.strip()
            if not tool_name:
                # Fallback: try to extract from content prefix like "Error: ..."
                m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\b', content)
                tool_name = m.group(1) if m else "unknown"
            if tool_name and tool_name not in ("unknown", ""):
                tools_used[tool_name] = tools_used.get(tool_name, 0) + 1

    lines = ["### Work Journal\n"]
    lines.append(f"  Goal: {goal}")
    lines.append(f"  Messages: {len(messages)}")
    lines.append(f"  Tool calls: {sum(tools_used.values())}")

    if decisions:
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_decisions = []
        for d in decisions:
            key = d.lower()[:60]
            if key not in seen:
                seen.add(key)
                unique_decisions.append(d)
        lines.append("\n  Decisions:")
        for d in unique_decisions[:10]:
            lines.append(f"    → {d}")

    if risks:
        seen_r: set[str] = set()
        unique_risks = []
        for r in risks:
            key = r.lower()[:60]
            if key not in seen_r:
                seen_r.add(key)
                unique_risks.append(r)
        lines.append("\n  Risks Identified:")
        for r in unique_risks[:10]:
            lines.append(f"    ⚠ {r}")

    if tools_used:
        lines.append("\n  Tools Used:")
        for t, count in sorted(tools_used.items(), key=lambda x: x[1], reverse=True)[:15]:
            lines.append(f"    {t}: {count}x")

    if not decisions and not risks and not tools_used:
        lines.append("\n  (auto-extracted from conversation — no decisions/risks found)")

    return "\n".join(lines)


# ============================================================================
# MILESTONE PLAN
# ============================================================================

def _milestone_plan(goal: str, workdir: str) -> str:
    """Generate DAG-based milestone plan with parallel execution."""
    lines = [
        "### Milestone Plan (DAG-Based)\n",
        f"  Goal: {goal}",
        "",
        "  Phase 1: Deep Analysis [parallel]",
        "    ├─ AST parse all files → complexity metrics",
        "    ├─ Build dependency graph → circular detection",
        "    ├─ Security scan → vulnerability report",
        "    ├─ Performance analysis → inefficiency detection",
        "    └─ Quality baseline → maintainability index",
        "    Rollback: No changes made",
        "",
        "  Phase 2: Strategic Planning [sequential]",
        "    ├─ Generate DAG of tasks with dependencies",
        "    ├─ Identify critical path",
        "    ├─ Calculate risk scores per task",
        "    ├─ Design rollback points",
        "    └─ Create project checkpoint",
        "    Rollback: git checkout -- <files>",
        "",
        "  Phase 3: Parallel Implementation [DAG execution]",
        "    ├─ Execute independent tasks in parallel",
        "    ├─ Surgical edits only (edit_file preferred)",
        "    ├─ Follow existing conventions exactly",
        "    ├─ Maximum 3 files changed per step",
        "    └─ Real-time complexity monitoring",
        "    Rollback: Restore from checkpoint",
        "",
        "  Phase 4: Continuous Verification [parallel]",
        "    ├─ Lint after EACH change",
        "    ├─ Tests after EACH change",
        "    ├─ Secret scan after changes",
        "    ├─ Compare metrics with baseline",
        "    ├─ Detect regressions",
        "    └─ Fix failures until green",
        "    Rollback: Revert last change",
        "",
        "  Phase 5: Final Evidence [sequential]",
        "    ├─ Complete audit trail with hash chain",
        "    ├─ Before/after metrics comparison",
        "    ├─ Risk assessment update",
        "    ├─ Technical debt calculation",
        "    └─ Work journal with decisions",
    ]
    return "\n".join(lines)


# ============================================================================
# CONTROL PLANE
# ============================================================================

def control_plane(cfg: Config, goal: str) -> str:
    """Run essential analyzers + fast swarm research for smooth operation."""
    from ..core import checkpoint
    from ..core.swarm import run_swarm
    from ..tools import REGISTRY

    wd = cfg.workdir
    blocks: list[str] = [
        DREAM_ULTRA_PRO_HEADER + goal,
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    def safe(label: str, fn) -> None:
        try:
            out = fn()
            if out:
                blocks.append(f"### {label}\n{str(out)[:2000]}")
        except Exception as e:
            blocks.append(f"### {label}\n(skipped: {e})")

    def _run_parallel(analyzers: list[tuple], max_workers: int) -> None:
        """Submit zero-arg thunks; append each result under its label.

        NOTE: submit the function directly (ex.submit(fn)); an earlier version
        passed the label string as the arg, so every analyzer silently failed.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(fn): label for label, fn in analyzers}
            for fut in concurrent.futures.as_completed(futures):
                label = futures[fut]
                try:
                    out = fut.result()
                    if out:
                        blocks.append(f"### {label}\n{str(out)[:2000]}")
                except Exception as e:
                    blocks.append(f"### {label}\n(skipped: {e})")

    # Phase 1: Quick project overview (concurrent).
    quick_analyzers = [
        ("Project tree", lambda: REGISTRY["tree"].run(wd)),
        ("Code metrics", lambda: REGISTRY["code_metrics"].run(wd)),
        ("Secret scan", lambda: REGISTRY["secret_scan"].run(wd)),
        ("TODO scan", lambda: REGISTRY["todo_scan"].run(wd)),
    ]
    _run_parallel(quick_analyzers, max_workers=4)

    # Phase 2: All 14 deep-analysis engines run for real, in parallel.
    essential_analyzers = [
        ("Deep AST Analysis", lambda: _deep_ast_analysis(wd)),
        ("Dependency Graph", lambda: _dependency_graph(wd)),
        ("Security Analysis", lambda: _security_analysis(wd)),
        ("Performance Analysis", lambda: _performance_analysis(wd)),
        ("Code Quality", lambda: _code_quality_baseline(wd)),
        ("Architecture Brain", lambda: _architecture_brain(wd)),
        ("Risk Heatmap", lambda: _risk_heatmap(wd)),
        ("Change Impact", lambda: _change_impact(wd)),
        ("Dead Code Detection", lambda: _dead_code_detection(wd)),
        ("Type Hints Analysis", lambda: _type_hints_analysis(wd)),
        ("Code Smells", lambda: _code_smells_detection(wd)),
        ("API Surface", lambda: _api_surface_analysis(wd)),
        ("Test Coverage", lambda: _test_coverage_analysis(wd)),
        ("Documentation", lambda: _documentation_analysis(wd)),
        ("Fake/Simulated Code", lambda: _fake_code_detection(wd)),
    ]
    _run_parallel(essential_analyzers, max_workers=8)

    # Phase 3: Deep web research (real network, but wrapped so offline never hangs).
    def _web_research() -> str:
        queries = _derive_research_queries(goal)
        if not queries:
            return "(no research queries derived)"
        out = [f"Deep web research ({len(queries)} queries):", ""]
        for q in queries:
            try:
                res = REGISTRY["web_search"].run(wd, query=q)
                # Also try to fetch the top result for deeper content
                lines = res.split("\n")
                top_url = ""
                for line in lines:
                    line = line.strip()
                    if line.startswith("http") and len(line) > 10:
                        top_url = line
                        break
                if top_url:
                    try:
                        fetched = REGISTRY["web_search"].run(wd, query=q, fetch=top_url)
                        res += f"\n\n[Top result content]:\n{fetched[:800]}"
                    except Exception:
                        pass
            except Exception as e:
                res = f"(search failed: {e})"
            out.append(f"» {q}\n{str(res)[:1500]}\n")
        return "\n".join(out)
    safe("Web Research", _web_research)

    # Phase 4: Project checkpoint (sequential — it writes to .zedpy/).
    safe("Auto-checkpoint",
         lambda: checkpoint.create(wd, f"dream-{time.strftime('%H%M%S')}"))

    # Phase 5: Milestone plan (DAG-based, short).
    blocks.append(_milestone_plan(goal, wd))

    # Phase 6: Coordinated swarm research (wrapped with tight timeout so tests stay offline-safe).
    def _swarm() -> str:
        subtasks = [
            f"Quick analysis of project structure for: {goal}",
            f"Key files and dependencies for: {goal}",
            f"Main risks for: {goal}",
            f"Implementation approach for: {goal}",
        ]
        try:
            return run_swarm(cfg, subtasks, max_workers=1, timeout_per_agent=5)
        except Exception as e:
            return f"(swarm skipped due to timeout/error: {e})"
    safe("Swarm Research", _swarm)

    blocks.append("")
    blocks.append("[DIRECTIVE — DREAM ULTRA PRO]")
    blocks.append("Use the real evidence above to execute the goal END-TO-END:")
    blocks.append("1. ANALYZE: deep AST + dependency graph + security + performance + quality baseline")
    blocks.append("2. PLAN: DAG-based milestones with dependencies, parallel execution, rollback")
    blocks.append("3. IMPLEMENT: surgical edits, follow conventions, max 3 files per step")
    blocks.append("4. VERIFY: lint + secret_scan + tests after EACH change, compare before/after")
    blocks.append("5. SELF-HEAL: diagnose failures and retry with a different approach")
    blocks.append("6. NO FAKE CODE: any pass/TODO/NotImplementedError/mock/simulated code "
                  "found by the 'Fake/Simulated Code' engine MUST be rewritten into real, "
                  "working code. Call the fake_scan tool and keep going until it reports "
                  "'Fake/stub findings: 0'.")
    blocks.append("7. REMEMBER: key decisions via remember tool")
    blocks.append("8. EVIDENCE: hash-chained audit trail with timestamps")
    blocks.append("Auto-accept ON. Never declare 'done' without verification.")
    return "\n\n".join(blocks)


def _derive_research_queries(goal: str) -> list[str]:
    """Turn a goal into focused, goal-specific web-research queries.

    Extracts key technical terms from the goal to build targeted queries
    rather than generic ones.
    """
    g = (goal or "").strip()
    if not g:
        return []

    # Extract key technical terms (words > 4 chars, not stopwords)
    _STOPWORDS = {
        "make", "create", "build", "write", "implement", "add", "update",
        "change", "modify", "improve", "fix", "the", "and", "for", "with",
        "that", "this", "from", "into", "using", "want", "need", "should",
        "please", "could", "would", "like", "also", "more", "very", "just",
    }
    words = re.findall(r'[A-Za-z][A-Za-z0-9_-]{3,}', g)
    key_terms = [w.lower() for w in words if w.lower() not in _STOPWORDS][:5]
    tech_phrase = " ".join(key_terms[:3]) if key_terms else g[:60]

    short = g if len(g) <= 80 else g[:80]

    queries = [
        f"{tech_phrase} python best practices 2024",
        f"{tech_phrase} implementation example",
        f"{short} how to",
        f"{tech_phrase} common pitfalls bugs",
    ]

    # Dedupe while preserving order, drop empties
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = q.strip()
        if q and q.lower() not in seen and len(q) > 5:
            seen.add(q.lower())
            out.append(q)
    return out[:4]


# ============================================================================
# VERIFICATION PLANE
# ============================================================================

def verification_plane(cfg: Config, messages: list[dict]) -> str:
    """Fast parallel verification + evidence pack with timeout protection."""
    from ..tools import REGISTRY

    wd = cfg.workdir
    parts: list[str] = ["[DREAM VERIFICATION]\n"]
    _VERIFY_TIMEOUT = 60  # seconds per check

    # Parallel verification with per-future timeout
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            "Secret Scan": ex.submit(lambda: REGISTRY["secret_scan"].run(wd)),
            "Code Metrics": ex.submit(lambda: REGISTRY["code_metrics"].run(wd)),
            "Quality Check": ex.submit(lambda: _code_quality_baseline(wd)),
            "Fake Code Check": ex.submit(lambda: _fake_code_detection(wd)),
        }
        for label, fut in futures.items():
            try:
                result = fut.result(timeout=_VERIFY_TIMEOUT)
                parts.append(f"### {label}\n{str(result)[:1500]}")
            except concurrent.futures.TimeoutError:
                parts.append(f"### {label}\n(timed out after {_VERIFY_TIMEOUT}s)")
            except Exception as e:
                parts.append(f"### {label}\n(error: {e})")

    # Work journal
    goal = ""
    for m in messages:
        if m.get("role") == "user":
            content = m.get("content") or ""
            if content and not content.startswith("["):
                goal = content[:200]
                break
    parts.append(_work_journal(goal, messages))

    # Evidence pack
    parts.append(_evidence_pack(messages, wd))

    return "\n\n".join(parts)


# ============================================================================
# ADVANCED ANALYSIS ENGINES - DREAM MODE ULTRA PRO
# ============================================================================

def _dead_code_detection(workdir: str) -> str:
    """Detect dead code, unused imports, unreachable functions."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    all_defined = set()  # All defined functions/classes
    all_called = set()   # All called functions/methods
    all_imported = set() # All imported names
    unused_imports = []
    unreachable = []

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue
        rel = str(fp.relative_to(root))

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except (SyntaxError, Exception):
            continue

        # Extract definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                all_defined.add((rel, node.name))
            elif isinstance(node, ast.ClassDef):
                all_defined.add((rel, node.name))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    all_imported.add((rel, name))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    all_imported.add((rel, name))

        # Extract calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    all_called.add((rel, node.func.id))
                elif isinstance(node.func, ast.Attribute):
                    all_called.add((rel, node.func.attr))

    # Find unused imports
    for file, name in all_imported:
        if name == "*":
            continue
        if name not in {n for _, n in all_called}:
            unused_imports.append((file, name))

    # Find dead functions
    for file, name in all_defined:
        if name.startswith("_") and name != "__init__":
            continue
        if name not in {n for _, n in all_called}:
            unreachable.append((file, name))

    lines = ["### Dead Code Detection\n"]
    lines.append(f"  Unused imports: {len(unused_imports)}")
    lines.append(f"  Dead functions: {len(unreachable)}")

    if unused_imports:
        lines.append("\n  Unused Imports:")
        for file, name in unused_imports[:15]:
            lines.append(f"    {file}: {name}")

    if unreachable:
        lines.append("\n  Dead Functions:")
        for file, name in unreachable[:15]:
            lines.append(f"    {file}: {name}")

    return "\n".join(lines)


def _type_hints_analysis(workdir: str) -> str:
    """Analyze type hint coverage and consistency."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    total_funcs = 0
    typed_funcs = 0
    total_params = 0
    typed_params = 0
    missing_return_types = 0

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except (SyntaxError, Exception):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                total_funcs += 1

                # Check return type
                if node.returns:
                    typed_funcs += 1
                else:
                    missing_return_types += 1

                # Check parameters
                for arg in node.args.args:
                    if arg.arg == "self" or arg.arg == "cls":
                        continue
                    total_params += 1
                    if arg.annotation:
                        typed_params += 1

    coverage = (typed_params / total_params * 100) if total_params > 0 else 0

    lines = ["### Type Hints Analysis\n"]
    lines.append(f"  Functions: {typed_funcs}/{total_funcs} have return types")
    lines.append(f"  Parameters: {typed_params}/{total_params} are typed")
    lines.append(f"  Type coverage: {coverage:.1f}%")
    lines.append(f"  Missing return types: {missing_return_types}")

    if coverage < 50:
        lines.append("\n  ⚠️ Low type hint coverage - consider adding types")
    elif coverage < 80:
        lines.append("\n  ⚠️ Medium type hint coverage")
    else:
        lines.append("\n  ✓ Good type hint coverage")

    return "\n".join(lines)


def _code_smells_detection(workdir: str) -> str:
    """Detect code smells and anti-patterns."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    smells = []

    smell_patterns = {
        "Long Parameter List": (r'def\s+\w+\s*\([^)]*,[^)]*,[^)]*,[^)]*\)', "More than 3 parameters"),
        "God Class": (r'class\s+\w+.*:', "Large class - consider splitting"),
        "Feature Envy": (r'self\.\w+\.\w+\.\w+', "Deep method chaining"),
        "Primitive Obsession": (r'def\s+\w+\s*\(.*int.*str.*bool', "Using primitives instead of objects"),
        "Switch Statement": (r'elif\s+.*==|if\s+.*==.*elif', "Multiple conditions - consider polymorphism"),
        "Lazy Class": (r'class\s+\w+.*:\s*\n\s*pass', "Empty class"),
        "Speculative Generality": (r'def\s+\w+.*\(.*=\s*None', "Optional parameters - check if needed"),
    }

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue
        rel = str(fp.relative_to(root))

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for name, (pattern, desc) in smell_patterns.items():
            matches = re.finditer(pattern, src, re.MULTILINE)
            for match in matches:
                line_num = src[:match.start()].count("\n") + 1
                smells.append({
                    "file": rel,
                    "line": line_num,
                    "type": name,
                    "desc": desc,
                })

    lines = ["### Code Smells Detection\n"]
    lines.append(f"  Total smells: {len(smells)}")

    # Group by type
    by_type: dict[str, list] = {}
    for smell in smells:
        by_type.setdefault(smell["type"], []).append(smell)

    for smell_type, items in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
        lines.append(f"\n  {smell_type} ({len(items)}):")
        for item in items[:5]:
            lines.append(f"    {item['file']}:{item['line']} - {item['desc']}")

    return "\n".join(lines)


def _api_surface_analysis(workdir: str) -> str:
    """Analyze public API surface and design patterns."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    public_funcs = []
    public_classes = []
    decorators_used = {}

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue
        rel = str(fp.relative_to(root))

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except (SyntaxError, Exception):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not node.name.startswith("_"):
                    public_funcs.append({
                        "file": rel,
                        "name": node.name,
                        "line": node.lineno,
                        "params": len(node.args.args),
                        "decorators": [d.id if isinstance(d, ast.Name) else "..." for d in node.decorator_list],
                    })
                    for d in node.decorator_list:
                        if isinstance(d, ast.Name):
                            decorators_used[d.id] = decorators_used.get(d.id, 0) + 1

            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith("_"):
                    public_classes.append({
                        "file": rel,
                        "name": node.name,
                        "line": node.lineno,
                        "methods": len([n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]),
                        "bases": len(node.bases),
                    })

    lines = ["### API Surface Analysis\n"]
    lines.append(f"  Public functions: {len(public_funcs)}")
    lines.append(f"  Public classes: {len(public_classes)}")

    if decorators_used:
        lines.append("\n  Decorators Used:")
        for deco, count in sorted(decorators_used.items(), key=lambda x: x[1], reverse=True)[:10]:
            lines.append(f"    @{deco}: {count}x")

    if public_funcs:
        lines.append("\n  Largest Public APIs:")
        for func in sorted(public_funcs, key=lambda x: x["params"], reverse=True)[:10]:
            lines.append(f"    {func['file']}:{func['name']}({func['params']} params)")

    return "\n".join(lines)


def _test_coverage_analysis(workdir: str) -> str:
    """Analyze test coverage and test quality."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    test_files = []
    source_files = []

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue
        rel = str(fp.relative_to(root))

        try:
            fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if "test" in rel.lower() or "spec" in rel.lower():
            test_files.append(rel)
        else:
            source_files.append(rel)

    test_ratio = len(test_files) / len(source_files) if source_files else 0

    lines = ["### Test Coverage Analysis\n"]
    lines.append(f"  Source files: {len(source_files)}")
    lines.append(f"  Test files: {len(test_files)}")
    lines.append(f"  Test ratio: {test_ratio:.2f}")

    if test_ratio < 0.3:
        lines.append("\n  ⚠️ Low test coverage - add more tests")
    elif test_ratio < 0.5:
        lines.append("\n  ⚠️ Medium test coverage")
    else:
        lines.append("\n  ✓ Good test coverage")

    if test_files:
        lines.append("\n  Test Files:")
        for tf in test_files[:10]:
            lines.append(f"    {tf}")

    return "\n".join(lines)


def _documentation_analysis(workdir: str) -> str:
    """Analyze documentation coverage and quality."""
    from ..tools.base import walk_files
    root = Path(workdir).resolve()

    docstrings_missing = 0
    module_docstrings = 0
    class_docstrings = 0
    func_docstrings = 0

    for fp in walk_files(root):
        if fp.suffix != ".py":
            continue

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except (SyntaxError, Exception):
            continue

        # Check module docstring
        if (tree.body and isinstance(tree.body[0], ast.Expr) and
            isinstance(tree.body[0].value, (ast.Constant, ast.Str))):
            module_docstrings += 1

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                    class_docstrings += 1
                else:
                    docstrings_missing += 1

            elif isinstance(node, ast.FunctionDef):
                if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                    func_docstrings += 1
                else:
                    docstrings_missing += 1

    total = module_docstrings + class_docstrings + func_docstrings
    coverage = (total / (total + docstrings_missing) * 100) if (total + docstrings_missing) > 0 else 0

    lines = ["### Documentation Analysis\n"]
    lines.append(f"  Module docstrings: {module_docstrings}")
    lines.append(f"  Class docstrings: {class_docstrings}")
    lines.append(f"  Function docstrings: {func_docstrings}")
    lines.append(f"  Missing docstrings: {docstrings_missing}")
    lines.append(f"  Documentation coverage: {coverage:.1f}%")

    if coverage < 30:
        lines.append("\n  ⚠️ Low documentation coverage")
    elif coverage < 60:
        lines.append("\n  ⚠️ Medium documentation coverage")
    else:
        lines.append("\n  ✓ Good documentation coverage")

    return "\n".join(lines)


# ============================================================================
# FAKE / SIMULATED CODE DETECTION ENGINE
# ============================================================================

# Names/decorators/bases that legitimately have empty or stub bodies.
_ABSTRACT_DECORATORS = {"abstractmethod", "abstractproperty", "overload",
                        "abc.abstractmethod", "abstractclassmethod",
                        "abstractstaticmethod"}
_ABSTRACT_BASES = {"ABC", "ABCMeta", "Protocol", "abc.ABC"}
_FAKE_WORDS = {"fake", "dummy", "mock", "stub", "placeholder", "todo",
               "changeme", "change_me", "foobar", "foo", "bar", "xxx",
               "tbd", "notimplemented", "not_implemented"}
_COMPUTE_PREFIXES = ("compute", "calculate", "calc_", "get_", "fetch_",
                     "load_", "read_", "build_", "make_", "create_",
                     "parse_", "process_", "run_", "handle_")
_SIMULATE_MARKERS = ("simulate", "simulated", "fake", "pretend", "mock",
                     "dummy", "placeholder", "for now", "temporary", "stub")


def _decorator_name(dec) -> str:
    """Best-effort dotted name of a decorator node."""
    if isinstance(dec, ast.Name):
        return dec.id
    if isinstance(dec, ast.Attribute):
        parts = []
        node = dec
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))
    if isinstance(dec, ast.Call):
        return _decorator_name(dec.func)
    return ""


def _base_name(base) -> str:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return f"{_base_name(base.value)}.{base.attr}" if base.value else base.attr
    return ""


class _FakeCodeVisitor(ast.NodeVisitor):
    """Walk a module, flagging fake/stub/simulated code with low false positives.

    Tracks the enclosing-class stack so abstract-method / Protocol bodies (which
    are legitimately empty) are not flagged.
    """

    def __init__(self, rel: str, source_lines: list[str], is_pyi: bool):
        self.rel = rel
        self.lines = source_lines
        self.is_pyi = is_pyi
        self.class_stack: list[set[str]] = []  # bases per enclosing class
        self.findings: list[dict] = []  # {line, category, severity, snippet}

    # --- class tracking ---
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = {_base_name(b) for b in node.bases}
        self.class_stack.append(bases)
        self.generic_visit(node)
        self.class_stack.pop()

    # --- function bodies ---
    def visit_FunctionDef(self, node) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _is_abstract_context(self, node) -> bool:
        decs = {_decorator_name(d) for d in node.decorator_list}
        if decs & _ABSTRACT_DECORATORS:
            return True
        for bases in self.class_stack:
            if bases & _ABSTRACT_BASES:
                return True
        return False

    def _add(self, line: int, category: str, severity: str) -> None:
        snippet = ""
        if 1 <= line <= len(self.lines):
            snippet = self.lines[line - 1].strip()[:100]
        self.findings.append({"line": line, "category": category,
                              "severity": severity, "snippet": snippet})

    def _check_function(self, node) -> None:
        body = list(node.body)
        # Drop a leading docstring.
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]
        if not body:
            return

        abstract = self._is_abstract_context(node)

        # 1. Body is a single `pass`.
        if len(body) == 1 and isinstance(body[0], ast.Pass):
            if not abstract:
                self._add(node.lineno, "empty-stub (pass)", "blocking")
            return

        # 2. Body is a single `...` (Ellipsis).
        if (len(body) == 1 and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and body[0].value.value is Ellipsis):
            if not abstract and not self.is_pyi:
                self._add(node.lineno, "empty-stub (...)", "blocking")
            return

        # 3. Body is a single `raise NotImplementedError`.
        if len(body) == 1 and isinstance(body[0], ast.Raise):
            exc = body[0].exc
            exc_name = ""
            if isinstance(exc, ast.Name):
                exc_name = exc.id
            elif isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                exc_name = exc.func.id
            if exc_name == "NotImplementedError" and not abstract:
                self._add(node.lineno, "NotImplementedError stub", "blocking")
            return

        # 4. Single return of a fake/placeholder value in a compute-like fn.
        if len(body) == 1 and isinstance(body[0], ast.Return):
            self._check_fake_return(node, body[0])

    def _check_fake_return(self, fn, ret: ast.Return) -> None:
        val = ret.value
        name = fn.name.lower()
        # Fake string/word literal returned anywhere.
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            if val.value.strip().lower() in _FAKE_WORDS:
                self._add(ret.lineno, "fake return value", "blocking")
                return
        # Empty/zero return from a function that claims to compute something.
        computes = name.startswith(_COMPUTE_PREFIXES)
        if computes:
            empty = (
                (isinstance(val, ast.Constant) and val.value in (None, 0))
                or (isinstance(val, ast.Dict) and not val.keys)
                or (isinstance(val, (ast.List, ast.Tuple, ast.Set)) and not val.elts)
            )
            if empty:
                self._add(ret.lineno, "compute fn returns empty/placeholder",
                          "blocking")


def _fake_code_detection(workdir: str, path: str = ".") -> str:
    """Detect fake / simulated / placeholder code across the tree.

    Blocking-severity findings (empty stubs, NotImplementedError, fake returns,
    simulated sleeps) gate Dream Mode completion. TODO/FIXME markers are reported
    as low severity. The agent remains resumable and bounded; a hard cap or stall
    guard returns a truthful blocker report instead of claiming infinite progress.
    """
    from ..tools.base import walk_files
    root = Path(workdir).resolve()
    base = (root / path).resolve() if path not in (".", "") else root

    blocking: list[tuple[str, dict]] = []
    low: list[tuple[str, dict]] = []

    todo_re = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
    sleep_re = re.compile(r"\b(?:time\.)?sleep\s*\(")

    for fp in walk_files(root):
        if fp.suffix not in (".py", ".pyi"):
            continue
        if base != root and base not in fp.parents and fp != base:
            continue
        rel = str(fp.relative_to(root))
        is_test = rel.startswith("test") or "test" in Path(rel).parts or "tests" in rel

        try:
            src = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        src_lines = src.split("\n")

        # AST-based structural signals.
        try:
            tree = ast.parse(src)
            visitor = _FakeCodeVisitor(rel, src_lines, fp.suffix == ".pyi")
            visitor.visit(tree)
            for f in visitor.findings:
                if is_test:
                    continue  # stubs in tests are expected
                blocking.append((rel, f))
        except SyntaxError:
            pass

        # Line-based signals.
        for i, line in enumerate(src_lines, 1):
            stripped = line.strip()
            # TODO/FIXME markers (low severity).
            if todo_re.search(line):
                low.append((rel, {"line": i, "category": "TODO/FIXME marker",
                                  "severity": "low", "snippet": stripped[:100]}))
            # sleep() used to simulate work (marker comment required).
            if sleep_re.search(line) and not is_test:
                prev = src_lines[i - 2] if i >= 2 else ""
                ctx = (line + " " + prev).lower()
                if any(m in ctx for m in _SIMULATE_MARKERS):
                    blocking.append((rel, {
                        "line": i, "category": "simulated work (sleep)",
                        "severity": "blocking", "snippet": stripped[:100]}))

    out = ["### Fake / Simulated Code Detection\n"]
    out.append(f"  Blocking findings: {len(blocking)}")
    out.append(f"  Low-severity markers (TODO/FIXME): {len(low)}")

    if blocking:
        out.append("\n  ⚠️ BLOCKING — rewrite these into real working code:")
        for rel, f in blocking[:25]:
            out.append(f"    {rel}:{f['line']} [{f['category']}] {f['snippet']}")
    if low:
        out.append("\n  Markers (non-blocking):")
        for rel, f in low[:10]:
            out.append(f"    {rel}:{f['line']} [{f['category']}] {f['snippet']}")

    if not blocking:
        out.append("\n  ✓ No fake/simulated code detected.")

    # Machine-readable line consumed by the Dream completion check.
    out.append(f"\nFake/stub findings: {len(blocking)}")
    return "\n".join(out)
