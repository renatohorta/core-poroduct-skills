from _shared import frontmatter


def test_roundtrip_scalars_and_lists():
    meta = {"id": "ST-001", "status": "2-todo", "labels": ["a", "b"], "empty": "", "none": []}
    text = frontmatter.dump(meta, "Body line\n\n")
    assert text == (
        "---\nid: ST-001\nstatus: 2-todo\nlabels: [a, b]\nempty:\nnone: []\n---\n\nBody line\n"
    )
    assert frontmatter.parse(text) == (meta, "Body line\n")


def test_dump_none_is_empty_and_order_kept():
    text = frontmatter.dump({"b": None, "a": "x"}, "")
    assert text.index("b:") < text.index("a:")
    assert frontmatter.parse(text)[0] == {"b": "", "a": "x"}
    assert "\r" not in text


def test_crlf_and_bom_parse_like_lf():
    lf = "---\nid: TK-001\ntags: [x, y]\n---\n\nhello\nworld\n"
    crlf = "﻿" + lf.replace("\n", "\r\n")
    assert frontmatter.parse(crlf) == frontmatter.parse(lf)
    assert frontmatter.parse(lf) == ({"id": "TK-001", "tags": ["x", "y"]}, "hello\nworld\n")


def test_no_frontmatter_returns_body():
    assert frontmatter.parse("just text\n") == ({}, "just text\n")


def test_values_with_colons_kept():
    text = "---\nsource: docs/x.md#Use Case: Book\n---\nb\n"
    meta, body = frontmatter.parse(text)
    assert meta == {"source": "docs/x.md#Use Case: Book"}
    assert body == "b\n"
    assert frontmatter.parse(frontmatter.dump(meta, body)) == (meta, body)


def test_empty_values_and_lists():
    meta, _ = frontmatter.parse("---\na:\nb: []\nc: [ x ,, y ]\nnocolon\n\n---\n")
    assert meta == {"a": "", "b": [], "c": ["x", "y"]}


def test_empty_body_roundtrip():
    assert frontmatter.parse(frontmatter.dump({"a": "1"}, "")) == ({"a": "1"}, "")
