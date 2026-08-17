import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import quote_plus

import render

TEMPLATE = Path(__file__).parent / "templates" / "comment.md"

ANNOTATION = (
    "::warning file=Sources/Greeting.swift,line=1,col=8,title=unused::"
    "Unused struct 'Greeting'"
)

CONTEXT = {
    "blob_url": "https://github.com/o/r/blob/head",
    "commit": "2b8bde259f74b508ac116633ef9a1e9c7db72dfd",
    "commit_url": "https://github.com/o/r/commit",
    "pull_request": "10",
    "repository": "periphery-pro/actions-test",
    "run_url": "https://github.com/o/r/actions/runs/99",
    "toolchain": "Periphery 1.1.0\nSwift 6.0.3",
}


def blocks():
    return render.Blocks.parse(TEMPLATE.read_text(encoding="utf-8"))


def annotations(count, path="Sources/Greeting.swift"):
    return [
        {
            "path": path,
            "line": str(index),
            "col": "8",
            "title": "unused",
            "message": f"Unused function 'helper{index}()'",
        }
        for index in range(1, count + 1)
    ]


class BlocksTest(unittest.TestCase):
    def test_ignores_the_preamble_before_the_first_block(self):
        parsed = render.Blocks.parse("a comment\n\n[only]\nbody\n")

        self.assertEqual(list(parsed), ["only"])
        self.assertEqual(parsed["only"], "body")

    def test_template_defines_every_block_the_renderer_uses(self):
        self.assertEqual(
            sorted(blocks()),
            [
                "bug_report_environment",
                "bug_report_title",
                "document",
                "footer",
                "headline_empty",
                "headline_empty_without_baseline",
                "headline_results",
                "headline_results_without_baseline",
                "results_header",
                "results_row",
                "results_truncated",
            ],
        )


class ParseAnnotationsTest(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "output.txt"
            path.write_text(text, encoding="utf-8")
            return render.parse_annotations(path)

    def test_reads_the_location_and_message(self):
        self.assertEqual(
            self.parse(ANNOTATION),
            [
                {
                    "path": "Sources/Greeting.swift",
                    "line": "1",
                    "col": "8",
                    "title": "unused",
                    "message": "Unused struct 'Greeting'",
                }
            ],
        )

    def test_ignores_lines_that_are_not_annotations(self):
        text = f"Building...\n{ANNOTATION}\nRemovable unused code: 10 of 11\n"

        self.assertEqual(len(self.parse(text)), 1)

    def test_reads_a_path_containing_a_comma(self):
        text = "::warning file=Sources/A,B.swift,line=9,col=2,title=unused::Unused function 'x()'"

        self.assertEqual(self.parse(text)[0]["path"], "Sources/A,B.swift")

    def test_reads_a_message_containing_a_double_colon(self):
        text = "::warning file=A.swift,line=1,col=1,title=unused::Unused function 'a::b()'"

        self.assertEqual(self.parse(text)[0]["message"], "Unused function 'a::b()'")

    def test_returns_nothing_for_a_missing_file(self):
        self.assertEqual(render.parse_annotations(Path("/nonexistent")), [])


class RenderTest(unittest.TestCase):
    def render(self, results, baseline_commit="a474b02db4bf397a4fc3529f5518775a53deb1c0"):
        return render.render(
            blocks(),
            results,
            baseline_commit=baseline_commit,
            budget=render.BUDGETS["summary"],
            **CONTEXT,
        )

    def test_counts_a_single_result_in_the_singular(self):
        self.assertIn("**1 new result** compared with ", self.render(annotations(1)))

    def test_counts_several_results_in_the_plural(self):
        self.assertIn("**3 new results** compared with ", self.render(annotations(3)))

    def test_omits_new_when_there_is_no_baseline(self):
        document = self.render(annotations(3), baseline_commit="")

        self.assertIn("**3 results**. No baseline was available", document)

    def test_names_the_baseline_commit(self):
        document = self.render(annotations(1))

        self.assertIn(
            "compared with [`a474b02`](https://github.com/o/r/commit/"
            "a474b02db4bf397a4fc3529f5518775a53deb1c0).",
            document,
        )

    def test_links_each_result_to_its_source(self):
        self.assertIn(
            "| `Unused function 'helper1()'` | "
            "[`Sources/Greeting.swift:1`]"
            "(https://github.com/o/r/blob/head/Sources/Greeting.swift#L1) |",
            self.render(annotations(1)),
        )

    def test_reports_no_results_without_a_table(self):
        document = self.render([])

        self.assertIn("No new unused code detected compared with ", document)
        self.assertNotIn("| Result | Location |", document)

    def test_escapes_a_pipe_so_it_cannot_open_a_column(self):
        results = annotations(1)
        results[0]["message"] = "Unused function '|=(_:_:)'"
        row = [
            line
            for line in self.render(results).splitlines()
            if line.startswith("| `")
        ][0]

        self.assertIn("\\|=", row)
        self.assertEqual(row.count("|") - row.count("\\|"), 3)

    def test_renders_the_message_as_code(self):
        row = [
            line
            for line in self.render(annotations(1)).splitlines()
            if line.startswith("| `")
        ][0]

        self.assertTrue(row.startswith("| `Unused function 'helper1()'` |"))

    def test_percent_encodes_a_path_in_the_link_target(self):
        results = annotations(1, path="Sources/My Module/A(1).swift")
        row = [l for l in self.render(results).splitlines() if l.startswith("| `")][0]

        # Displayed verbatim, encoded in the target so the link cannot end early.
        self.assertIn("[`Sources/My Module/A(1).swift:1`]", row)
        self.assertIn("/Sources/My%20Module/A%281%29.swift#L1)", row)

    def test_leaves_no_blank_line_where_a_section_is_empty(self):
        self.assertNotIn("\n\n\n", self.render([]))

    def test_credits_periphery_at_the_end(self):
        self.assertIn(
            "> Generated by [Periphery](https://github.com/periphery-pro/actions) ·",
            self.render(annotations(1)),
        )

    def test_offers_a_bug_report_link(self):
        self.assertIn("[Report a bug](https://github.com/periphery-pro/issues/issues/new?", self.render([]))

    def test_bug_report_selects_the_issue_form(self):
        self.assertIn("template=bug_report.yml", self.render([]))

    def test_bug_report_title_names_the_repository_and_pull_request(self):
        self.assertIn(
            quote_plus("periphery-pro/actions-test#10"),
            self.render([]),
        )

    def test_bug_report_carries_the_scan_context(self):
        document = self.render([])

        for expected in ["Periphery 1.1.0", "Swift 6.0.3", "Repository: periphery-pro/actions-test",
                         "Commit: 2b8bde259f74b508ac116633ef9a1e9c7db72dfd",
                         "Run: https://github.com/o/r/actions/runs/99"]:
            self.assertIn(quote_plus(expected), document)

    def test_bug_report_url_is_percent_encoded(self):
        # A raw newline or space would end the markdown link early.
        link = self.render([]).split("[Report a bug](")[1].split(")")[0]

        self.assertNotIn(" ", link)
        self.assertNotIn("\n", link)

    def test_credits_periphery_even_with_no_results(self):
        self.assertIn("> Generated by [Periphery](https://github.com/periphery-pro/actions)", self.render([]))


class TruncationTest(unittest.TestCase):
    def render_within(self, budget, results):
        return render.render(
            blocks(), results, baseline_commit="", budget=budget, **CONTEXT
        )

    def test_summary_budget_stays_below_the_job_summary_limit(self):
        self.assertLess(render.BUDGETS["summary"], render.JOB_SUMMARY_LIMIT)

    def test_comment_budget_stays_below_the_comment_limit(self):
        self.assertLess(render.BUDGETS["comment"], render.COMMENT_LIMIT)

    def test_a_comment_sized_report_fits_in_a_comment(self):
        document = self.render_within(
            render.BUDGETS["comment"], annotations(20_000)
        )

        self.assertLess(len(document), render.COMMENT_LIMIT)
        self.assertIn("of 20000 results.", document)

    def test_a_summary_sized_report_would_not_fit_in_a_comment(self):
        # The two destinations need separate budgets; this is why.
        document = self.render_within(
            render.BUDGETS["summary"], annotations(20_000)
        )

        self.assertGreater(len(document), render.COMMENT_LIMIT)
        self.assertLess(len(document.encode("utf-8")), render.JOB_SUMMARY_LIMIT)

    def test_emits_every_result_when_they_fit(self):
        document = self.render_within(render.BUDGETS["summary"], annotations(3))

        self.assertNotIn("Showing", document)
        self.assertEqual(document.count("| `Unused function"), 3)

    def test_stops_and_explains_once_the_budget_is_reached(self):
        document = self.render_within(1200, annotations(50))

        self.assertIn("of 50 results. The full list is in the scan log.", document)
        self.assertLess(len(document.encode("utf-8")), 2000)

    def test_counts_only_the_rows_it_kept(self):
        document = self.render_within(1200, annotations(50))
        shown = document.count("| `Unused function")

        self.assertIn(f"_Showing {shown} of 50 results.", document)


class MainTest(unittest.TestCase):
    def run_main(self, directory, *, target="comment", write_annotations=True):
        annotations_path = Path(directory) / "output.txt"
        output_path = Path(directory) / "comment" / "comment.md"

        if write_annotations:
            annotations_path.write_text(ANNOTATION, encoding="utf-8")

        environment = {
            "ANNOTATIONS": str(annotations_path),
            "BASELINE_COMMIT": "a474b02db4bf397a4fc3529f5518775a53deb1c0",
            "BLOB_URL": CONTEXT["blob_url"],
            "COMMIT": CONTEXT["commit"],
            "COMMIT_URL": CONTEXT["commit_url"],
            "PULL_REQUEST": CONTEXT["pull_request"],
            "REPOSITORY": CONTEXT["repository"],
            "RUN_URL": CONTEXT["run_url"],
            "OUTPUT": str(output_path),
            "TARGET": target,
            "TEMPLATE": str(TEMPLATE),
        }

        with mock.patch.dict("os.environ", environment, clear=False):
            return render.main(), output_path

    def test_writes_the_report_and_creates_its_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            status, output = self.run_main(directory)

            self.assertEqual(status, 0)
            self.assertIn("Unused struct 'Greeting'", output.read_text())

    def test_rejects_an_unknown_target(self):
        with tempfile.TemporaryDirectory() as directory:
            status, output = self.run_main(directory, target="elsewhere")

            self.assertEqual(status, 1)
            self.assertFalse(output.exists())

    def test_succeeds_without_writing_when_the_scan_produced_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            status, output = self.run_main(directory, write_annotations=False)

            self.assertEqual(status, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
