"""Tool registry. Naya tool add karna? Yahan TOOLS list me daal do."""
from .advanced1 import (
    CodeMetrics,
    Deps,
    FakeScan,
    FuzzyFind,
    Lint,
    SecretScan,
    TodoScan,
)
from .advanced2 import DataTool, HttpRequest, RegexReplace, Scaffold, ShowDiff, Tree
from .analyze import AnalyzeCode
from .files import AppendFile, EditFile, ListDir, ReadFile, WriteFile
from .git import GitTool
from .memory import Recall, Remember
from .search import FindFiles, Grep
from .shell import RunShell
from .websearch import WebSearch

TOOLS = [
    # File ops
    ReadFile(),
    WriteFile(),
    AppendFile(),
    EditFile(),
    ListDir(),
    # Search
    Grep(),
    FindFiles(),
    # Shell
    RunShell(),
    # Advanced (Features 5, 8, 9, 10 from first batch)
    GitTool(),
    AnalyzeCode(),
    WebSearch(),
    Remember(),
    Recall(),
    # New 18 advanced tools
    CodeMetrics(),      # #5
    FuzzyFind(),        # #6
    Lint(),             # #8
    Deps(),             # #9
    SecretScan(),       # #10
    TodoScan(),         # #11
    FakeScan(),         # fake/simulated code detector (Dream Mode)
    ShowDiff(),         # #2
    Scaffold(),         # #12
    HttpRequest(),      # #13
    DataTool(),         # #14
    RegexReplace(),     # #15
    Tree(),             # #16
]

REGISTRY = {t.name: t for t in TOOLS}
SCHEMAS = [t.schema() for t in TOOLS]

__all__ = ["TOOLS", "REGISTRY", "SCHEMAS"]
