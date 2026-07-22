# Periphery GitHub Actions

The official reusable workflow for scanning a public repository with Periphery.
It needs no Periphery account or secret.

Each workflow version uses the CLI release with the same version from
[periphery-pro/cli-releases](https://github.com/periphery-pro/cli-releases).
For example, `@v1.0.0` downloads and runs CLI release `1.0.0`.

```yaml
jobs:
  periphery:
    permissions:
      contents: read
      id-token: write
    uses: periphery-pro/actions/.github/workflows/scan.yml@v1.0.0.beta.1
```

Use an immutable release tag in production. Stable releases also provide moving
major (`@v1`) and major-minor (`@v1.2`) tags for users who deliberately opt in
to the latest compatible workflow release; those tags always point to the
matching latest CLI release in that channel.
