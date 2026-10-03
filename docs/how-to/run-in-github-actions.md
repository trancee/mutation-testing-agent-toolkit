# How to run mutation testing in GitHub Actions

Use this guide to run an already-configured mutation test suite on pull requests, enforce a minimum mutation score, and retain the full report as a workflow artifact.

## Prerequisites

- Mutation testing is configured in the project. If it is not, complete the [bootstrap tutorial](../tutorials/bootstrap-existing-project.md).
- The project includes a Gradle wrapper.
- Business logic and its tests have the mutflow annotations described in the bootstrap tutorial.

## Add the workflow

Create `.github/workflows/mutation-testing.yml`:

```yaml
name: Mutation testing

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  mutation-testing:
    runs-on: ubuntu-latest
    env:
      MIN_MUTATION_SCORE: '0.80'
    steps:
      - uses: actions/checkout@v7

      - uses: actions/setup-java@v6
        with:
          distribution: temurin
          java-version: '26'

      - uses: gradle/actions/setup-gradle@v6
        with:
          gradle-version: '9.8.0'

      - name: Generate mutation results
        run: ./gradlew mutationResults --no-daemon --console=plain

      - name: Enforce mutation quality
        run: |
          python3 - <<'PY'
          import json
          import os
          from pathlib import Path

          report_path = Path("build/reports/mutation-results.json")
          if not report_path.is_file():
              raise SystemExit(f"Mutation report not found: {report_path}")

          results = json.loads(report_path.read_text())
          gap_count = results["gaps"]
          if gap_count:
              gap_types = ", ".join(
                  gap["type"] for gap in results["executionGaps"]
              )
              raise SystemExit(
                  f"Mutation run has {gap_count} execution gap(s): {gap_types}"
              )

          score = results["mutationScore"]
          if score is None:
              raise SystemExit("Mutation run produced no evaluable mutations")

          minimum = float(os.environ["MIN_MUTATION_SCORE"])
          if score < minimum:
              raise SystemExit(
                  f"Mutation score {score:.1%} is below the {minimum:.1%} minimum"
              )

          print(f"Mutation score {score:.1%} meets the {minimum:.1%} minimum")
          PY

      - name: Upload mutation results
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: mutation-results
          path: |
            build/reports/mutation-results.json
            build/test-results/test/
          if-no-files-found: warn
          retention-days: 14
```

Set `MIN_MUTATION_SCORE` to the threshold your project enforces. The value is a fraction, so `0.80` means 80%.

The quality step also rejects execution gaps and runs with no evaluable mutations. This prevents an incomplete run from passing because its score happens to meet the threshold. See the [mutation results reference](../reference/mutation-results-format.md) for the report fields and quality bands.

## Adjust a multi-module build

If the mutflow plugin and `mutationResults` task belong to a subproject, use its qualified Gradle task and report path. For a subproject named `service`:

```yaml
- name: Generate mutation results
  run: ./gradlew :service:mutationResults --no-daemon --console=plain
```

Change `report_path` and the uploaded artifact path to `service/build/reports/mutation-results.json`. Keep the test results path under the same subproject.

## Check the workflow

Open a pull request or start the workflow from the Actions page. The `mutation-testing` job should:

1. Run the annotated tests and their generated mutations.
2. Print the mutation score and configured minimum.
3. Upload `mutation-results.json` and the JUnit XML files, including when the quality check fails.

If the quality check fails, download the `mutation-results` artifact and follow [How to interpret and act on mutation testing results](interpret-results.md).
