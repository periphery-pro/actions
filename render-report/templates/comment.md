Blocks are delimited by a [name] line. Everything above the first block is
ignored, so this paragraph is a comment. Placeholders use $name and are
substituted by render.py; write $$ for a literal dollar sign.

[document]
## <img src="$logo_url" width="24" align="top" alt=""> Unused Code Report

$headline

$baseline

$results

[headline_results]
**$count $qualifier$noun.**

[headline_empty]
No ${qualifier}unused code detected.

[baseline_available]
Compared with the baseline from [`$short_sha`]($commit_url/$sha).

[baseline_missing]
No baseline was available, so every result is reported.

[results_header]
| Result | Location |
| :- | :- |

[results_row]
| `$message` | [`$path:$line`]($blob_url/$path#L$line) |

[results_truncated]
_Showing $shown of $total results. The full list is in the scan log._
