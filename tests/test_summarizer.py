"""Tests for the heuristic summarizer."""

from contextpack.summarizer import summarize, HEAD_LINES, TAIL_LINES


def test_short_file_returned_unchanged():
    content = "line 1\nline 2\nline 3\n"
    assert summarize("a.py", content) == content


def test_file_at_threshold_returned_unchanged():
    content = "\n".join(f"line {i}" for i in range(HEAD_LINES + TAIL_LINES))
    assert summarize("a.py", content) == content


def test_long_file_includes_omission_marker():
    content = "\n".join(f"line {i}" for i in range(200))
    out = summarize("a.py", content)
    assert "lines omitted" in out
    assert "heuristic summary" in out


def test_long_file_keeps_head_and_tail():
    content = "\n".join(f"line {i}" for i in range(200))
    out = summarize("a.py", content)
    assert "line 0" in out
    assert "line 199" in out


def test_extracts_python_def_and_class():
    content = "\n".join(["x = 1"] * 30) + "\ndef do_thing(x):\n    pass\nclass Worker:\n    pass\n"
    out = summarize("a.py", content)
    assert "def do_thing" in out
    assert "class Worker" in out


def test_extracts_async_def():
    content = "\n".join(["x = 1"] * 30) + "\nasync def fetch(url):\n    pass\n"
    out = summarize("a.py", content)
    assert "def fetch" in out


def test_extracts_js_function_and_class():
    content = "\n".join([f"// line {i}" for i in range(40)]) + """
function hello() {}
export class Greeter {}
"""
    out = summarize("a.js", content)
    assert "function hello" in out
    assert "class Greeter" in out


def test_extracts_js_arrow_const():
    content = "\n".join([f"// line {i}" for i in range(40)]) + """
const greet = (name) => `hi ${name}`
export const fetcher = async (u) => fetch(u)
"""
    out = summarize("a.ts", content)
    assert "const greet" in out
    assert "const fetcher" in out


def test_extracts_go_func():
    content = "\n".join([f"// line {i}" for i in range(40)]) + """
func main() {}
func (s *Server) Start() {}
"""
    out = summarize("a.go", content)
    assert "func main" in out
    assert "func Start" in out


def test_extracts_rust_fn():
    content = "\n".join([f"// line {i}" for i in range(40)]) + """
pub fn entrypoint() {}
fn helper() {}
"""
    out = summarize("a.rs", content)
    assert "fn entrypoint" in out
    assert "fn helper" in out


def test_does_not_duplicate_symbols():
    """The extracted symbol list should dedupe; the original lines may
    still appear in the head/tail context, which is fine."""
    content = "\n".join([f"// line {i}" for i in range(40)]) + """
def repeated(): pass
def repeated(): pass
"""
    out = summarize("a.py", content)
    # Symbol list should contain `repeated` exactly once.
    assert out.count("  - def repeated") == 1
