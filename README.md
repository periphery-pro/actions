# Periphery GitHub Actions

The official reusable workflow for scanning a public repository with Periphery.
It needs no Periphery account or secret.

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
to the latest compatible workflow release.
