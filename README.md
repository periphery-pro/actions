# Periphery GitHub Actions

The official reusable workflow for scanning **public GitHub repositories** with
Periphery. Public scans do not need a Periphery account.

Each workflow version uses the CLI release with the same version from
[cli-releases](https://github.com/periphery-pro/cli-releases).
For example, `@v1.0.0` downloads and runs CLI release `1.0.0`.

## Configuration

The workflow checks out the caller repository and runs the scan from its root.
Put your Periphery configuration in `.periphery.yml` at
that root; the CLI discovers it automatically. The reusable workflow accepts no
configuration inputs, so the configuration stays versioned with the repository
being scanned.

```yaml
jobs:
  periphery:
    permissions:
      actions: read
      contents: read
      id-token: write
    uses: periphery-pro/actions/.github/workflows/scan.yml@v1
```

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

The caller is responsible for selecting which pushes record baselines. A
typical workflow runs for pull requests and for pushes to `main`:

```yaml
on:
  pull_request:
  push:
    branches: [main]
```

Stable releases also provide moving
major (`@v1`) and major-minor (`@v1.2`) tags for users who deliberately opt in
to the latest compatible workflow release; those tags always point to the
matching latest CLI release in that channel.
