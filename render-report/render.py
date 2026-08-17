"""Render Periphery scan annotations as a markdown report.

The scan emits GitHub Actions workflow commands, which the runner rewrites in the
log without their file and line attributes. This reads the raw output and renders
it with the blocks in templates/comment.md.
"""

import os
import re
import sys
from pathlib import Path
from string import Template
from urllib.parse import quote, urlencode

# GitHub renders nothing at all once a job summary exceeds 1 MiB.
JOB_SUMMARY_LIMIT = 1024 * 1024

# GitHub rejects an issue comment body longer than this with HTTP 422. The limit counts
# characters, so budgeting in bytes stays on the safe side of it.
COMMENT_LIMIT = 65_536

# The report is rendered once per destination, because a comment is far smaller than a
# job summary. Each budget leaves room for the surrounding document.
BUDGETS = {
    "summary": 900_000,
    "comment": 60_000,
}

# The bug report form lives in a separate repository from the scanned project.
ISSUE_FORM_URL = "https://github.com/periphery-pro/issues/issues/new"
ISSUE_FORM_TEMPLATE = "bug_report.yml"

ANNOTATION = re.compile(
    r"^::warning file=(?P<path>.*?),line=(?P<line>\d+),col=(?P<col>\d+),"
    r"title=(?P<title>.*?)::(?P<message>.*)$"
)


class Blocks(dict):
    """The named blocks of a template file."""

    @classmethod
    def parse(cls, text):
        blocks = cls()
        name = None

        for raw in text.splitlines():
            match = re.fullmatch(r"\[([a-z_]+)\]", raw.strip())
            if match:
                name = match.group(1)
                blocks[name] = []
            elif name is not None:
                blocks[name].append(raw)

        return cls({name: "\n".join(lines).strip() for name, lines in blocks.items()})

    def render(self, name, **fields):
        return Template(self[name]).substitute(**fields)


def parse_annotations(path):
    if not path.exists():
        return []

    results = []

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = ANNOTATION.match(raw)
        if match:
            results.append(match.groupdict())

    return results


def escape_cell(text):
    """Keep a declaration name from breaking out of its table cell.

    Swift operators may contain a pipe, which would otherwise start a new column.
    """
    return text.replace("|", "\\|")


def render_results(blocks, results, blob_url, budget):
    if not results:
        return ""

    header = blocks["results_header"]
    rows = []

    # Reserve the note that appears if the table is cut short, so adding it can never
    # push the document past the budget.
    note = blocks.render("results_truncated", shown=len(results), total=len(results))
    used = len(header.encode("utf-8")) + len(note.encode("utf-8")) + 4

    for result in results:
        row = blocks.render(
            "results_row",
            message=escape_cell(result["message"]),
            path=result["path"],
            # A path may contain characters that would end the markdown link early.
            path_url=quote(result["path"]),
            line=result["line"],
            blob_url=blob_url,
        )

        if used + len(row.encode("utf-8")) + 1 > budget:
            break

        rows.append(row)
        used += len(row.encode("utf-8")) + 1

    body = "\n".join([header, *rows])

    if len(rows) < len(results):
        truncated = blocks.render(
            "results_truncated", shown=len(rows), total=len(results)
        )
        body += f"\n\n{truncated}"

    return body


def bug_report_url(
    blocks,
    *,
    commit,
    commit_url,
    pull_request,
    pull_request_url,
    repository,
    run_url,
    toolchain,
):
    """Build a link that opens the bug report form with the scan context filled in."""
    query = {
        "template": ISSUE_FORM_TEMPLATE,
        "title": blocks.render(
            "bug_report_title", pull_request=pull_request, repository=repository
        ),
        "environment": blocks.render(
            "bug_report_environment",
            commit=commit,
            commit_url=commit_url,
            pull_request=pull_request,
            pull_request_url=pull_request_url,
            repository=repository,
            run_url=run_url,
            short_commit=commit[:7],
            toolchain=toolchain.strip(),
        ),
    }

    return f"{ISSUE_FORM_URL}?{urlencode(query)}"


def render(
    blocks,
    results,
    *,
    baseline_commit,
    blob_url,
    budget,
    commit,
    commit_url,
    pull_request,
    pull_request_url,
    repository,
    run_url,
    toolchain,
):
    name = "headline_results" if results else "headline_empty"
    fields = {}

    if baseline_commit:
        fields = {
            "commit_url": commit_url,
            "sha": baseline_commit,
            "short_sha": baseline_commit[:7],
        }
    else:
        name += "_without_baseline"

    if results:
        fields.update(
            count=len(results),
            noun="result" if len(results) == 1 else "results",
        )

    footer = blocks.render(
        "footer",
        bug_report_url=bug_report_url(
            blocks,
            commit=commit,
            commit_url=commit_url,
            pull_request=pull_request,
            pull_request_url=pull_request_url,
            repository=repository,
            run_url=run_url,
            toolchain=toolchain,
        ),
    )
    headline = blocks.render(name, **fields)

    def document(table):
        rendered = blocks.render(
            "document", footer=footer, headline=headline, results=table
        )
        # Drop the blank line left behind when a section renders empty.
        return re.sub(r"\n{3,}", "\n\n", rendered).strip() + "\n"

    # Everything outside the table is measured rather than estimated, because the
    # footer carries a bug report URL whose length depends on the recorded versions.
    overhead = len(document("").encode("utf-8"))

    return document(render_results(blocks, results, blob_url, budget - overhead))


def main():
    annotations = Path(os.environ["ANNOTATIONS"])
    output = Path(os.environ["OUTPUT"])
    target = os.environ["TARGET"]
    template = Path(os.environ["TEMPLATE"])

    if target not in BUDGETS:
        print(
            f"Unknown target {target!r}; expected one of {', '.join(sorted(BUDGETS))}",
            file=sys.stderr,
        )
        return 1

    if not annotations.exists():
        print(f"No scan output at {annotations}; nothing to render", file=sys.stderr)
        return 0

    blocks = Blocks.parse(template.read_text(encoding="utf-8"))
    results = parse_annotations(annotations)
    toolchain_file = Path(os.environ.get("TOOLCHAIN_FILE", ""))
    toolchain = (
        toolchain_file.read_text(encoding="utf-8", errors="replace")
        if toolchain_file.name and toolchain_file.exists()
        else "Versions were not recorded."
    )

    document = render(
        blocks,
        results,
        baseline_commit=os.environ.get("BASELINE_COMMIT", ""),
        blob_url=os.environ["BLOB_URL"],
        budget=BUDGETS[target],
        commit=os.environ["COMMIT"],
        commit_url=os.environ["COMMIT_URL"],
        pull_request=os.environ["PULL_REQUEST"],
        pull_request_url=os.environ["PULL_REQUEST_URL"],
        repository=os.environ["REPOSITORY"],
        run_url=os.environ["RUN_URL"],
        toolchain=toolchain,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    print(f"Rendered {len(results)} result(s) to {output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
