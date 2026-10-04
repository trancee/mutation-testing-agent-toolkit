# Should MutFlow's KMP Dependency Injection Be Fixed Upstream? (Kompact Trial Research)

**Date:** 2026-10-03
**Research only.** No upstream issues/PRs were opened, no maintainers were contacted, and no code in MutFlow or Kompact was modified while producing this report.

**Trigger:** While trialling MutFlow 1.6.0 on Kompact (JVM + iOS + Android Native KMP targets), applying the MutFlow Gradle plugin to the normal build caused `:kompact:compileKotlinAndroidNativeArm64` to fail resolving `io.github.anschnapp.mutflow:mutflow-annotations:1.6.0` for `android_arm64`, even with `mutflow.enabled=false` set.

**Primary sources inspected (all fetched directly, not via secondary articles):**
- `anschnapp/mutflow`, canonical upstream repo, pinned tag **`v1.6.0`** = commit `4734e39cb7a8e3e64ec742be89b6e353a6fdfc58` — source code, `DESIGN-MULTIPLATFORM.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `gradle.properties`.
- Published **Gradle Module Metadata** for `mutflow-annotations:1.6.0` and `mutflow-runtime:1.6.0` fetched directly from Maven Central (`repo1.maven.org`), independent of anything the repo's own docs claim.
- GitHub REST/Search API against `anschnapp/mutflow` (tags, releases, issues, repo metadata) — live, queried today.
- `trancee/kompact`, the real trial repository, at its current `HEAD` = commit `703574da42dc0993d45069a788a3456af27784f0` (fix commit), compared against the pre-fix commit `32a2e10dbb6b61ed0a2b7053f0c257750fd46063`.
- This toolkit's own existing documentation (`docs/explanation/mutflow-architecture.md`, `docs/how-to/troubleshoot-mutation-testing.md`, `docs/tutorials/kmp-jvm-mutation-test.md`, ADR-001) for consistency/precedent, and `docs/agents/issue-tracker.md` for report placement conventions.

---

## Verdict (TL;DR)

1. **Not already fixed.** `v1.6.0` is both the exact tag Kompact pinned and the newest tag in the repository (no GitHub Releases exist at all — only tags — so "latest stable release" = `v1.6.0`). The behavior is unchanged since Kotlin Multiplatform support was first introduced in `v1.2.0` (2026‑09‑06); nothing in the `v1.3.0`–`v1.6.0` changelog entries touches dependency wiring or target resolution.
2. **This is a deliberate, explicitly documented design choice, not an accidental bug** — the maintainer's own code comment, the design document, the README, and the `v1.2.0` CHANGELOG entry all state the same thing independently: declaring a KMP target MutFlow does not publish a klib for is a **hard resolution failure by design**, not a degraded experience. Android Native and iOS **device** targets are explicitly classified **"Out of scope"** — not merely "not yet published."
3. **However, there is a real, concrete, and currently undocumented gap**: the `mutflow.enabled=false` escape hatch is advertised project‑wide ("zero overhead… no extra compilation happens") but **does not and architecturally cannot** prevent the `commonMain`/`commonTest` dependency declarations that trigger the failure, because those two dependency lines execute *before* the `enabled` gate is even read. The docs never state this caveat anywhere a KMP user with mixed supported/unsupported targets would find it before hitting the failure.
4. **Recommended action: documentation first, not a PR, and not a code-behavior-change issue — yet.** `anschnapp/mutflow`'s `CONTRIBUTING.md` explicitly welcomes **documentation improvements as direct pull requests**, but requires a **discussion issue before any PR that changes behavior**. Since the one change that would *actually* let a mixed-target KMP project opt out of the `commonMain`/`commonTest` wiring is a behavior change (not a bug fix), this report's concrete next action is an **upstream discussion issue** (not a PR), with a documentation fix identified as the lower-risk, immediately-actionable complement. See §4 for the full recommendation, draft issue text, and acceptance criteria.
5. **Kompact's existing consumer-side workaround (`apply false` + conditional `pluginManager.apply`, Gradle-DSL FQN targeting instead of the `@MutationTarget` annotation, and a JVM-only `src/mutflowTest/kotlin` source set) is already the correct and, in fact, the only currently-possible fix** given MutFlow's current architecture — no upstream change is required for Kompact's own build to keep working. The question this report answers is whether upstream should make that pattern easier/safer/more discoverable for the *next* consumer, not whether Kompact itself needs anything further.

---

## 1. Canonical repository, version verification, and "already fixed?" check

### 1.1 Canonical repository and exact version pinned

The canonical upstream repository is **[`anschnapp/mutflow`](https://github.com/anschnapp/mutflow)** ("Mutation testing inside your Kotlin tests. Compile once, catch gaps.", Apache-2.0, 36 stars, 7 forks as of this research — `https://api.github.com/repos/anschnapp/mutflow`).

Kompact pins `id("io.github.anschnapp.mutflow") version "1.6.0" apply false` — confirmed directly in the live build file: `trancee/kompact:kompact/build.gradle.kts:14` (commit `703574d`, current `HEAD`).

### 1.2 `v1.6.0` is the exact tag *and* the latest tag — nothing newer exists

Queried `https://api.github.com/repos/anschnapp/mutflow/tags` directly: the newest tag is `v1.6.0`, resolving to commit `4734e39cb7a8e3e64ec742be89b6e353a6fdfc58`. Queried `https://api.github.com/repos/anschnapp/mutflow/releases`: **the array is empty** — this project does not use GitHub Releases at all, only lightweight/annotated git tags. Therefore "latest stable release" and "the exact `v1.6.0` tag Kompact used" are the same commit: **there is no newer version where this could already be fixed.**

### 1.3 Nothing changed between the KMP feature's introduction and `v1.6.0` that touches this behavior

`CHANGELOG.md` at the pinned commit (`anschnapp/mutflow:CHANGELOG.md`) shows Kotlin Multiplatform support was introduced in **`v1.2.0` (2026‑09‑06)** and the dependency-resolution behavior was called out, as a *known limitation*, in that very same release:

> "Because Kotlin Multiplatform resolves dependencies per target variant, the published target set *is* the supported set: a project declaring a target mutflow does not publish gets a resolution failure rather than a degraded experience. To try an unpublished target, build mutflow yourself with `./gradlew publishToMavenLocal -Pmutflow.extraNativeTargets=macosArm64` and consume it from `mavenLocal()` - no build-file edits needed."
> — `anschnapp/mutflow:CHANGELOG.md` (`## [1.2.0]`, "Known limitations (multiplatform path)" bullet)

Subsequent releases (`v1.2.1`, `v1.2.2`, `v1.3.0`, `v1.3.1`, `v1.3.2`, `v1.4.0`, `v1.5.0`, `v1.5.1`, `v1.6.0`) add operators, JUnit 4 support, compiler-crash fixes, and (in `1.6.0`) a per-test wall-clock timeout budget (`anschnapp/mutflow:CHANGELOG.md`, `## [1.6.0]`, "Added" — this is unrelated to dependency resolution, though it is notable that Kompact's own mutation run separately hit **8 timed-out mutations**, which this exact `1.6.0` feature targets — a tuning opportunity, not part of this report's scope). **None of these entries mention changing how or when `commonMain`/`commonTest` dependencies are added, and none mention publishing new native-target variants.** This is independent, dated, primary-source confirmation that the behavior is original to the KMP feature and has not been revisited in four minor releases.

### 1.4 No prior upstream issue reports this specific interaction

Searched the GitHub Search API against `anschnapp/mutflow` issues/PRs (`is:issue,pr` implicit via `/search/issues`) for `android_arm64`, `androidNativeArm64`, `iosArm64`, `"no matching variant"`, and `"mutflow.enabled"` in title/body/comments — **all five queries returned zero results.** A title-scoped search for `multiplatform`/`Android`/`commonMain` returned exactly one hit, PR #14 ("Multiplatform mutation runtime and new operators" — a large, unrelated, **closed-not-merged** community PR proposing a broader JS/Wasm/Native rewrite with its own `macosArm64` target, not about dependency scoping). A full listing of the 6 currently-open issues (`/repos/anschnapp/mutflow/issues?state=open`) shows none relate to KMP target scoping; recent closed issues (#23, #40) are unrelated discussion-first proposals about timeout/flake handling, authored by a `CONTRIBUTOR`-tier user and closed/engaged by the maintainer quickly — useful precedent for how the repo's discussion-first process actually works in practice (see §4). **Conclusion: this exact interaction — resolution failure despite `mutflow.enabled=false` for a KMP project with unsupported declared targets — does not appear to have been previously reported upstream.** (Caveat: GitHub's search API can miss issues that don't use these literal terms; this is a reasonably thorough but not exhaustive check — see "Gaps" in §4.)

---

## 2. The KMP boundary, precisely

### 2.1 Where the dependency is actually injected, with exact lines

The injection happens in `MutflowKmpSupport.configure()`, called unconditionally for every project that has **both** the MutFlow plugin and the Kotlin Multiplatform plugin applied — this call site itself has no `enabled` guard:

```kotlin
target.plugins.withId("org.jetbrains.kotlin.multiplatform") {
    debug("  kotlin.multiplatform plugin detected, configuring native mutation testing...")
    MutflowKmpSupport.configure(target, extension)
}
```
— `anschnapp/mutflow:mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowGradlePlugin.kt:115-118` ([permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowGradlePlugin.kt#L115-L118))

Inside `configure()`, the dependency declarations and the `enabled` check appear in this exact order:

```kotlin
fun configure(project: Project, extension: MutflowExtension) {
    val kotlin = project.extensions.getByType(KotlinMultiplatformExtension::class.java)

    // The user-facing dependencies mirror the JVM path: production code
    // needs the annotations, test code needs the underTest API. Both are
    // multiplatform artifacts, so declaring them on the common source
    // sets covers every target (including a jvm() target, where they are
    // harmless without the JVM wiring).
    kotlin.sourceSets.getByName("commonMain").dependencies {
        implementation("${MutflowGradlePlugin.GROUP_ID}:mutflow-annotations:$MUTFLOW_VERSION")
    }
    kotlin.sourceSets.getByName("commonTest").dependencies {
        implementation("${MutflowGradlePlugin.GROUP_ID}:mutflow-runtime:$MUTFLOW_VERSION")
    }

    // The gradle property gate is read eagerly on purpose: the mutated
    // compilations have to be created while the kotlin { } block is being
    // evaluated (KGP finalizes its model in afterEvaluate, which runs
    // before any afterEvaluate this plugin could register). Setting
    // `mutflow { enabled = false }` in the build script still disables
    // instrumentation (isApplicable checks it lazily) and the
    // orchestrator tasks (onlyIf), just not the compilation creation.
    val enabledByProperty = project.providers.gradleProperty("mutflow.enabled")
        .map { it.toBoolean() }
        .getOrElse(true)
    if (!enabledByProperty) {
        return
    }
    // ... (lines 75-86: umbrella task + per-target wiring, all skipped above if disabled)
}
```
— `anschnapp/mutflow:mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowKmpSupport.kt:46-87` ([permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowKmpSupport.kt#L46-L87), dependency lines at `L54-L59`, comment + early return at `L61-L73`)

This precisely and literally confirms the "known context" given for this research: **the two dependency declarations (`L54-59`) execute unconditionally, before the `mutflow.enabled` Gradle-property check (`L68-73`) is even evaluated.** The early return at `L72` only skips creating the umbrella `mutflowNativeTest` task and the per-target `configureNativeTarget`/`configureJvmTarget` wiring (`L75-86`) — it never un-does the two `dependencies { implementation(...) }` calls above it, because those already ran as plain statements in the function body, not inside any conditional.

### 2.2 Why disabling mutation *execution* cannot avoid dependency *resolution*

Gradle resolves a source set's declared dependencies into concrete, variant-matched artifacts during **configuration/compilation**, for every Kotlin compilation that (transitively, via the default source-set hierarchy template) depends on that source set — this is independent of which task a user ultimately asks Gradle to run, and independent of any property read *inside* a task's execution (`onlyIf`) or inside the compiler-plugin's own lazy `isApplicable` check. Concretely:

- `commonMain` is the root of the KMP default hierarchy: **every** platform target's main compilation (`jvmMain`, `iosArm64Main`, `androidNativeArm64Main`, …) depends on it. Adding `mutflow-annotations` to `commonMain` therefore adds it to **every declared target's** compile classpath, not just the one(s) a user actually cares about mutation-testing.
- There are two independent "disable" switches in this plugin, and **neither** reaches the two lines above:
  - **`mutflow.enabled` Gradle property** (eager, read at `MutflowKmpSupport.kt:68`): gates whether the native/JVM per-target compilations and tasks get created at all — but only *after* the `commonMain`/`commonTest` dependency lines already executed.
  - **`mutflow { enabled = false }` DSL property** (lazy `Property<Boolean>`, declared `MutflowGradlePlugin.kt:19`, defaulted from the same Gradle property at `L102-106`): only consulted later and lazily, by `isApplicable()` (compiler-plugin instrumentation gate, `MutflowGradlePlugin.kt:241-249`) and by `task.onlyIf("mutflow is disabled") { extension.enabled.get() }` (task-execution gate, `MutflowKmpSupport.kt:209` and `:281`). Both of these run *after* Gradle has already had to resolve the dependency graph for configuration, so by the time they could matter, the resolution failure has already happened (or, for supported targets, resolution already succeeded and these gates just suppress what runs next).
- Net effect: **there is no setting in the published MutFlow 1.6.0 plugin that removes the `commonMain`/`commonTest` dependency edges for a target once the plugin's `configure()` function has executed for that project.** The only way to avoid them is to prevent `configure()` from running in the first place — i.e., not apply the `org.jetbrains.kotlin.multiplatform`-aware code path to that project at all, which in Gradle terms means deferring/conditionally applying the whole plugin (exactly what Kompact's fix does; see §2.5).

This directly explains the user's "known context" claim end-to-end, from source, with exact lines — not merely as an inference from documentation prose.

### 2.3 This is not an inconsistency between the JVM and KMP code paths — it is the same design intent with a different blast radius

It would be inaccurate to describe this as "the enabled-check is wired correctly for JVM but wired incorrectly for KMP." The plain `kotlin("jvm")` path has the *same* underlying intent — keep annotation/wrapper APIs resolvable even when disabled, so user source code that references them still compiles — and it is **also** not fully gated by `enabled`:

```kotlin
target.plugins.withId("org.jetbrains.kotlin.jvm") {
    target.afterEvaluate {
        if (extension.enabled.get()) {
            configureSourceSets(target)
            addDependencies(target)
        } else {
            // Add annotations and test dependencies so code still compiles
            target.dependencies.add("implementation", "$GROUP_ID:mutflow-annotations:$MUTFLOW_VERSION")
            target.dependencies.add("testImplementation", "$GROUP_ID:mutflow-junit6:$MUTFLOW_VERSION")
        }
    }
}
```
— `anschnapp/mutflow:mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowGradlePlugin.kt:120-141` ([permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowGradlePlugin.kt#L120-L141))

Even in the **disabled** branch (`L127-137`) of the plain-JVM path, `mutflow-annotations` and `mutflow-junit6` are still added — just without the extra `mutatedMain` source set / double-compilation machinery (`configureSourceSets`, `addDependencies` with `mutflow-core`). This is **harmless for plain JVM** only because `mutflow-annotations` and `mutflow-junit6` always publish a JVM variant (there is no other target to fail to resolve). The KMP path applies the identical "always keep annotations/runtime resolvable" principle to `commonMain`/`commonTest` — but because `commonMain` fans out to every declared platform target, and MutFlow does not publish klib variants for every possible Kotlin/Native target, the *same* design choice that is invisible in the JVM path becomes a hard failure in the KMP path whenever a project declares a target outside MutFlow's published set. **The design is consistent; the consequence differs because of variant-publishing coverage, not because of inconsistent gating logic.** This nuance matters for evaluating fixes in §3: a "fix" that simply moves the `enabled` check earlier would reintroduce the exact compile-breakage-when-disabled problem the author was trying to avoid.

### 2.4 Independent confirmation of published variants: Maven Central Gradle Module Metadata

Rather than relying solely on the repository's own documentation, the actual **published Gradle Module Metadata** for `mutflow-annotations:1.6.0` and `mutflow-runtime:1.6.0` was fetched directly from Maven Central (`repo1.maven.org/maven2/io/github/anschnapp/mutflow/...`). Both `.module` files list exactly the same five publishable variant families:

| Variant family | `org.jetbrains.kotlin.platform.type` / `native.target` attribute |
|---|---|
| `metadataApiElements` / `metadataSourcesElements` | `common` (Kotlin metadata only, not directly consumable by a compilation) |
| `jvmApiElements-published` / `jvmRuntimeElements-published` / `jvmSourcesElements-published` | `jvm` |
| `linuxX64ApiElements-published` / `linuxX64SourcesElements-published` | `native` / `linux_x64` |
| `mingwX64ApiElements-published` / `mingwX64SourcesElements-published` | `native` / `mingw_x64` |

— `mutflow-annotations-1.6.0.module` and `mutflow-runtime-1.6.0.module`, fetched from `https://repo1.maven.org/maven2/io/github/anschnapp/mutflow/mutflow-annotations/1.6.0/mutflow-annotations-1.6.0.module` and the equivalent `mutflow-runtime` path, 2026‑10‑03.

**There is no `android_arm64`, `ios_arm64`, `ios_simulator_arm64`, or `macos_*` variant published at all.** This is independent, primary-source (actual published artifact metadata, not a doc claim) confirmation of exactly the failure mechanism: when Kompact's `androidNativeArm64Main` compilation needs to resolve `commonMain`'s `mutflow-annotations` dependency, Gradle's variant-aware resolver has no `android_arm64` entry to match against anything in this module — hence "no matching variant," independent of task selection, independent of `mutflow.enabled`.

### 2.5 `mutflow-annotations`/`mutflow-core`/`mutflow-runtime` are genuinely cross-platform modules by design — only `mutflow-junit6`/`mutflow-junit4` are JVM-only

This is confirmed by the `v1.2.0` CHANGELOG entry itself: *"`mutflow-annotations`, `mutflow-core` and `mutflow-runtime` are now Kotlin Multiplatform modules (JVM behavior unchanged and regression-verified; JVM actuals are the previous implementations verbatim)"* (`anschnapp/mutflow:CHANGELOG.md`, `## [1.2.0]`). The design document's module-impact table states the same: `mutflow-core` and `mutflow-runtime` "Become[] KMP… moves to `commonMain`" (`anschnapp/mutflow:DESIGN-MULTIPLATFORM.md:202-203`). So the dependencies forced into `commonMain`/`commonTest` are not JVM-only shims awkwardly bolted onto common source — **they are the real, intended, cross-platform API surface** (the `@MutationTarget` annotation and the `MutFlow.underTest {}` wrapper). The JVM-only pieces are specifically `mutflow-junit6` (and the plugin-unwired `mutflow-junit4`), which is why the KMP plugin only ever puts `mutflow-junit6` on the JVM-target `mutatedTest` compilation, never on `commonTest` (`MutflowKmpSupport.kt:124-141`). This matters for §3: "don't put these in `commonMain`/`commonTest` at all" is not a coherent fix, because the annotation genuinely needs to be visible from common production code for any target mutflow *does* support, including native ones.

### 2.6 Android Native and iOS device targets are architecturally excluded, not merely unpublished

The design document's own target table states this as an explicit classification, distinguishing three different states:

| Target | Status (verbatim from table) |
|---|---|
| `linuxX64` | "**Done (Phase 2)**: runtime klibs build; unit tests and the end-to-end verification run on the Linux dev machine" |
| `mingwX64` | "**Declared (Phase 2)**: klib cross-compiles from Linux… an actual test run needs a Windows host" |
| `macosX64`, `macosArm64` | "Planned… **Not blocked on producing the klibs**… Blocked on having a Mac to *run* the tests on" |
| Apple simulators (`iosSimulatorArm64`, `iosX64`, …) | "Planned: klibs cross-compile like the macOS ones, but running needs more than a host… a simulator needs `simctl` with env vars carrying the `SIMCTL_CHILD_` prefix" |
| **iOS/watchOS/tvOS device targets, Android Native** | **"Out of scope: no standard Gradle test execution exists for these"** |

— `anschnapp/mutflow:DESIGN-MULTIPLATFORM.md:220-226` ([permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/DESIGN-MULTIPLATFORM.md#L220-L226))

Crucially, this is **not just a publishing gap that more CI effort could close** — it is backed by an architectural constraint in the orchestrator itself. The native mutation orchestrator only registers a runnable mutation task when the target matches the build host exactly:

```kotlin
target.binaries.test(MUTATED_BINARY_PREFIX, listOf(NativeBuildType.DEBUG)) { binary ->
    binary.compilation = mutatedTest

    // The orchestrator can only execute binaries of the build host.
    // For cross-compiled targets (e.g. mingwX64 on Linux) the mutated
    // binary still builds - that is the compile-proof - but no
    // orchestrator task is registered, matching how KGP itself only
    // runs <target>Test on a matching host.
    if (target.konanTarget != HostManager.host) {
        return@test
    }
    // ... orchestrator task registration follows
}
```
— `anschnapp/mutflow:mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowKmpSupport.kt:258-268` ([permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowKmpSupport.kt#L258-L268))

`androidNativeArm64`/`androidNativeX64`/etc. and `iosArm64` (device) can never equal `HostManager.host` on any real Gradle build machine (a build host is always some flavor of Linux/macOS/Windows x64/arm64 — never literally an Android or iOS device). **Even `iosSimulatorArm64` fails this exact-match check on an Apple Silicon Mac**, because `HostManager.host` there resolves to `macos_arm64`, a distinct `KonanTarget` from `ios_simulator_arm64` — which is precisely why the CHANGELOG's `v1.2.0` "Known limitations" list separately flags simulators as needing unimplemented `SIMCTL_CHILD_`-prefixed environment-variable forwarding (`anschnapp/mutflow:CHANGELOG.md`, `## [1.2.0]`, third bullet). **Conclusion: even if MutFlow published `android_arm64`/`ios_arm64` klib variants today (via the `-Pmutflow.extraNativeTargets` escape hatch or otherwise), the current orchestrator would still refuse to register a mutation-test task for them — they would only ever get "compile proof," never real mutation execution, under the existing design.** This is a materially stronger form of "out of scope" than "not yet published," and it rules out "just publish more variants" as a viable *complete* fix for Android Native/iOS device (see §3a).

### 2.7 Independent verification against this toolkit's own prior documentation

This toolkit's own docs already state the same conclusion, each with the same `v1.6.0` design-doc citation this report independently re-derived from source: `docs/explanation/mutflow-architecture.md`, `docs/how-to/troubleshoot-mutation-testing.md`, and `docs/tutorials/kmp-jvm-mutation-test.md` all cite `https://github.com/anschnapp/mutflow/blob/v1.6.0/DESIGN-MULTIPLATFORM.md#supported-targets` for the "iOS/Android Native unsupported" claim. This report corroborates that citation against the primary source directly (§2.6) and additionally traces the *mechanism* (§2.1-2.4) and the *consumer-facing documentation gap* (§2.8) that none of the existing toolkit docs had previously analyzed in this depth.

### 2.8 The concrete documentation gap

The README's "Disabling Mutation Testing" section — which appears early, well before the KMP section 400+ lines later — makes an unqualified, project-wide-sounding promise:

> "You can completely disable mutation testing without removing the plugin. When disabled, no compiler plugin is registered and no extra compilation happens - zero overhead."
> … "When disabled, your code still compiles normally (`@MutationTarget` and `@MutFlowTest` annotations are still available), but tests run without any mutations - the mutation summary will show 0 mutations discovered."
— `anschnapp/mutflow:README.md:113-133` ([permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/README.md#L113-L133))

This is **literally true** for a plain `kotlin("jvm")` project (confirmed in §2.3: the disabled branch there only skips the *extra* `mutatedMain` compilation, and the still-added `mutflow-annotations`/`mutflow-junit6` always resolve on the JVM). It is **also true in the narrow sense** for a KMP project's *per-target* `mutatedMain`/`mutatedTest` compilations (those genuinely are skipped by the eager `mutflow.enabled` property check, §2.1). But the overall framing — "completely disable," "zero overhead" — does not warn a KMP reader that the `commonMain`/`commonTest` dependency *resolution* requirement for **every declared target** survives regardless, and can turn "zero overhead" into "build does not configure at all" for a project with any unsupported target declared. Separately, the KMP-specific "Current limitations" list (`anschnapp/mutflow:README.md:662-683`) and "Trying an unpublished target" section (`README.md:686-692`) both explain the *general* "declare an unpublished target → hard resolution failure" rule, but **neither mentions that this triggers independently of `mutflow.enabled`, nor cross-references the "Disabling Mutation Testing" section at all.** A full-text search of `DESIGN-MULTIPLATFORM.md`'s "Open Questions" section (`DESIGN-MULTIPLATFORM.md:723-735`) for "eager"/"commonMain"/"enabled" confirms this interaction is not discussed there either. **This is the one concrete, verifiable, currently-undocumented gap in otherwise thorough and honest documentation** — not a hidden defect, but a missing cross-reference between two sections that, read separately, each sound more reassuring than the combined truth for a mixed-target KMP consumer.

---

## 3. Evaluating upstream options

### (a) Publish/maintain the required KMP variants (`android_arm64`, `ios_arm64`, `ios_simulator_arm64`, …)

- **For macOS/Apple simulator targets**: already the maintainer's own stated plan, blocked only on (1) a Mac CI runner to *execute* (not just cross-compile) tests, which the design doc shows is otherwise mechanically solved (`DESIGN-MULTIPLATFORM.md` "Apple cross-compilation" note confirms klibs already cross-compile from Linux today) and (2) implementing `SIMCTL_CHILD_`-prefixed environment variable forwarding for simulators specifically. This is **feasible and already on the maintainer's own roadmap** — not something this report needs to propose.
- **For iOS *device* targets and Android Native**: infeasible under the *current* orchestrator design regardless of publishing effort, because §2.6 shows the orchestrator requires `target.konanTarget == HostManager.host` to register any mutation-execution task at all, and no standard Gradle build host can ever *be* an iOS or Android device. Closing this gap would require a fundamentally different test-execution strategy (e.g., device-farm/emulator/instrumentation-test integration) — a large, separate design effort, explicitly out of scope for "publish more variants," and explicitly declared "Out of scope" by the maintainer already. **Not a viable near-term fix for Kompact's specific targets.**

### (b) Make dependency injection target/source-set-aware or configurable/opt-in

Two different versions of this option exist, with different risk profiles:

- **(b‑minimal) Fail fast with an actionable error, without changing what fails.** Add a reactive listener (the same `kotlin.targets.withType(...).all { }` pattern already used at `MutflowKmpSupport.kt:80-86`) that, as each native target is added, checks whether its `konanTarget` has a published MutFlow variant, and if not, throws a `GradleException` naming the unsupported target and pointing directly at the `apply(false)` + conditional `pluginManager.apply(...)` pattern (i.e., document-the-workaround-in-the-error-message). This **does not change the `enabled`/compile-safety design at all** — it only replaces Gradle's generic, mutflow-agnostic "no matching variant" stack trace with an immediate, specific, actionable message. Low risk, small diff, does not touch the eager-dependency-for-compile-safety guarantee. Still a **behavior change** (new fail-fast point, new error text), so per `CONTRIBUTING.md` it needs a discussion issue first, but it is a strong, minimal candidate.
- **(b‑full) Add a first-class opt-in "which platforms should MutFlow wire into" DSL** (e.g., `mutflow { platforms = setOf("jvm") }`), so `configure()` can skip the `commonMain`/`commonTest` dependency declarations for excluded targets' compilations. This is architecturally harder than it sounds: `commonMain` is shared by *all* targets via the default hierarchy template, so "scope out some targets" cannot simply skip a dependency declaration on `commonMain` itself without either (i) introducing new intermediate source sets per supported-target-subset (a nontrivial restructuring of the plugin's source-set model), or (ii) reintroducing the "code using `@MutationTarget`/`MutFlow.underTest` in common source may not compile for excluded targets" problem the current unconditional design was built to avoid (§2.3). **This is the deepest, highest-risk option and is not obviously worth its complexity given that the equivalent outcome is already fully achievable today using stock Gradle (conditional plugin application) plus MutFlow's existing Gradle-DSL `targets` FQN mechanism plus a JVM-only test source set — exactly what Kompact already did (§3, "existing primitives" below).**

**Existing primitives that already make (b) largely unnecessary for consumers today:** MutFlow already ships a Gradle-DSL-only way to select mutation targets by fully-qualified class name pattern — `mutflow { targets = listOf("com.example.Calculator", "com.example.service.*") }`, confirmed in `README.md`'s "Specifying Mutation Targets" section and `MutflowExtension.targets: ListProperty<String>` (`MutflowGradlePlugin.kt:20`, consumed at `MutflowGradlePlugin.kt:280-282` via `SubpluginOption("target", target)`). This sidesteps needing the `@MutationTarget` annotation in common source at all. Combined with standard Gradle plugin-application deferral (`apply false` + conditional `pluginManager.apply(...)`, a stock Gradle idiom requiring zero MutFlow code changes) and a project-authored JVM-only wrapper test source set, a consumer can **already** fully avoid the `commonMain`/`commonTest` wiring for any subset of targets — this is precisely Kompact's fix (§3, Kompact section below). **This substantially weakens the urgency case for (b‑full)**: the capability exists; what's missing is *documentation that this pattern is the supported way to do it* (→ option c), not new plugin code.

### (c) Document the limitation/workaround explicitly

Lowest-risk, fastest, and per `CONTRIBUTING.md` requires **no discussion issue at all** — the policy explicitly states *"Bug fixes and documentation improvements are of course always welcome as direct pull requests"* (`anschnapp/mutflow:CONTRIBUTING.md`, "Start with a Discussion, Not a Pull Request" section). Concrete, scoped additions that would close the gap identified in §2.8:
1. A one-paragraph caveat in "Disabling Mutation Testing" (`README.md:113-136`) cross-referencing the KMP section: *"In a Kotlin Multiplatform project, `mutflow.enabled=false` does not prevent `commonMain`/`commonTest` from depending on `mutflow-annotations`/`mutflow-runtime` for every declared target — see Kotlin Multiplatform Support → Current limitations."*
2. A new bullet in the KMP "Current limitations" list (`README.md:662-683`) stating the `enabled=false`-does-not-avoid-resolution fact explicitly, and naming the `apply(false)` + conditional `pluginManager.apply(...)` pattern as the supported workaround for projects that declare targets MutFlow does not publish.
3. Optionally, a short "Using MutFlow in a KMP project with unsupported targets" worked example, modeled directly on Kompact's own (already working, already in a public repo) fix.

### (d) No change

Defensible as a *minimal-risk* baseline given the design is intentional and already mostly documented in general terms (§1.3, §2.6) — but leaves the exact gap in §2.8 unaddressed, meaning the next KMP adopter with a mixed supported/unsupported target set will most likely rediscover this the same way Kompact did: via an opaque Gradle resolution failure during a "just trying it out" build, rather than from the docs. Given (c) is low-risk and directly addressable without any discussion-issue friction, "no change" is not the recommended option.

---

## 4. Recommendation

### Primary recommendation: raise an upstream **discussion issue** (not a PR) proposing (b‑minimal) + documenting (c); do not claim a PR should be filed

`anschnapp/mutflow`'s `CONTRIBUTING.md` is explicit and leaves no ambiguity about process:

> "If you'd like to propose a new feature or a change in behavior, please open a discussion issue first before writing any code… Bug fixes and documentation improvements are of course always welcome as direct pull requests."
— `anschnapp/mutflow:CONTRIBUTING.md` ([permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/CONTRIBUTING.md))

The maintainer's own recent history shows this process working in practice: issues **#23** ("Discussion: per-test wall-clock budget for mutants that hang outside loops") and **#40** ("Discussion: a kill by a test that fails on and off hides a survivor") are both titled `Discussion: …`, opened by a third-party contributor, and (in #23's case) closed by the maintainer himself within a month after a design conversation — a clear, working, recent precedent for exactly this process (`https://github.com/anschnapp/mutflow/issues/23`, `https://github.com/anschnapp/mutflow/issues/40`).

Classifying this report's findings against that policy:
- The **fail-fast actionable-error proposal (b‑minimal)** is a *behavior change* (a new place the build can fail, with new text) — **requires a discussion issue first**, not a direct PR.
- The **documentation clarification (c)** is explicitly pre-approved for a **direct PR** per policy — but per this task's constraints, **no PR is being filed or claimed as warranted by this research alone**; this report only identifies it as the lowest-risk, immediately-actionable improvement a maintainer or future contributor could make.

**Concrete next action if/when someone acts on this research:** open one upstream GitHub discussion issue bundling both the documentation gap and the fail-fast proposal (consistent with how #23/#40 bundle a problem statement with a proposed fix), titled and scoped as follows.

#### Draft issue title
> Discussion: KMP `commonMain`/`commonTest` dependency wiring ignores `mutflow.enabled` and fails hard on unsupported targets

#### Problem statement (draft)
Applying the MutFlow plugin to a Kotlin Multiplatform project with any declared target outside the published set (e.g. `androidNativeArm64`, `iosArm64`) fails that target's compilation with a Gradle "no matching variant" resolution error — **even when `mutflow.enabled=false`** — because `MutflowKmpSupport.configure()` adds `mutflow-annotations`/`mutflow-runtime` to `commonMain`/`commonTest` unconditionally, before the `enabled` gate is read (`MutflowKmpSupport.kt:54-73`). This is consistent with the project's documented "published target set is the supported set" policy (CHANGELOG `v1.2.0`), but the "Disabling Mutation Testing" section's "zero overhead" claim does not warn KMP users that disabling does not avoid this, and the failure's Gradle error message gives no indication that MutFlow, or the `apply(false)` workaround, is involved at all.

#### Proposed behavior / minimal change (draft, for discussion — not proposing to implement without maintainer buy-in)
1. **Docs (direct-PR-eligible per CONTRIBUTING.md):** cross-reference the "Disabling Mutation Testing" and KMP "Current limitations" sections; state explicitly that `enabled=false` does not prevent `commonMain`/`commonTest` resolution for declared targets; document the `apply(false)` + conditional `pluginManager.apply(...)` pattern as the supported way to scope MutFlow to a subset of a KMP project's targets.
2. **Code (discussion-gated):** when `MutflowKmpSupport.configure()` observes a declared native target whose `konanTarget` has no published MutFlow variant, fail immediately with a MutFlow-specific `GradleException` naming the target and linking to the workaround, instead of letting Gradle's generic variant-resolution error surface. No change to which targets are supported, no change to the eager-dependency/compile-safety design for supported targets.

#### Acceptance tests (draft)
- A KMP project declaring only `jvm()` + `linuxX64()` continues to build and run `mutflowJvmTest`/`mutflowLinuxX64Test` unchanged (regression check).
- A KMP project declaring `jvm()` + `androidNativeArm64()` with the plugin applied directly (no `apply(false)` guard) now fails configuration with a MutFlow-authored message naming `androidNativeArm64` and the workaround, instead of Gradle's generic "no matching variant" trace.
- The same project, using the documented `apply(false)` + conditional-apply pattern, continues to build normally end-to-end (i.e., the documented workaround keeps working exactly as Kompact's does today).
- `mutflow.enabled=false` on a pure-`jvm()`-only (no unsupported targets) KMP project still compiles with zero added behavior (no regression to the existing "still compiles with annotations available" promise).

#### Risks (draft)
- A new fail-fast point is itself a behavior change for any existing consumer currently relying on (or simply not having hit) the current silent-until-Gradle-resolves error — low probability given the failure already occurs today for such projects, but worth flagging in the discussion issue.
- Maintainer may prefer "no code change, docs only" (option c/d) as sufficient, consistent with the project's stated preference for a tightly-scoped tool (`CONTRIBUTING.md`, "About the Mutation Set" — though that section is about mutation operators specifically, the same "pragmatic, focused tool" ethos could reasonably extend to declining extra configuration surface for an explicitly out-of-scope target class).
- The "young… may still be revised" caveat MutFlow already applies to its KMP configuration surface generally (`README.md:680-683`, "Current limitations" final bullet) suggests the maintainer is already cautious about adding more DSL surface here, which should temper expectations for (b‑full) in particular.

### Why not a PR right now
Per this task's explicit constraint and per `CONTRIBUTING.md`'s own policy, the only piece of this that would be pre-approved for a direct PR (the documentation fix) is exactly the piece this research is not authorized to file. The behavior-changing piece (b‑minimal) requires a discussion issue first regardless. **No PR should be claimed as warranted from this research; the appropriate next action, if pursued, is the discussion issue drafted above.**

### Gaps and uncertainties
- GitHub's search API is not exhaustive; it is possible (though five targeted queries plus a scan of all 6 open issues found nothing) that this exact interaction has been raised in a closed issue using different phrasing, or discussed outside GitHub (Discussions are disabled on this repo: `"has_discussions":false` in the repo API response).
- This report relies on the GitHub REST/Search API and raw file fetches captured on 2026‑10‑03; repository state (tags, issues) could change after this date.
- The feasibility sketch for (b‑minimal)/(b‑full) is this report's own design analysis against the read source, not something validated by the maintainer — it is offered as a discussion starting point, not a verified-correct patch.
- Kompact's own build was not re-run as part of this research (no code changes were made, per task constraints); the "normal CI is green, mutation report shows 33/22/3/8/0" facts are taken from the already-existing session record and the repository's current (`703574d`) state, not independently re-executed here.

---

## 5. Citations

**Upstream `anschnapp/mutflow`, pinned at tag `v1.6.0` = commit `4734e39cb7a8e3e64ec742be89b6e353a6fdfc58`:**
- Repo metadata, tags, releases: `https://api.github.com/repos/anschnapp/mutflow`, `https://api.github.com/repos/anschnapp/mutflow/tags`, `https://api.github.com/repos/anschnapp/mutflow/releases` (fetched 2026‑10‑03; latest tag `v1.6.0`, zero releases).
- `anschnapp/mutflow:mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowKmpSupport.kt:46-87` — [permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowKmpSupport.kt#L46-L87) — the `configure()` function; dependency declarations `L54-59`, enabled-gate + comment `L61-73`.
- `anschnapp/mutflow:mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowKmpSupport.kt:258-268` — [permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowKmpSupport.kt#L258-L268) — `HostManager.host` exact-match gate on orchestrator task registration.
- `anschnapp/mutflow:mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowGradlePlugin.kt:98-141` — [permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowGradlePlugin.kt#L98-L141) — `apply()`; KMP vs. plain-JVM code paths, the JVM-path disabled-branch dependency fallback.
- `anschnapp/mutflow:mutflow-gradle-plugin/src/main/kotlin/io/github/anschnapp/mutflow/gradle/MutflowGradlePlugin.kt:18-63` — `MutflowExtension` (`enabled`, `targets: ListProperty<String>`, run-loop settings).
- `anschnapp/mutflow:DESIGN-MULTIPLATFORM.md:214-237` — [permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/DESIGN-MULTIPLATFORM.md#L214-L237) — "Supported Targets" table and "Publishing a target is a support promise…" paragraph.
- `anschnapp/mutflow:DESIGN-MULTIPLATFORM.md:723-735` — [permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/DESIGN-MULTIPLATFORM.md#L723-L735) — "Open Questions" (searched; no mention of this interaction).
- `anschnapp/mutflow:README.md:113-136` — [permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/README.md#L113-L136) — "Disabling Mutation Testing."
- `anschnapp/mutflow:README.md:662-692` — [permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/README.md#L662-L692) — KMP "Current limitations" and "Trying an unpublished target."
- `anschnapp/mutflow:CHANGELOG.md` — [permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/CHANGELOG.md) — `## [1.2.0]` (KMP introduction + "Known limitations" bullet, verbatim quoted in §1.3/§3a); `## [1.6.0]` (latest entry, unrelated per-test timeout-budget feature).
- `anschnapp/mutflow:CONTRIBUTING.md` — [permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/CONTRIBUTING.md) — discussion-first-for-behavior-change / direct-PR-for-docs-and-bugfixes policy.
- `anschnapp/mutflow:gradle.properties` — [permalink](https://github.com/anschnapp/mutflow/blob/4734e39cb7a8e3e64ec742be89b6e353a6fdfc58/gradle.properties) — `kotlinVersion=2.4.20`, `junitVersion=6.1.3`.
- `https://repo1.maven.org/maven2/io/github/anschnapp/mutflow/mutflow-annotations/1.6.0/mutflow-annotations-1.6.0.module` and the equivalent `mutflow-runtime` path — published Gradle Module Metadata, fetched directly from Maven Central 2026‑10‑03; confirms exactly `metadata`/`jvm`/`linuxX64`/`mingwX64` variants, no Apple/Android variants.
- `https://api.github.com/search/issues?q=repo:anschnapp/mutflow+android_arm64+OR+androidNativeArm64+OR+iosArm64`, `...+%22no+matching+variant%22`, `...+%22mutflow.enabled%22` — zero results each (fetched 2026‑10‑03).
- `https://github.com/anschnapp/mutflow/issues/14`, `/issues/23`, `/issues/40` — related/precedent issues reviewed (PR #14 unrelated multiplatform rewrite, closed not merged; #23/#40 discussion-first precedent, both opened by community contributor `rikshot`).

**Kompact trial (`trancee/kompact`), current `HEAD` = commit `703574da42dc0993d45069a788a3456af27784f0`:**
- `trancee/kompact:kompact/build.gradle.kts:14` — [permalink](https://github.com/trancee/kompact/blob/703574da42dc0993d45069a788a3456af27784f0/kompact/build.gradle.kts#L14) — `id("io.github.anschnapp.mutflow") version "1.6.0" apply false`.
- `trancee/kompact:kompact/build.gradle.kts:22-41` — [permalink](https://github.com/trancee/kompact/blob/703574da42dc0993d45069a788a3456af27784f0/kompact/build.gradle.kts#L22-L41) — the `mutationJvmOnly` guard, including the comment *"MutFlow 1.6.0 injects dependencies into common source sets. Apply it only when the reduced model contains JVM, the target for which it publishes variants"* (`L34-36`), and Gradle-DSL FQN targeting (`L39`) instead of the `@MutationTarget` annotation.
- `trancee/kompact:kompact/build.gradle.kts:69-73` — [permalink](https://github.com/trancee/kompact/blob/703574da42dc0993d45069a788a3456af27784f0/kompact/build.gradle.kts#L69-L73) — native targets (`iosArm64()`, `iosSimulatorArm64()`, `androidNativeArm64()`) declared only when `!mutationJvmOnly`.
- `trancee/kompact:kompact/build.gradle.kts:137-144` — [permalink](https://github.com/trancee/kompact/blob/703574da42dc0993d45069a788a3456af27784f0/kompact/build.gradle.kts#L137-L144) — JVM-only `mutatedTest` source directory wiring to `src/mutflowTest/kotlin`.
- Commit `32a2e10dbb6b61ed0a2b7053f0c257750fd46063` — [commit link](https://github.com/trancee/kompact/commit/32a2e10dbb6b61ed0a2b7053f0c257750fd46063) — the initial, flawed attempt (unconditional `plugins{}` application) that reproduced the reported failure.
- Commit `703574da42dc0993d45069a788a3456af27784f0` — [commit link](https://github.com/trancee/kompact/commit/703574da42dc0993d45069a788a3456af27784f0) — the fix (deferred/conditional plugin application, DSL targeting, isolated JVM-only adapter tests).
- Session record `9921caea-2ccf-46eb-92e3-62e6ee87e44e` (local session store) — exact mutation outcome figures (33 evaluated, 22 killed, 3 survived, 8 timed out, 0 gaps) and confirmation that normal (non-mutation) CI is green post-fix.

**This toolkit (`mutation-testing-agent-toolkit`), for conventions and precedent only:**
- `docs/agents/issue-tracker.md` — `.scratch/<feature-slug>/{research,issues}/NN-slug.md` convention followed for this report's placement.
- `docs/explanation/mutflow-architecture.md`, `docs/how-to/troubleshoot-mutation-testing.md`, `docs/tutorials/kmp-jvm-mutation-test.md` — existing citations of the same `v1.6.0` design doc, corroborated (not merely repeated) by this report's independent source inspection.
- `.scratch/omp-mutation-testing/research/02-mutflow-kmp-support.md`, `.scratch/scott-cc-comparison/issues/04-decide-upstream-recommendations.md` — structural precedent for this report's format and for how this repository has previously evaluated upstream-contribution-worthiness.
