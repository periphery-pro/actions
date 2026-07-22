# Periphery GitHub Actions

The official reusable workflow for scanning a public repository with Periphery.
It needs no Periphery account or secret.

Each workflow version uses the CLI release with the same version from
[cli-releases](https://github.com/periphery-pro/cli-releases).
For example, `@v1.0.0` downloads and runs CLI release `1.0.0`.

## Configuration

The workflow checks out the caller repository and runs the scan from its root.
Put your Periphery configuration in `.periphery.yml` (or `.periphery.yaml`) at
that root; the CLI discovers it automatically. The reusable workflow accepts no
configuration inputs, so the configuration stays versioned with the repository
being scanned.

```yaml
jobs:
  periphery:
    permissions:
      contents: read
      id-token: write
    uses: periphery-pro/actions/.github/workflows/scan.yml@v1.0.0.beta.1
```

Stable releases also provide moving
major (`@v1`) and major-minor (`@v1.2`) tags for users who deliberately opt in
to the latest compatible workflow release; those tags always point to the
matching latest CLI release in that channel.
