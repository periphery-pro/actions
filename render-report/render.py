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
    used = len(header) + 1000

    for result in results:
        row = blocks.render(
            "results_row",
            message=escape_cell(result["message"]),
            path=result["path"],
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


def render(blocks, results, *, baseline_commit, blob_url, budget, commit_url, logo_url):
    qualifier = "new " if baseline_commit else ""

    if results:
        headline = blocks.render(
            "headline_results",
            count=len(results),
            qualifier=qualifier,
            noun="result" if len(results) == 1 else "results",
        )
    else:
        headline = blocks.render("headline_empty", qualifier=qualifier)

    if baseline_commit:
        baseline = blocks.render(
            "baseline_available",
            commit_url=commit_url,
            sha=baseline_commit,
            short_sha=baseline_commit[:7],
        )
    else:
        baseline = blocks["baseline_missing"]

    document = blocks.render(
        "document",
        baseline=baseline,
        headline=headline,
        logo_url=logo_url,
        results=render_results(blocks, results, blob_url, budget),
    )

    # Drop the blank line left behind when a section renders empty.
    return re.sub(r"\n{3,}", "\n\n", document).strip() + "\n"


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

    document = render(
        blocks,
        results,
        baseline_commit=os.environ.get("BASELINE_COMMIT", ""),
        blob_url=os.environ["BLOB_URL"],
        budget=BUDGETS[target],
        commit_url=os.environ["COMMIT_URL"],
        logo_url=os.environ["LOGO_URL"],
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    print(f"Rendered {len(results)} result(s) to {output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
