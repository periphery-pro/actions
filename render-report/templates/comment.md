Blocks are delimited by a [name] line. Everything above the first block is
ignored, so this paragraph is a comment. Placeholders use $name and are
substituted by render.py; write $$ for a literal dollar sign.

[document]
## Unused Code Report

$headline

$results

$footer

[headline_results]
**$count new $noun** compared with [`$short_sha`]($commit_url/$sha)

[headline_results_without_baseline]
**$count $noun**. No baseline was available, so every result is reported.

[headline_empty]
No new unused code detected compared with [`$short_sha`]($commit_url/$sha).

[headline_empty_without_baseline]
No unused code detected.

[results_header]
| Result | Location |
| :- | :- |

[results_row]
| $message | [$path:$line]($blob_url/$path_url#L$line) |

[results_remainder]
<details>
<summary>Show remaining $count results</summary>

| Result | Location |
| :- | :- |
$rows
$truncated
</details>

[results_truncated]
_Showing $shown of $total results. The full list is in the scan log._

[footer]
> Scanned by [Periphery](https://github.com/periphery-pro/actions) · [Report a bug]($bug_report_url)

[bug_report_title]
Inaccurate result in $repository#$pull_request

[bug_report_environment]
$toolchain

Scan context
------------
Pull request: [$repository#$pull_request]($pull_request_url)
Commit: [$short_commit]($commit_url/$commit)
Run: $run_url
