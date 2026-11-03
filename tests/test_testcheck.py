"""Test-value checks of a delivery (INIT-03 §7.7, G5) — declaration-based, nothing is run.

The fixture test files written into tmp_path are DATA: some intentionally
contain worthless tests (`assert True`, no assertion, ...) that must be rejected.
"""
from pathlib import Path

from _shared import testcheck
from _shared.cards import Card

STORY = Card("ST-001", "story", "Book a visit", "3-doing", {"id": "ST-001"},
             "## Acceptance criteria\n\n"
             "- **ST-001/AC-1**: Patient picks a slot\n"
             "- **ST-001/AC-2**: Patient gets a confirmation\n", Path())
TASK = Card("TK-001", "task", "Booking", "3-doing", {"id": "TK-001", "parent": "ST-001"},
            "## Description\n\nDo it.\n\n## Covers\n\n- ST-001/AC-1\n- ST-001/AC-2\n", Path())
BUG = Card("BUG-007", "bug", "Double booking", "3-doing", {"id": "BUG-007"},
           "## Symptom\n\nTwo bookings.\n\n## Reproduction\n\nBook twice.\n", Path())

GOOD_PY = '''\
import pytest
from app.booking import book, confirm


def test_book_slot_st_001_ac_1():
    assert book("09:00") == "booked"


# covers ST-001/AC-2
def test_confirmation_sent():
    with pytest.raises(ValueError):
        confirm(None)


class TestBooking:
    def test_method(self):
        """ST-001/AC-1: a booked slot is returned."""
        self.assertEqual(book("10:00"), "booked")
'''


def delivery(tests, red=None, *, drop=()):
    """A delivery document; `tests` = [(ref, ids)], red defaults to one block per test."""
    red = {ref: "E   AssertionError" for ref, _ in tests} if red is None else red
    parts = {
        "What was done": "Implemented booking.",
        "Files changed": "- app/booking.py",
        "Tests": "\n".join(f"- {ref} — covers {', '.join(ids)}" for ref, ids in tests),
        "Red evidence": "\n\n".join(f"### {ref}\n\n```\n{out}\n```" for ref, out in red.items()),
    }
    return "\n\n".join(f"## {k}\n\n{v}" for k, v in parts.items() if k not in drop) + "\n"


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def check(root, text, task=TASK, story=STORY):
    return testcheck.check_delivery(testcheck.parse_delivery(text), task, story, root)


def bad_test(root, body, name="test_bad_st_001_ac_1"):
    """A test file with one good test (covers AC-2) plus one test under scrutiny (AC-1)."""
    write(root, "tests/test_x.py",
          "from app.booking import book\n\n\n"
          "def test_good_st_001_ac_2():\n    assert book('a') == 'booked'\n\n\n"
          f"def {name}():\n{body}\n")
    return check(root, delivery([("tests/test_x.py::test_good_st_001_ac_2", ["ST-001/AC-2"]),
                                 (f"tests/test_x.py::{name}", ["ST-001/AC-1"])]))


def test_good_python_test_passes(tmp_path):
    write(tmp_path, "tests/test_booking.py", GOOD_PY)
    doc = delivery([("tests/test_booking.py::test_book_slot_st_001_ac_1", ["ST-001/AC-1"]),
                    ("tests/test_booking.py::test_confirmation_sent", ["ST-001/AC-2"]),
                    ("tests/test_booking.py::TestBooking::test_method", ["ST-001/AC-1"])])
    parsed = testcheck.parse_delivery(doc)
    assert [t[:2] for t in parsed.tests][2] == ("tests/test_booking.py", "TestBooking::test_method")
    assert parsed.tests[0][2] == ["ST-001/AC-1"]
    assert check(tmp_path, doc) == []
    info = testcheck.find_test(tmp_path, "tests/test_booking.py", "test_confirmation_sent")
    assert info.has_assertion and not info.trivial and info.calls_code


def test_assert_true_rejected(tmp_path):
    problems = bad_test(tmp_path, "    book('a')\n    assert True")
    assert problems == ["tests/test_x.py::test_bad_st_001_ac_1: only asserts constants (trivial)"]
    problems = bad_test(tmp_path, "    book('a')\n    self.assertTrue(True)")
    assert problems == ["tests/test_x.py::test_bad_st_001_ac_1: only asserts constants (trivial)"]


def test_constant_comparison_rejected(tmp_path):
    problems = bad_test(tmp_path, "    book('a')\n    assert 1 == 1\n    assert 'a' in ['a', 'b']")
    assert problems == ["tests/test_x.py::test_bad_st_001_ac_1: only asserts constants (trivial)"]


def test_no_assertion_rejected(tmp_path):
    problems = bad_test(tmp_path, "    book('a')")
    assert problems == ["tests/test_x.py::test_bad_st_001_ac_1: has no assertion"]


def test_no_project_call_rejected(tmp_path):
    problems = bad_test(tmp_path, "    x = len([1, 2])\n    assert x == sorted([2, 1])[0] + 1")
    assert problems == ["tests/test_x.py::test_bad_st_001_ac_1: never calls project code"]


def test_test_without_criterion_reference_rejected(tmp_path):
    problems = bad_test(tmp_path, "    assert book('a') == 'booked'", name="test_unlinked")
    assert problems == ["tests/test_x.py::test_unlinked: does not reference ST-001/AC-1",
                        "Criterion ST-001/AC-1 (task Covers) has no test."]
    # declaring an ID that is not a criterion of the story
    write(tmp_path, "tests/test_y.py", "from app import f\n\n\n"
          "def test_ac_9_st_001_ac_9():\n    assert f() == 1\n\n\n"
          "def test_st_001_ac_1():\n    assert f() == 1\n\n\n"
          "def test_st_001_ac_2():\n    assert f() == 1\n")
    problems = check(tmp_path, delivery([("tests/test_y.py::test_ac_9_st_001_ac_9", ["ST-001/AC-9"]),
                                         ("tests/test_y.py::test_st_001_ac_1", ["ST-001/AC-1"]),
                                         ("tests/test_y.py::test_st_001_ac_2", ["ST-001/AC-2"])]))
    assert problems == ["tests/test_y.py::test_ac_9_st_001_ac_9: ST-001/AC-9 is not a criterion of ST-001"]


def test_uncovered_criterion_reported(tmp_path):
    write(tmp_path, "tests/test_booking.py", GOOD_PY)
    problems = check(tmp_path, delivery(
        [("tests/test_booking.py::test_book_slot_st_001_ac_1", ["ST-001/AC-1"])]))
    assert problems == ["Criterion ST-001/AC-2 (task Covers) has no test."]
    # bugs: the regression test must declare (and reference) the bug ID
    write(tmp_path, "tests/test_bug.py", "from app.booking import book\n\n\n"
          "def test_no_double_booking_bug_007():\n    assert book('a') != book('a')\n")
    ok = delivery([("tests/test_bug.py::test_no_double_booking_bug_007", ["BUG-007"])])
    assert check(tmp_path, ok, task=BUG, story=None) == []
    other = delivery([("tests/test_booking.py::test_book_slot_st_001_ac_1", ["ST-001/AC-1"])])
    assert check(tmp_path, other, task=BUG, story=STORY) == [
        "No test references the bug ID BUG-007."]


def test_missing_red_evidence_reported(tmp_path):
    write(tmp_path, "tests/test_booking.py", GOOD_PY)
    tests = [("tests/test_booking.py::test_book_slot_st_001_ac_1", ["ST-001/AC-1"]),
             ("tests/test_booking.py::test_confirmation_sent", ["ST-001/AC-2"])]
    doc = delivery(tests, red={tests[0][0]: ""})
    assert check(tmp_path, doc) == [
        "tests/test_booking.py::test_book_slot_st_001_ac_1: no red evidence",
        "tests/test_booking.py::test_confirmation_sent: no red evidence"]
    # a missing section is a document-level problem
    doc = delivery(tests, drop=("Red evidence", "Files changed"))
    problems = check(tmp_path, doc)
    assert problems[0] == "The delivery lacks required sections: ## Files changed, ## Red evidence"


GOOD_JS = '''\
import { book } from "../src/booking";

describe("booking", () => {
  // ST-001/AC-1
  test("books a slot", () => {
    expect(book("09:00")).toBe("booked");
  });

  it("ST-001/AC-2 sends a confirmation", async () => {
    const res = await book("10:00");
    expect(res.confirmed).toBe(true);
  });

  test("ST-001/AC-1 trivially true", () => {
    book("x");
    expect(true).toBe(true);
  });
});
'''


def test_js_expect_true_rejected_and_good_js_passes(tmp_path):
    write(tmp_path, "web/booking.test.ts", GOOD_JS)
    good = [("web/booking.test.ts::books a slot", ["ST-001/AC-1"]),
            ("web/booking.test.ts::ST-001/AC-2 sends a confirmation", ["ST-001/AC-2"])]
    assert check(tmp_path, delivery(good)) == []
    bad = good + [("web/booking.test.ts::ST-001/AC-1 trivially true", ["ST-001/AC-1"])]
    assert check(tmp_path, delivery(bad)) == [
        "web/booking.test.ts::ST-001/AC-1 trivially true: only asserts constants (trivial)"]
    info = testcheck.find_test(tmp_path, "web/booking.test.ts", "ST-001/AC-1 trivially true")
    assert info.has_assertion and info.trivial and info.calls_code


def test_missing_or_outside_file_is_a_problem_not_crash(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    write(tmp_path, "elsewhere/test_e.py", "def test_st_001_ac_1():\n    assert f()\n")
    write(root, "tests/test_ok.py", GOOD_PY)
    write(root, "tests/broken.py", "def test_st_001_ac_1(:\n")
    write(root, "spec/booking_spec.rb", "it 'books ST-001/AC-2' do\n  expect(book).to eq 1\nend\n")
    doc = delivery([("tests/missing.py::test_st_001_ac_1", ["ST-001/AC-1"]),
                    ("../elsewhere/test_e.py::test_st_001_ac_1", ["ST-001/AC-1"]),
                    (f"{tmp_path / 'elsewhere' / 'test_e.py'}::test_st_001_ac_1", ["ST-001/AC-1"]),
                    ("tests/test_ok.py::test_nope", ["ST-001/AC-1"]),
                    ("tests/broken.py::test_st_001_ac_1", ["ST-001/AC-1"]),
                    ("spec/booking_spec.rb::books ST-001/AC-2", ["ST-001/AC-2"])])
    parsed = testcheck.parse_delivery(doc)
    assert testcheck.check_delivery(parsed, TASK, STORY, root) == [
        "tests/missing.py::test_st_001_ac_1: file not found",
        "../elsewhere/test_e.py::test_st_001_ac_1: outside the project",
        f"{tmp_path / 'elsewhere' / 'test_e.py'}::test_st_001_ac_1: outside the project",
        "tests/test_ok.py::test_nope: test not found",
        "tests/broken.py::test_st_001_ac_1: test not found",
        "Criterion ST-001/AC-1 (task Covers) has no test."]
    assert testcheck.find_test(root, "../elsewhere/test_e.py", "test_st_001_ac_1") is None
    assert testcheck.delivery_warnings(parsed, root) == [
        "spec/booking_spec.rb::books ST-001/AC-2: language not analysed "
        "(only the test name was checked)"]
    # an empty or garbage document never crashes either
    assert check(root, "")[0].startswith("The delivery lacks required sections")
    assert check(root, "## Tests\n\n- nonsense\n## Red evidence\n") != []


def test_id_pattern_variants():
    ac = testcheck.id_pattern("ST-001/AC-1")
    for text in ("ST-001/AC-1", "test_st_001_ac_1_books", "ST001-AC1", "st-001-ac-1",
                 "# covers st001/ac1"):
        assert ac.search(text), text
    for text in ("ST-001/AC-12", "ST-0012/AC-1", "ST-002/AC-1", "XST-001/AC-1"):
        assert not ac.search(text), text
    bug = testcheck.id_pattern("BUG-007")
    assert bug.search("test_bug_007_regression") and bug.search("BUG-007") and bug.search("BUG007")
    assert not bug.search("BUG-0071")


# ─── review fix round 1: regressions ─────────────────────────────────────

def one_file(root, source, tests, task=TASK, story=STORY, rel="tests/test_r.py"):
    """Check `tests` [(name, ids)] of a single fixture file."""
    write(root, rel, source)
    return check(root, delivery([(f"{rel}::{n}", ids) for n, ids in tests]), task, story)


def test_every_declared_id_must_be_referenced(tmp_path):
    src = "from app import book\n\n\ndef test_st_001_ac_1():\n    assert book('a') == 1\n"
    assert one_file(tmp_path, src, [("test_st_001_ac_1", ["ST-001/AC-1", "ST-001/AC-2"])]) == [
        "tests/test_r.py::test_st_001_ac_1: does not reference ST-001/AC-2",
        "Criterion ST-001/AC-2 (task Covers) has no test."]
    assert one_file(tmp_path, src, [("test_st_001_ac_1", ["BUG-007", "ST-001/AC-1"])],
                    task=BUG, story=STORY) == [
        "tests/test_r.py::test_st_001_ac_1: does not reference BUG-007",
        "No test references the bug ID BUG-007."]


def test_delivery_name_suffix_is_not_a_reference(tmp_path):
    src = ("from app import book\n\n\ndef test_x():\n    assert book('a') == 1\n\n\n"
           "def test_st_001_ac_2():\n    assert book('b') == 1\n")
    assert one_file(tmp_path, src, [("test_x[ST-001/AC-1]", ["ST-001/AC-1"]),
                                    ("test_st_001_ac_2", ["ST-001/AC-2"])]) == [
        "tests/test_r.py::test_x[ST-001/AC-1]: does not reference ST-001/AC-1",
        "Criterion ST-001/AC-1 (task Covers) has no test."]


def test_fixtures_and_setup_objects_count_as_project_code(tmp_path):
    src = (
        "import unittest\n\n\n"
        "def test_fixture_st_001_ac_1(booking):\n    assert booking.status == 'ok'\n\n\n"
        "class TestB(unittest.TestCase):\n"
        "    def test_attr_st_001_ac_2(self):\n        self.assertEqual(self.b.status, 'new')\n\n"
        "    def test_raises_st_001_ac_2(self):\n        self.assertRaises(ValueError, self.b.cancel)\n\n"
        "    def test_with_st_001_ac_2(self):\n"
        "        with self.assertRaises(ValueError):\n            self.b.cancel()\n")
    assert one_file(tmp_path, src, [("test_fixture_st_001_ac_1", ["ST-001/AC-1"]),
                                    ("TestB::test_attr_st_001_ac_2", ["ST-001/AC-2"]),
                                    ("TestB::test_raises_st_001_ac_2", ["ST-001/AC-2"]),
                                    ("TestB::test_with_st_001_ac_2", ["ST-001/AC-2"])]) == []


def test_tautologies_rejected(tmp_path):
    for body in ("x = book('a')\n    assert x == x", "f = book\n    f('a')\n    assert f is f",
                 "book('a')\n    assert True or book('b')", "book('a')\n    assert not (1 > 2)",
                 "book('a')\n    foo = 5\n    assert foo is not None"):
        assert bad_test(tmp_path, f"    {body}") == [
            "tests/test_x.py::test_bad_st_001_ac_1: only asserts constants (trivial)"], body
    # same expression on both sides but with calls: the two calls may differ (side effects)
    assert bad_test(tmp_path, "    assert book('a') != book('a')") == []


def test_method_calls_named_like_builtins_count_as_code(tmp_path):
    assert bad_test(tmp_path, "    assert svc.open('x') == 1") == []
    assert bad_test(tmp_path, "    assert df.sum() == 3") == []


def test_pytest_aliases_are_assertions(tmp_path):
    src = ("from pytest import raises\nimport pytest as pt\nfrom app import book\n\n\n"
           "def test_st_001_ac_1():\n    with raises(ValueError):\n        book(None)\n\n\n"
           "def test_st_001_ac_2():\n    with pt.raises(ValueError):\n        book(None)\n")
    assert one_file(tmp_path, src, [("test_st_001_ac_1", ["ST-001/AC-1"]),
                                    ("test_st_001_ac_2", ["ST-001/AC-2"])]) == []


def test_declared_ids_are_normalised(tmp_path):
    src = ("from app import book\n\n\ndef test_st_001_ac_1():\n    assert book('a') == 1\n\n\n"
           "def test_st_001_ac_2():\n    assert book('b') == 1\n")
    assert one_file(tmp_path, src, [("test_st_001_ac_1", ["st-001/ac-1"]),
                                    ("test_st_001_ac_2", ["ST001-AC2"])]) == []
    bug = "from app import book\n\n\ndef test_bug_007():\n    assert book('a') == 1\n"
    assert one_file(tmp_path, bug, [("test_bug_007", ["bug_007"])], task=BUG, story=None) == []
