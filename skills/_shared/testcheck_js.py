"""
testcheck_js.py — best-effort regex analysis of a JS/TS test (`test(`/`it(` titles).

Used by `testcheck`. Pure standard library.
"""
from __future__ import annotations

import re

ABOVE = 3
_START = re.compile(r"^[ \t]*(?:test|it|describe)(?:\.\w+)*\s*\(", re.MULTILINE)
_LITERAL = re.compile(r"""^\s*(?:true|false|null|undefined|NaN|-?\d+(?:\.\d+)?|'[^']*'|"[^"]*"|`[^`$]*`)?\s*$""")
_STRING = re.compile(r"""'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`""")
_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
_CALL = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\(")
_NOT_CODE = {"expect", "assert", "test", "it", "describe", "beforeEach", "afterEach",
             "beforeAll", "afterAll", "console.log", "require", "if", "for", "while",
             "switch", "catch", "function", "return", "typeof", "async", "await", "new"}


def _paren_arg(text: str, open_at: int):
    """Text between the `(` at `open_at` and its matching `)`, and the index after it."""
    depth, i, quote = 0, open_at, None
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif c in "'\"`":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return text[open_at + 1:i], i + 1
        i += 1
    return text[open_at + 1:], len(text)


def _split_args(arg: str) -> list:
    out, depth, quote, cur = [], 0, None, ""
    for c in arg:
        if quote:
            quote = None if c == quote else quote
        elif c in "'\"`":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            out.append(cur)
            cur = ""
            continue
        cur += c
    return out + [cur]


def _assertions(body: str) -> list:
    """[is constant-only] per `expect(...)...(...)` / `assert(...)` / `assert.x(...)`."""
    found = []
    for m in re.finditer(r"(?<![\w$.])(expect|assert(?:\.\w+)?)\s*\(", body):
        arg, end = _paren_arg(body, m.end() - 1)
        args = [arg]
        if m[1] == "expect":
            chain = re.match(r"(?:\s*\.\s*\w+)+\s*\(", body[end:])
            if chain:
                args.append(_paren_arg(body, end + chain.end() - 1)[0])
        found.append(all(_LITERAL.match(a) for x in args for a in _split_args(x)))
    return found


def find(text: str, name: str):
    """(source, has_assertion, trivial, calls_code) of the test titled `name`, or None."""
    title = re.compile(r"^[ \t]*(?:test|it)(?:\.\w+)*\s*\(\s*(['\"`])" + re.escape(name) + r"\1",
                       re.MULTILINE)
    m = title.search(text)
    if m is None:
        return None
    nxt = _START.search(text, m.end())
    body = text[m.start():nxt.start() if nxt else len(text)]
    lines = text[:m.start()].splitlines()
    above = []
    for line in reversed(lines[-ABOVE:]):
        if not line.strip().startswith(("//", "/*", "*")):
            break
        above.insert(0, line)
    asserts = _assertions(_COMMENT.sub("", body))
    code = _STRING.sub('""', _COMMENT.sub("", body))
    calls = any(c not in _NOT_CODE and not c.startswith(("expect", "assert"))
                for c in _CALL.findall(code))
    source = "\n".join(above + [body])
    return source, bool(asserts), bool(asserts) and all(asserts), calls
