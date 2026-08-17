import tempfile
import unittest
from pathlib import Path
from unittest import mock

import render

TEMPLATE = Path(__file__).parent / "templates" / "comment.md"

ANNOTATION = (
    "::warning file=Sources/Greeting.swift,line=1,col=8,title=unused::"
    "Unused struct 'Greeting'"
)

CONTEXT = {
    "blob_url": "https://github.com/o/r/blob/head",
    "commit_url": "https://github.com/o/r/commit",
    "logo_url": "https://logo.svg",
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
                "baseline_available",
                "baseline_missing",
                "document",
                "headline_empty",
                "headline_results",
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
            blocks(), results, baseline_commit=baseline_commit, **CONTEXT
        )

    def test_counts_a_single_result_in_the_singular(self):
        self.assertIn("**1 new result.**", self.render(annotations(1)))

    def test_counts_several_results_in_the_plural(self):
        self.assertIn("**3 new results.**", self.render(annotations(3)))

    def test_omits_new_when_there_is_no_baseline(self):
        document = self.render(annotations(3), baseline_commit="")

        self.assertIn("**3 results.**", document)
        self.assertIn("No baseline was available", document)

    def test_names_the_baseline_commit(self):
        document = self.render(annotations(1))

        self.assertIn(
            "Compared with the baseline from "
            "[`a474b02`](https://github.com/o/r/commit/"
            "a474b02db4bf397a4fc3529f5518775a53deb1c0).",
            document,
        )

    def test_links_each_result_to_its_source(self):
        self.assertIn(
            "| Unused function 'helper1()' | "
            "[`Sources/Greeting.swift:1`]"
            "(https://github.com/o/r/blob/head/Sources/Greeting.swift#L1) |",
            self.render(annotations(1)),
        )

    def test_reports_no_results_without_a_table(self):
        document = self.render([])

        self.assertIn("No new unused code detected.", document)
        self.assertNotIn("| Result | Location |", document)

    def test_shows_the_logo_beside_the_title(self):
        self.assertIn(
            '<img src="https://logo.svg" width="24" align="top" alt=""> '
            "Unused Code Report",
            self.render([]),
        )

    def test_leaves_no_blank_line_where_a_section_is_empty(self):
        self.assertNotIn("\n\n\n", self.render([]))


class TruncationTest(unittest.TestCase):
    def render_within(self, budget, results):
        with mock.patch.object(render, "BUDGET", budget):
            return render.render(blocks(), results, baseline_commit="", **CONTEXT)

    def test_keeps_the_budget_below_the_github_limit(self):
        self.assertLess(render.BUDGET, 1024 * 1024)

    def test_emits_every_result_when_they_fit(self):
        document = self.render_within(render.BUDGET, annotations(3))

        self.assertNotIn("Showing", document)
        self.assertEqual(document.count("| Unused function"), 3)

    def test_stops_and_explains_once_the_budget_is_reached(self):
        document = self.render_within(1200, annotations(50))

        self.assertIn("of 50 results. The full list is in the scan log.", document)
        self.assertLess(len(document.encode("utf-8")), 2000)

    def test_counts_only_the_rows_it_kept(self):
        document = self.render_within(1200, annotations(50))
        shown = document.count("| Unused function")

        self.assertIn(f"_Showing {shown} of 50 results.", document)


class MainTest(unittest.TestCase):
    def run_main(self, directory, *, write_annotations=True):
        annotations_path = Path(directory) / "output.txt"
        output_path = Path(directory) / "comment" / "comment.md"

        if write_annotations:
            annotations_path.write_text(ANNOTATION, encoding="utf-8")

        environment = {
            "ANNOTATIONS": str(annotations_path),
            "BASELINE_COMMIT": "a474b02db4bf397a4fc3529f5518775a53deb1c0",
            "BLOB_URL": CONTEXT["blob_url"],
            "COMMIT_URL": CONTEXT["commit_url"],
            "LOGO_URL": CONTEXT["logo_url"],
            "OUTPUT": str(output_path),
            "TEMPLATE": str(TEMPLATE),
        }

        with mock.patch.dict("os.environ", environment, clear=False):
            return render.main(), output_path

    def test_writes_the_report_and_creates_its_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            status, output = self.run_main(directory)

            self.assertEqual(status, 0)
            self.assertIn("Unused struct 'Greeting'", output.read_text())

    def test_succeeds_without_writing_when_the_scan_produced_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            status, output = self.run_main(directory, write_annotations=False)

            self.assertEqual(status, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
