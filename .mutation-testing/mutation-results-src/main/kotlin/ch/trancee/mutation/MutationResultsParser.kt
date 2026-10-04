package ch.trancee.mutation

import java.util.regex.Pattern

/**
 * Pure parsing and computation functions for mutflow's MutationTestingSummary output.
 *
 * These functions have no Gradle dependency — they can be unit-tested directly.
 * The Gradle [MutationResultsTask] is a thin adapter that calls these.
 */
object MutationResultsParser {

    /**
     * Parses mutflow's MutationTestingSummary from captured JUnit XML `<system-out>`.
     *
     * mutflow output format (with multi-killer support):
     * ```
     * ✓ (Calculator.kt:7) > → >=
     *     killed by: isPositive returns false for zero()
     *     killed by: testAnotherMethod()
     * ✗ (Calculator.kt:8) >= → >
     *     SURVIVED - no test caught this mutation!
     * ⏱ (Calculator.kt:12) + → *
     *     TIMED OUT - likely causes an infinite loop
     * ```
     *
     * Multiple "killed by:" lines per mutation are captured (all recorded killers for each mutation).
     */
    fun parseMutflowSummary(stdout: String): List<MutationResult> {
        val mutations = mutableListOf<MutationResult>()

        val mutationPattern = Pattern.compile(
            """([✓✗⏱])\s*\(([^)]+)\)\s+(.+?)\s*(?:→|->)\s*(.+)"""
        )
        val killedByPattern = Pattern.compile("""(?:killed by:?\s*(.+))""")

        val lines = stdout.lines().filter { it.isNotBlank() }
        var i = 0
        while (i < lines.size) {
            val line = lines[i].replace(Regex("[\\u2500-\\u257F]"), "").trim()
            val matcher = mutationPattern.matcher(line)
            if (matcher.matches()) {
                val statusIcon = matcher.group(1)
                val sourceLocation = matcher.group(2)
                val originalOp = matcher.group(3).trim()
                val variantOp = matcher.group(4).trim()

                val result = when (statusIcon) {
                    "✓" -> MutationResultType.Killed
                    "✗" -> MutationResultType.Survived
                    "⏱" -> MutationResultType.TimedOut
                    else -> continue // skip unrecognized status icons
                }

                val killedByTests = mutableListOf<String>()
                val killedByTest: String? = if (result == MutationResultType.Killed) {
                    // Collect ALL "killed by:" lines that follow (full killer set)
                    var j = i + 1
                    while (j < lines.size) {
                        val nextLine = lines[j].replace(Regex("[\\u2500-\\u257F]"), "").trim()
                        val killedMatcher = killedByPattern.matcher(nextLine)
                        if (killedMatcher.matches()) {
                            killedByTests.add(killedMatcher.group(1).trim())
                            j++ // consume the killed-by line
                        } else {
                            break // stop at first non-killed-by line
                        }
                    }
                    i = j - 1 // advance past all consumed killed-by lines
                    killedByTests.firstOrNull()
                } else {
                    null
                }

                mutations.add(MutationResult(
                    sourceLocation = sourceLocation,
                    originalOperator = originalOp,
                    variantOperator = variantOp,
                    result = result,
                    killedByTest = killedByTest,
                    killedByTests = killedByTests,
                ))
            }
            i++
        }
        return mutations
    }

    /**
     * Calculates mutation score, quality band, confidence level, confidence interval,
     * and totals from parsed mutation results, accounting for execution gaps.
     *
     * Score = killed / evaluated. Infrastructure gaps never subtract evaluated
     * mutations; any gap makes the aggregate score and interval unavailable.
     *
     * Confidence interval uses the Wilson score interval (appropriate for proportions,
     * especially near 0 or 1 where the normal approximation degrades).
     */
    fun calculateMetrics(
        mutations: List<MutationResult>,
        gaps: Int = 0,
    ): MutationStats {
        val total = mutations.size
        val killed = mutations.count { it.result == MutationResultType.Killed }
        val survived = mutations.count { it.result == MutationResultType.Survived }
        val timedOut = mutations.count { it.result == MutationResultType.TimedOut }
        require(gaps >= 0) { "Execution gap count must be nonnegative" }
        val evaluated = total
        val score: Double? = if (evaluated > 0 && gaps == 0) killed.toDouble() / evaluated else null

        val band = score?.let { s ->
            when {
                s > 0.8 -> QualityBand.Excellent
                s > 0.6 -> QualityBand.Good
                s > 0.3 -> QualityBand.Fair
                else -> QualityBand.Poor
            }
        } ?: QualityBand.Poor

        val (ciLow, ciHigh) = if (evaluated > 0 && score != null) {
            wilsonInterval(killed, evaluated)
        } else {
            null to null
        }

        val confidence = when {
            total < 10 -> ConfidenceLevel.Low
            total <= 50 -> ConfidenceLevel.Medium
            else -> ConfidenceLevel.High
        }

        return MutationStats(
            score = score,
            band = band,
            confidence = confidence,
            total = total,
            killed = killed,
            survived = survived,
            timedOut = timedOut,
            gaps = gaps,
            mutationsEvaluated = evaluated,
            confidenceIntervalLow = ciLow,
            confidenceIntervalHigh = ciHigh,
        )
    }

    /**
     * Wilson score 95% confidence interval for a binomial proportion.
     * Returns (low, high) bounds. Used for mutation score confidence intervals.
     */
    private fun wilsonInterval(successes: Int, trials: Int): Pair<Double?, Double?> {
        if (trials <= 0) return null to null
        val z = 1.96
        val n = trials.toDouble()
        val phat = successes.toDouble() / n
        val denom = 1 + z * z / n
        val center = (phat + z * z / (2 * n)) / denom
        val margin = z * kotlin.math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
        return Pair(
            maxOf(0.0, center - margin),
            minOf(1.0, center + margin),
        )
    }

    /**
     * Builds the per-test-per-mutation killer matrix: test name → list of
     * mutation source locations it killed.
     */
    fun buildTestKillerMatrix(mutations: List<MutationResult>): Map<String, List<String>> {
        val testKillerMatrix = mutableMapOf<String, MutableList<String>>()
        mutations.forEach { m ->
            m.killedByTests.forEach { testName ->
                testKillerMatrix.getOrPut(testName) { mutableListOf() }.add(m.sourceLocation)
            }
        }
        return testKillerMatrix
    }

    /**
     * Detects redundant test groups: tests that share an identical failure
     * signature (same set of mutations they killed), indicating consolidation
     * opportunities. Groups exceeding [threshold] are returned.
     *
     * Uses composite mutation keys (sourceLocation:originalOp->variantOp) for
     * precision — same approach as the testKillerMatrix but with per-mutation
     * granularity for accurate signature matching.
     */
    fun detectRedundantTestGroups(
        mutations: List<MutationResult>,
        threshold: Int = 5,
    ): List<RedundantGroup> {
        val testSignatures = mutableMapOf<String, MutableSet<String>>()

        mutations.forEach { mutation ->
            if (mutation.result == MutationResultType.Killed) {
                val mutationKey = "${mutation.sourceLocation}:${mutation.originalOperator}->${mutation.variantOperator}"
                mutation.killedByTests.forEach { testName ->
                    testSignatures.getOrPut(testName) { mutableSetOf() }.add(mutationKey)
                }
            }
        }

        val groups = mutableMapOf<Set<String>, MutableList<String>>()
        testSignatures.forEach { (testName, signature) ->
            if (signature.isNotEmpty()) {
                groups.getOrPut(signature.toSet()) { mutableListOf() }.add(testName)
            }
        }

        return groups.filter { it.value.size > threshold }
            .map { (signature, tests) ->
                RedundantGroup(
                    tests = tests.sorted(),
                    count = tests.size,
                    failureSignature = tests.first().let { testSignatures[it] }.orEmpty().sorted(),
                )
            }
            .sortedByDescending { it.count }
    }

    /**
     * Detects execution gaps from mutflow's output at the parser level.
     *
     * Two gap types are detectable from stdout + parsed mutations:
     * - [ExecutionGap] with type "NO_OUTPUT" — stdout is empty or no mutations parsed
     * - "PARTIAL_RUN" — actual upstream tested counters disagree with parsed details
     *
     * Build-level gaps (COMPILATION_FAILURE, IR_TRANSFORMATION_ERROR, BACKSTOP_TIMEOUT)
     * are detected by the Gradle task / test-executor and passed in via [buildLevelGaps].
     */
    fun detectGaps(
        stdout: String,
        mutations: List<MutationResult>,
        buildLevelGaps: List<ExecutionGap> = emptyList(),
    ): List<ExecutionGap> {
        val gaps = buildLevelGaps.toMutableList()

        val testedCounts = summaryCounts(stdout, "Tested this run")
        if (stdout.isBlank()) {
            if (gaps.isEmpty()) {
                gaps.add(ExecutionGap(
                    type = "NO_OUTPUT",
                    reason = "No mutflow output captured — test class may have failed to produce JUnit XML",
                ))
            }
        } else if (mutations.isEmpty() && (testedCounts.isEmpty() || testedCounts.any { it != 0 })) {
            gaps.add(ExecutionGap(
                type = "NO_OUTPUT",
                reason = "Stdout was non-empty but no mutation results could be parsed",
            ))
        }

        val reportedCount = testedCounts.sum()
        if (testedCounts.isNotEmpty() && mutations.size != reportedCount) {
            gaps.add(ExecutionGap(
                type = "PARTIAL_RUN",
                reason = "Parsed ${mutations.size} mutations but mutflow reported $reportedCount tested this run",
            ))
        }

        val discoveredCounts = summaryCounts(stdout, "Total mutations discovered")
        val remainingCounts = summaryCounts(stdout, "Remaining untested")
        if (listOf(discoveredCounts, testedCounts, remainingCounts).any { it.isNotEmpty() } &&
            (discoveredCounts.size != testedCounts.size || remainingCounts.size != testedCounts.size ||
                testedCounts.indices.any { index ->
                    discoveredCounts[index].toLong() !=
                        testedCounts[index].toLong() + remainingCounts[index].toLong()
                })) {
            gaps.add(ExecutionGap(
                type = "PARTIAL_RUN",
                reason = "Mutflow discovered, tested, and remaining counters are missing or inconsistent",
            ))
        }

        return gaps
    }

    fun discoveredCount(stdout: String): Int? =
        summaryCounts(stdout, "Total mutations discovered").takeIf { it.isNotEmpty() }?.sum()

    private fun summaryCounts(stdout: String, label: String): List<Int> =
        Regex("${Regex.escape(label)}:\\s*(\\d+)").findAll(stdout)
            .map { it.groupValues[1].toInt() }.toList()

    /**
     * Assembles a complete [MutationResults] from parsed mutations, test method
     * names, execution gaps, redundant groups, and the generated-at timestamp.
     *
     * If [redundantGroups] is null, redundant groups are computed from the mutations.
     */
    fun assembleResults(
        mutations: List<MutationResult>,
        testMethods: List<String>,
        generatedAt: Long = System.currentTimeMillis(),
        gaps: List<ExecutionGap> = emptyList(),
        redundantGroups: List<RedundantGroup>? = null,
        discoveredMutations: Int = mutations.size,
    ): MutationResults {
        require(discoveredMutations >= mutations.size) { "Discovered count is smaller than evaluated count" }
        val stats = calculateMetrics(mutations, gaps.size)
        val testKillerMatrix = buildTestKillerMatrix(mutations)
        val rg = redundantGroups ?: detectRedundantTestGroups(mutations)

        return MutationResults(
            generatedAt = generatedAt,
            mutationScore = stats.score,
            qualityBand = stats.band,
            confidence = stats.confidence,
            totalMutations = discoveredMutations,
            killed = stats.killed,
            survived = stats.survived,
            timedOut = stats.timedOut,
            gaps = stats.gaps,
            mutationsEvaluated = stats.mutationsEvaluated,
            confidenceIntervalLow = stats.confidenceIntervalLow,
            confidenceIntervalHigh = stats.confidenceIntervalHigh,
            testMethods = testMethods,
            testKillerMatrix = testKillerMatrix,
            mutations = mutations,
            executionGaps = gaps,
            redundantGroups = rg,
            untestedMutations = discoveredMutations - mutations.size,
        )
    }
}
