# `sample/buildSrc` reference

The root `bootstrap.sh install` command generates this directory from the canonical typed sources in
`.mutation-testing/mutation-results-src/`. It contains the `MutationResults` data
classes and parser functions used by the neutral
`.mutation-testing/mutation-results.gradle.kts` task.

The setup command verifies the target Kotlin Gradle plugin version against the
compiler-coupled toolkit pin before changing the build.

Do not edit these generated files directly. Regenerate them from the repository root:

```bash
./bootstrap.sh install sample
```

See [How to set up mutation testing manually](../../docs/how-to/manual-setup.md) for the corresponding manual setup.
