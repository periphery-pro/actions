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
| `periphery-version` | string | latest | Exact Periphery CLI release tag to use. |
| `run_without_baseline` | boolean | `false` | Run a full pull-request scan when its merge-base baseline is unavailable. When `false`, the scan is skipped instead. |

By default, the workflow downloads the latest stable CLI release from
[cli-releases](https://github.com/periphery-pro/cli-releases).

When the caller runs on pushes, the workflow records the scan results as a
baseline artifact keyed by the commit SHA. Artifact retention follows the
caller repository's GitHub Actions retention setting, which defaults to 90
days for public repositories. On pull requests, the workflow finds the head
branch's merge-base commit, downloads that commit's baseline, and only reports
results introduced since then. Pull-request results use GitHub Actions
annotations so they appear inline on the changed files.

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
      periphery-version: 1.0.0.beta.3
```

The caller is responsible for selecting which pushes record baselines. A
typical workflow runs for pull requests and for pushes to `main`:

```yaml
on:
  pull_request:
  push:
    branches: [main]
```

Stable releases also provide moving major (`@v1`) and major-minor (`@v1.2`)
workflow tags.
