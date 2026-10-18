from __future__ import annotations

from leakguard_core.gitsource import parse_log

SHA = "a" * 40
BLOB = "b" * 40


def test_parse_log_tracks_line_numbers_binaries_and_tricky_lines() -> None:
    lines = [
        "\x1eLGCOMMIT " + SHA,
        "Dev Name",
        "dev" + "@" + "example.com",
        "Dev Name",
        "dev" + "@" + "example.com",
        "\x1fLGMSG",
        "feat: add notes",
        "",
        "Body line\x1fLGEND",
        "",
        ":000000 100644 " + "0" * 40 + " " + "c" * 40 + " A\tdocs/notes.md",
        ":000000 100644 " + "0" * 40 + " " + BLOB + " A\tsamples/a.docx",
        "",
        "diff --git a/docs/notes.md b/docs/notes.md",
        "new file mode 100644",
        "--- /dev/null",
        "+++ b/docs/notes.md",
        "@@ -0,0 +1,3 @@",
        "+first line",
        "+++ looks like a header but is content",
        "+third line",
        "diff --git a/samples/a.docx b/samples/a.docx",
        "new file mode 100644",
        "Binary files /dev/null and b/samples/a.docx differ",
    ]
    commits = list(parse_log(lines))
    assert len(commits) == 1
    commit = commits[0]
    assert commit.sha == SHA and commit.author_name == "Dev Name"
    assert commit.message == "feat: add notes\n\nBody line"
    notes = commit.files["docs/notes.md"]
    assert notes.lines == [
        (1, "first line"),
        (2, "++ looks like a header but is content"),
        (3, "third line"),
    ]
    binary = commit.files["samples/a.docx"]
    assert binary.binary and binary.blob == BLOB


def test_parse_log_context_and_removed_lines_keep_numbering() -> None:
    lines = [
        "\x1eLGCOMMIT " + SHA,
        "A",
        "a" + "@" + "example.com",
        "A",
        "a" + "@" + "example.com",
        "\x1fLGMSG",
        "edit\x1fLGEND",
        "diff --git a/x.txt b/x.txt",
        "--- a/x.txt",
        "+++ b/x.txt",
        "@@ -1,3 +1,3 @@",
        " keep",
        "-old",
        "+new",
        " tail",
        "\\ No newline at end of file",
    ]
    commit = next(iter(parse_log(lines)))
    assert commit.files["x.txt"].lines == [(2, "new")]
