"""
testcheck_py.py — `ast` analysis of a Python test (used by `testcheck`).

`find(text, name)` -> (source, has_assertion, trivial, calls_code) or None.
Pure standard library.
"""
from __future__ import annotations

import ast
import builtins
import re

ABOVE = 3
_BUILTINS = set(dir(builtins))
_NOT_CONSTANT = (ast.Name, ast.Attribute, ast.Call, ast.Subscript, ast.Starred, ast.NamedExpr)
_RAISES = {"raises", "warns"}  # pytest.raises / pytest.warns
_UNITTEST_RAISES = {"assertRaises", "assertWarns", "assertRaisesRegex", "assertWarnsRegex"}


def comments_above(lines: list, start: int, markers: tuple) -> list:
    """The run of comment lines (at most ABOVE) directly above line index `start`."""
    taken = []
    for line in reversed(lines[max(0, start - ABOVE):start]):
        if not line.strip().startswith(markers):
            break
        taken.insert(0, line)
    return taken


def _pytest_names(tree: ast.Module) -> tuple:
    """(names bound to the pytest module, names bound to pytest.raises/warns)."""
    modules, helpers = {"pytest"}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {a.asname or a.name for a in node.names if a.name == "pytest"}
        elif isinstance(node, ast.ImportFrom) and node.module == "pytest":
            helpers |= {a.asname or a.name for a in node.names if a.name in _RAISES}
    return modules, helpers


def _callee(func: ast.expr):
    """(final name, root name) of a call target: `a.b.c()` -> ("c", "a")."""
    final = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    root = func
    while isinstance(root, (ast.Attribute, ast.Call, ast.Subscript)):
        root = root.func if isinstance(root, ast.Call) else root.value
    return final, getattr(root, "id", None)


def _literal_names(func) -> set:
    """Local names whose every binding in the test is a constant-only value."""
    values = {}
    for node in ast.walk(func):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            for t in node.targets if isinstance(node, ast.Assign) else [node.target]:
                if isinstance(t, ast.Name):
                    values.setdefault(t.id, []).append(node.value)
    return {n for n, vs in values.items() if _only_assign_targets(func, n)
            and all(not any(isinstance(x, _NOT_CONSTANT) for x in ast.walk(v)) for v in vs)}


def _only_assign_targets(func, name: str) -> bool:
    """True if every Store of `name` is a plain `name = ...` target (no loop/with/aug/unpack)."""
    plain = sum(1 for n in ast.walk(func) if isinstance(n, (ast.Assign, ast.AnnAssign))
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target])
                if isinstance(t, ast.Name) and t.id == name)
    stores = sum(1 for n in ast.walk(func)
                 if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Store))
    return plain == stores


def _same(a, b) -> bool:
    """Identical expressions without calls (`x == x`); `f() == f()` may differ (side effects)."""
    return ast.dump(a) == ast.dump(b) and not any(isinstance(n, ast.Call) for n in ast.walk(a))


class _Analysis:
    def __init__(self, func, pytest_modules: set, pytest_helpers: set):
        self.func = func
        self.pytest_modules, self.pytest_helpers = pytest_modules, pytest_helpers
        self.literals = _literal_names(func)
        args = func.args
        params = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
        params += [a.arg for a in (args.vararg, args.kwarg) if a]
        self.params = set(params) - {"self", "cls"}

    # constants and tautologies
    def constant(self, node) -> bool:
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id in self.literals and isinstance(n.ctx, ast.Load):
                continue
            if isinstance(n, _NOT_CONSTANT):
                return False
        return True

    def truthy_constant(self, node) -> bool:
        if not self.constant(node):
            return False
        try:
            return bool(ast.literal_eval(node))
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return False

    def trivial(self, node) -> bool:
        """An asserted expression whose outcome does not depend on project code."""
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.Or) and any(self.truthy_constant(v) for v in node.values):
                return True
            return all(self.trivial(v) for v in node.values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self.trivial(node.operand)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and _same(node.left,
                                                                          node.comparators[0]):
            return True
        return self.constant(node)

    # code exercised inside an assertion: a fixture parameter or a `self.<attr>` read
    def touches_code(self, node) -> bool:
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id in self.params:
                return True
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                    and n.value.id == "self" and not n.attr.startswith("assert"):
                return True
        return False

    def is_raises(self, call: ast.Call) -> bool:
        f = call.func
        if isinstance(f, ast.Name):
            return f.id in self.pytest_helpers
        return isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
            and f.value.id in self.pytest_modules and f.attr in _RAISES

    def run(self) -> tuple:
        tested, any_assert, calls = [], False, False  # tested: [trivial?]
        for node in ast.walk(self.func):
            if isinstance(node, ast.Assert):
                any_assert = True
                tested.append(self.trivial(node.test))
                calls = calls or self.touches_code(node.test)
            elif isinstance(node, ast.Call):
                final, root = _callee(node.func)
                if self.is_raises(node) or final in _UNITTEST_RAISES:
                    any_assert = True
                    tested.append(False)  # the guarded code is what is tested
                    skip = 2 if final and final.endswith("Regex") else 1
                    calls = calls or any(not self.constant(a) for a in node.args[skip:])
                elif final and final.startswith("assert"):
                    any_assert = True
                    exprs = list(node.args) + [k.value for k in node.keywords]
                    if isinstance(node.func, ast.Attribute) and root != "self":
                        exprs.append(node.func.value)  # `mock.assert_called_once()`
                    same = len(node.args) >= 2 and _same(node.args[0], node.args[1])
                    tested.append(same or all(self.trivial(e) for e in exprs))
                    calls = calls or any(self.touches_code(e) for e in exprs)
                elif isinstance(node.func, ast.Name):
                    calls = calls or node.func.id not in _BUILTINS
                elif root not in self.pytest_modules and root != "unittest":
                    calls = True
        return any_assert, any_assert and all(tested), calls


def find(text: str, name: str):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    *classes, func_name = re.sub(r"\[.*\]$", "", name).split("::")
    scope = tree.body
    for cls in classes:
        node = next((n for n in scope if isinstance(n, ast.ClassDef) and n.name == cls), None)
        if node is None:
            return None
        scope = node.body
    func = next((n for n in scope if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == func_name), None)
    if func is None:
        return None
    lines = text.splitlines()
    start = min([func.lineno] + [d.lineno for d in func.decorator_list]) - 1
    source = comments_above(lines, start, ("#",)) + lines[start:func.end_lineno]
    return ("\n".join(source), *_Analysis(func, *_pytest_names(tree)).run())
