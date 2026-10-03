package ch.trancee.mutation

import ch.trancee.mutation.MutationResultsParser.parseMutflowSummary
import ch.trancee.mutation.MutationResultsParser.detectRedundantTestGroups
import ch.trancee.mutation.MutationResultsParser.detectGaps
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.*

class MutationResultsParserTest {

    @Test
    fun `multi-killer mutation captures all killing tests`() {
        val stdout = """
            ✓ (Calculator.kt:7) > → >=
                killed by: testIsPositive
                killed by: testIsPositiveBoundary
                killed by: testPositiveNumbers
        """.trimIndent()

        val mutations = parseMutflowSummary(stdout)
        assertEquals(1, mutations.size)

        val mutation = mutations[0]
        assertEquals(MutationResultType.Killed, mutation.result)
        assertEquals("Calculator.kt:7", mutation.sourceLocation)
        assertEquals(">", mutation.originalOperator)
        assertEquals(">=", mutation.variantOperator)
        assertEquals(3, mutation.killedByTests.size)
        assertEquals("testIsPositive", mutation.killedByTest)
        assertTrue(mutation.killedByTests.contains("testIsPositive"))
        assertTrue(mutation.killedByTests.contains("testIsPositiveBoundary"))
        assertTrue(mutation.killedByTests.contains("testPositiveNumbers"))
    }

    @Test
    fun `survived mutation has no killer`() {
        val stdout = """
            ✗ (Calculator.kt:8) >= → >
                SURVIVED - no test caught this mutation!
        """.trimIndent()

        val mutations = parseMutflowSummary(stdout)
        assertEquals(1, mutations.size)

        val mutation = mutations[0]
        assertEquals(MutationResultType.Survived, mutation.result)
        assertNull(mutation.killedByTest)
        assertTrue(mutation.killedByTests.isEmpty())
    }

    @Test
    fun `timed-out mutation has no killer`() {
        val stdout = """
            ⏱ (Calculator.kt:12) + → *
                TIMED OUT - likely causes an infinite loop
        """.trimIndent()

        val mutations = parseMutflowSummary(stdout)
        assertEquals(1, mutations.size)

        val mutation = mutations[0]
        assertEquals(MutationResultType.TimedOut, mutation.result)
        assertNull(mutation.killedByTest)
        assertTrue(mutation.killedByTests.isEmpty())
    }

    @Test
    fun `empty stdout yields no mutations`() {
        val mutations = parseMutflowSummary("")
        assertTrue(mutations.isEmpty())
    }

    @Test
    fun `mixed results parse correctly`() {
        val stdout = """
            ✓ (Calculator.kt:7) > → >=
                killed by: testIsPositive
                killed by: testIsPositiveBoundary
            ✗ (Calculator.kt:8) >= → >
                SURVIVED - no test caught this mutation!
            ⏱ (Calculator.kt:12) + → *
                TIMED OUT - likely causes an infinite loop
        """.trimIndent()

        val mutations = parseMutflowSummary(stdout)
        assertEquals(3, mutations.size)
        assertEquals(MutationResultType.Killed, mutations[0].result)
        assertEquals(MutationResultType.Survived, mutations[1].result)
        assertEquals(MutationResultType.TimedOut, mutations[2].result)
        assertEquals(2, mutations[0].killedByTests.size)
    }

    @Test
    fun `malformed lines are skipped`() {
        val stdout = """
            Some random log line
            ✓ (Calculator.kt:7) > → >=
                killed by: testIsPositive
            Another random line
        """.trimIndent()

        val mutations = parseMutflowSummary(stdout)
        assertEquals(1, mutations.size)
        assertEquals(MutationResultType.Killed, mutations[0].result)
    }

    @Test
    fun `unicode box-drawing character is stripped from killed-by lines`() {
        val stdout = """
            ✓ (Calculator.kt:7) > → >=
                ║ killed by: testIsPositive
        """.trimIndent()

        val mutations = parseMutflowSummary(stdout)
        assertEquals(1, mutations.size)
        assertEquals(1, mutations[0].killedByTests.size)
        assertEquals("testIsPositive", mutations[0].killedByTests[0])
    }

    @Test
    fun `various box-drawing characters are stripped`() {
        val stdout = """
            ✓ (Calculator.kt:7) > → >=
                │ killed by: testIsPositive
                ┃ killed by: testIsPositiveBoundary
                ╎ killed by: testPositiveNumbers
        """.trimIndent()

        val mutations = parseMutflowSummary(stdout)
        assertEquals(1, mutations.size)
        assertEquals(3, mutations[0].killedByTests.size)
        assertEquals("testIsPositive", mutations[0].killedByTests[0])
        assertEquals("testIsPositiveBoundary", mutations[0].killedByTests[1])
        assertEquals("testPositiveNumbers", mutations[0].killedByTests[2])
    }

    @Test
    fun `redundant group detected when 6 tests share identical signature`() {
        // 6 tests all kill the same mutation → identical signature → redundant group
        val mutations = listOf(
            MutationResult("(Calc.kt:7)", ">", ">=", MutationResultType.Killed, null,
                listOf("testA", "testB", "testC", "testD", "testE", "testF")),
        )
        val groups = detectRedundantTestGroups(mutations)
        assertEquals(1, groups.size)
        assertEquals(6, groups[0].count)
        assertEquals(6, groups[0].tests.size)
        assertTrue(groups[0].tests.contains("testA"))
        assertEquals(1, groups[0].failureSignature.size)
        assertEquals("(Calc.kt:7):>->>=", groups[0].failureSignature[0])
    }

    @Test
    fun `five tests with identical signature is not redundant`() {
        val mutations = listOf(
            MutationResult("(Calc.kt:7)", ">", ">=", MutationResultType.Killed, null,
                listOf("testA", "testB", "testC", "testD", "testE")),
        )
        val groups = detectRedundantTestGroups(mutations)
        assertEquals(0, groups.size)
    }
    @Test
    fun `different signatures are not grouped`() {
        val mutations = listOf(
            MutationResult("(Calc.kt:7)", ">", ">=", MutationResultType.Killed, null,
                listOf("testA", "testB", "testC", "testD", "testE", "testF")),
            MutationResult("(Calc.kt:8)", ">=", ">", MutationResultType.Killed, null,
                listOf("testA", "testB", "testC", "testD", "testE", "testF")),
            MutationResult("(Calc.kt:9)", "+", "*", MutationResultType.Killed, null,
                listOf("testG", "testH", "testI")),
        )
        val groups = detectRedundantTestGroups(mutations)
        // testA-F (6 tests, same signature {7, 8}) → redundant
        // testG-I (3 tests, signature {9}) → below threshold
        assertEquals(1, groups.size)
        assertEquals(6, groups[0].count)
    }


    @Test
    fun `zombies with empty signatures are not flagged as redundant`() {
        val mutations = listOf(
            MutationResult("(Calc.kt:7)", ">", ">=", MutationResultType.Survived), // no killer tests
            MutationResult("(Calc.kt:8)", ">=", ">", MutationResultType.Survived),
        )
        val groups = detectRedundantTestGroups(mutations)
        assertEquals(0, groups.size)
    }

    @Test
    fun `multiple redundant groups are sorted by count descending`() {
        val mutations = listOf(
            MutationResult("(A.kt:1)", ">", ">=", MutationResultType.Killed, null,
                listOf("a1", "a2", "a3", "a4", "a5", "a6", "a7")),
            MutationResult("(B.kt:2)", ">", ">=", MutationResultType.Killed, null,
                listOf("b1", "b2", "b3", "b4", "b5", "b6")),
        )
        val groups = detectRedundantTestGroups(mutations)
        assertEquals(2, groups.size)
        assertEquals(7, groups[0].count)
        assertEquals(6, groups[1].count)
    }

    @Test
    fun `detectGaps returns NO_OUTPUT for empty stdout`() {
        val gaps = MutationResultsParser.detectGaps(
            stdout = "",
            mutations = emptyList(),
        )
        assertEquals(1, gaps.size)
        assertEquals("NO_OUTPUT", gaps[0].type)
    }

    @Test
    fun `detectGaps returns NO_OUTPUT when stdout non-empty but no mutations parsed`() {
        val gaps = MutationResultsParser.detectGaps(
            stdout = "mutflow summary output without recognizable lines",
            mutations = emptyList(),
        )
        assertEquals(1, gaps.size)
        assertEquals("NO_OUTPUT", gaps[0].type)
    }

    @Test
    fun `detectGaps returns empty for normal output`() {
        val stdout = """
            ✓ (Calculator.kt:7) > → >=
                killed by: testIsPositive
            ✗ (Calculator.kt:8) >= → >
                SURVIVED - no test caught this mutation!
        """.trimIndent()
        val mutations = parseMutflowSummary(stdout)
        val gaps = MutationResultsParser.detectGaps(stdout, mutations)
        assertEquals(0, gaps.size)
    }

    @Test
    fun `detectGaps detects PARTIAL_RUN from actual upstream counters`() {
        val stdout = """
            ✓ (Calc.kt:1) > → >=
                killed by: testA
            ║  Total mutations discovered: 5 ║
            ║  Tested this run: 5 ║
            ║  Remaining untested: 0 ║
        """.trimIndent()
        val mutations = parseMutflowSummary(stdout) // finds 1 mutation
        val gaps = MutationResultsParser.detectGaps(stdout, mutations)
        assertTrue(gaps.any { it.type == "PARTIAL_RUN" })
    }

    @Test
    fun `budgeted runs retain discovered and untested counts without a gap`() {
        val stdout = """
            ║  Total mutations discovered: 32 ║
            ║  Tested this run: 1 ║
            ║  Remaining untested: 31 ║
            ✓ (Calc.kt:1) > → >=
                killed by: testA
        """.trimIndent()
        val mutations = parseMutflowSummary(stdout)

        val report = MutationResultsParser.assembleResults(
            mutations, listOf("testA"),
            gaps = detectGaps(stdout, mutations),
            discoveredMutations = MutationResultsParser.discoveredCount(stdout)!!,
        )

        assertEquals(32, report.totalMutations)
        assertEquals(1, report.mutationsEvaluated)
        assertEquals(31, report.untestedMutations)
        assertEquals(0, report.gaps)
        assertEquals(1.0, report.mutationScore)
    }

    @Test
    fun `valid zero discovery summary is not an execution gap`() {
        val stdout = """
            ║  Total mutations discovered: 0 ║
            ║  Tested this run: 0 ║
            ║  Remaining untested: 0 ║
        """.trimIndent()

        val gaps = detectGaps(stdout, emptyList())

        assertTrue(gaps.isEmpty())
    }

    @Test
    fun `remaining counter mismatch is a partial run even when every detail was parsed`() {
        val stdout = """
            Total mutations discovered: 4
            Tested this run: 1
            Remaining untested: 2
            ✓ (Calc.kt:1) > → >=
                killed by: boundary()
        """.trimIndent()
        val mutations = parseMutflowSummary(stdout)

        val gaps = detectGaps(stdout, mutations)

        assertEquals("PARTIAL_RUN", gaps.single().type)
    }

    @Test
    fun `multiple complete summaries aggregate discovered counts and retain budgets`() {
        val stdout = """
            Total mutations discovered: 2
            Tested this run: 1
            Remaining untested: 1
            ✓ (Calc.kt:1) > → >=
                killed by: boundary()
            Total mutations discovered: 3
            Tested this run: 1
            Remaining untested: 2
            ✗ (Calc.kt:2) + → -
        """.trimIndent()
        val mutations = parseMutflowSummary(stdout)

        val gaps = detectGaps(stdout, mutations)

        assertTrue(gaps.isEmpty())
        assertEquals(5, MutationResultsParser.discoveredCount(stdout))
    }

    @Test
    fun `discovered count smaller than evaluated count is rejected at assembly`() {
        val mutations = listOf(MutationResult("Calc.kt:1", ">", ">=", MutationResultType.Killed))

        val failure = assertThrows(IllegalArgumentException::class.java) {
            MutationResultsParser.assembleResults(mutations, emptyList(), discoveredMutations = 0)
        }

        assertTrue(failure.message!!.contains("Discovered count is smaller"))
    }

    @Test
    fun `zero discovery across multiple sessions is not missing output`() {
        val stdout = List(2) {
            "Total mutations discovered: 0\nTested this run: 0\nRemaining untested: 0"
        }.joinToString("\n")

        val gaps = detectGaps(stdout, emptyList())

        assertTrue(gaps.isEmpty())
        assertEquals(0, MutationResultsParser.discoveredCount(stdout))
    }

    @Test
    fun `counter errors cannot cancel each other across sessions`() {
        val stdout = """
            Total mutations discovered: 2
            Tested this run: 1
            Remaining untested: 0
            ✓ (Calc.kt:1) > → >=
            Total mutations discovered: 1
            Tested this run: 1
            Remaining untested: 1
            ✗ (Calc.kt:2) + → -
        """.trimIndent()
        val mutations = parseMutflowSummary(stdout)

        val gaps = detectGaps(stdout, mutations)

        assertEquals("PARTIAL_RUN", gaps.single().type)
    }

    @Test
    fun `detectGaps preserves build-level gaps passed in`() {
        val buildGap = ExecutionGap(
            type = "COMPILATION_FAILURE",
            reason = "IR transformation error",
            testClass = "CalculatorTest",
        )
        val gaps = MutationResultsParser.detectGaps(
            stdout = "",
            mutations = emptyList(),
            buildLevelGaps = listOf(buildGap),
        )
        // Should have the build-level gap, and NO_OUTPUT is skipped because build gap exists
        assertEquals(1, gaps.size)
        assertEquals("COMPILATION_FAILURE", gaps[0].type)
    }
}
