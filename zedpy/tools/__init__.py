"""Tool registry. Naya tool add karna? Yahan TOOLS list me daal do."""
from .files import ReadFile, WriteFile, AppendFile, EditFile, ListDir
from .search import Grep, FindFiles
from .shell import RunShell
from .git import GitTool
from .websearch import WebSearch
from .analyze import AnalyzeCode
from .memory import Remember, Recall
from .advanced1 import CodeMetrics, FuzzyFind, Lint, Deps, SecretScan, TodoScan
from .advanced2 import ShowDiff, Scaffold, HttpRequest, DataTool, RegexReplace, Tree

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
