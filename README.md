# Periphery GitHub Actions

The official reusable workflow for scanning **public GitHub repositories** with
[Periphery](https://periphery.pro). On pull requests, it compares the scan with
an automatically recorded baseline from the merge-base commit and reports only
issues introduced by the pull request. Results appear as inline GitHub
annotations and in the job summary, and optionally as a pull-request comment, so
a project can adopt Periphery without first fixing all of its existing unused
code.

## Configuration

The workflow checks out the caller repository and runs the scan from its root.
Put your Periphery configuration in `.periphery.yml` at that root; the CLI
discovers it automatically, so scan configuration stays versioned with the
repository being scanned.

```yaml
on:
  pull_request:
  push:
    branches: [main]

jobs:
  periphery:
    permissions:
      actions: read
      contents: read
      id-token: write
    uses: periphery-pro/actions/.github/workflows/scan.yml@v1
```

Pull-request runs compare against a baseline; push runs record one. The caller
decides which pushes record baselines, so include the branches you merge into.
Each baseline artifact is keyed by commit SHA and follows the caller
repository's GitHub Actions retention setting, which defaults to 90 days for
public repositories.

### Inputs

All inputs are optional and are passed under `with:`.

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `fetch_depth` | number | `0` | Git history depth fetched from the pull-request head and base. `0` fetches the complete history, which reliably identifies a pull request's merge base. Set a positive value to limit the checkout for large repositories — it must be deep enough to reach the merge-base commit, or the baseline lookup fails and the scan is skipped. |
| `checkout_submodules` | boolean | `false` | Recursively check out the caller repository's Git submodules before scanning. Enable this when the build needs them. |
| `runner` | string | `macos-15` | GitHub-hosted macOS runner label to scan on, for example `macos-26`, or a [larger runner](https://docs.github.com/en/actions/using-github-hosted-runners/using-larger-runners) label such as `macos-15-xlarge` where the repository has access to one. |
| `xcode_version` | string | empty | Xcode version to build with, for example `26.3`. It must match an `/Applications/Xcode_<version>.app` install on the selected [runner image](https://github.com/actions/runner-images#available-images); the job fails and lists the installed versions otherwise. By default the runner's preselected Xcode is used. |
| `setup` | string | empty | Bash script run in the checked-out repository after checkout and before scanning, for projects with build prerequisites. It runs from the repository root and may invoke several project scripts, for example `./scripts/prepare-periphery-scan.sh`. A non-zero exit fails the job before the scan starts. |
| `periphery_version` | string | latest | Exact Periphery CLI release tag to use, for example `1.0.0`. See [available releases](https://github.com/periphery-pro/cli-releases/releases). By default the workflow resolves the latest stable release. Pin this to keep results stable across CLI updates. |
| `run_without_baseline` | boolean | `false` | What to do when a pull request's merge-base baseline is unavailable, which happens before the first baseline is recorded or after the artifact expires. By default the scan is skipped and a notice explains why. Set `true` to scan anyway — every existing result is then reported, not only what the pull request introduced. |
| `post_comment` | boolean | `true` | Publish the rendered report so it can be posted as a pull-request comment. This only prepares the report; a comment appears when the caller also adds the workflow described below. Set `false` to keep the job summary but never comment. |

## Pull-request comments

Pull requests from forks receive a read-only `GITHUB_TOKEN`, so the scan job
cannot post a comment itself. Add a second workflow that runs in the base
repository once the scan completes:

```yaml
name: Periphery comment

on:
  workflow_run:
    workflows: [Periphery]
    types: [completed]

permissions: {}

jobs:
  comment:
    permissions:
      actions: read
      pull-requests: write
    uses: periphery-pro/actions/.github/workflows/comment.yml@v1
```

Set `workflows` to the name of the workflow that calls `scan.yml`. GitHub reads
`workflow_run` triggers only from the default branch, so this file takes effect
once it is committed there.

The comment repeats the job summary, and later pushes to the pull request update
it in place rather than adding another comment. Set the `post_comment` input to
`false` on the scan workflow to stop commenting without removing this file.

Stable releases also provide a moving major (`@v1`) workflow tag.
