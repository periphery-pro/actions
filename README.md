# Periphery GitHub Actions

The official reusable workflow for scanning **public GitHub repositories** with
Periphery. On pull requests, it compares the scan with an automatically recorded
baseline from the merge-base commit and reports only issues introduced by the
pull request. Results appear as inline GitHub annotations, so a project can
adopt Periphery without first fixing all of its existing unused code.

## Configuration

The workflow checks out the caller repository and runs the scan from its root.
Put your Periphery configuration in `.periphery.yml` at
that root; the CLI discovers it automatically, so scan configuration stays
versioned with the repository being scanned. Workflow behavior can be adjusted
with the inputs below.

```yaml
jobs:
  periphery:
    permissions:
      actions: read
      contents: read
      id-token: write
    uses: periphery-pro/actions/.github/workflows/scan.yml@v1
```

### Inputs

| Input | Type | Default | Description |
| --- | --- | --- | --- |
| `fetch_depth` | number | `0` | Git history depth fetched from the pull-request head and base. `0` fetches the complete history; a positive value must be deep enough to include the merge base. |
| `checkout_submodules` | boolean | `false` | Recursively check out Git submodules before scanning. |
| `setup` | string | empty | Bash script to run after checkout and before scanning. |
| `periphery_version` | string | latest | Exact Periphery CLI release tag to use. |
| `run_without_baseline` | boolean | `false` | Run a full pull-request scan when its merge-base baseline is unavailable. When `false`, the scan is skipped instead. |

By default, the workflow downloads the latest stable CLI release from
[cli-releases](https://github.com/periphery-pro/cli-releases).

If the merge-base baseline is unavailable, the pull-request scan is skipped by
default. Set `run_without_baseline` to `true` to run a full scan instead:

```yaml
jobs:
  periphery:
    permissions:
      actions: read
      contents: read
      id-token: write
    uses: periphery-pro/actions/.github/workflows/scan.yml@v1
    with:
      run_without_baseline: true
```

The workflow fetches the complete Git history by default so it can reliably
identify a pull request's merge base. Set `fetch_depth` to a positive number
to limit the checkout history for large repositories. The configured depth
must include the merge-base commit or baseline lookup will fail:

```yaml
jobs:
  periphery:
    permissions:
      actions: read
      contents: read
      id-token: write
    uses: periphery-pro/actions/.github/workflows/scan.yml@v1
    with:
      fetch_depth: 100
```

If the project relies on Git submodules, enable their recursive checkout:

If the project relies on Git submodules, enable their recursive checkout:

```yaml
jobs:
  periphery:
    permissions:
      actions: read
      contents: read
      id-token: write
    uses: periphery-pro/actions/.github/workflows/scan.yml@v1
    with:
      checkout_submodules: true
```

For projects that need build prerequisites, run a Bash setup script from the
checked-out repository before the scan. It can invoke multiple project scripts:

```yaml
jobs:
  periphery:
    permissions:
      actions: read
      contents: read
      id-token: write
    uses: periphery-pro/actions/.github/workflows/scan.yml@v1
    with:
      setup: |
        ./scripts/prepare-periphery-scan.sh
```

To use a particular CLI release instead of the latest available release:

```yaml
jobs:
  periphery:
    permissions:
      actions: read
      contents: read
      id-token: write
    uses: periphery-pro/actions/.github/workflows/scan.yml@v1
    with:
      periphery_version: 1.0.0
```

The caller is responsible for selecting which pushes record baselines. Each
baseline artifact is keyed by commit SHA and follows the caller repository's
GitHub Actions retention setting, which defaults to 90 days for public
repositories. A typical workflow runs for pull requests and for pushes to
`main`:

```yaml
on:
  pull_request:
  push:
    branches: [main]
```

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
it in place rather than adding another comment.

Stable releases also provide moving major (`@v1`) and major-minor (`@v1.2`)
workflow tags.
