package ch.trancee.mutation

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class MutationResultsSummaryTest {

    @Test
    fun `renders score counts and actionable mutation details`() {
        val results = MutationResultsParser.assembleResults(
            mutations = listOf(
                MutationResult("Calculator.kt:1", ">", ">=", MutationResultType.Killed),
                MutationResult("Calculator.kt:4", "==", "!=", MutationResultType.Killed),
                MutationResult("Calculator|.kt:2", "<", "<=", MutationResultType.Survived),
                MutationResult("Calculator.kt:3", "0", "-1", MutationResultType.TimedOut),
            ),
            testMethods = listOf("example.CalculatorTest::testBoundary()"),
            generatedAt = 1700000000000L,
            discoveredMutations = 5,
        )

        val failedSummary = MutationResultsSummary.render(results, runFailed = true)
        val passedSummary = MutationResultsSummary.render(
            MutationResultsParser.assembleResults(
                mutations = listOf(
                    MutationResult("Calculator.kt:1", ">", ">=", MutationResultType.Killed),
                ),
                testMethods = listOf("example.CalculatorTest::testBoundary()"),
                generatedAt = 1700000000000L,
            ),
            runFailed = false,
        )

        assertTrue(failedSummary.contains("| Gradle task | FAILED |"))
        assertTrue(passedSummary.contains("| Gradle task | PASSED |"))
        assertTrue(failedSummary.contains("| Mutation score | 50.00% (Fair) |"))
        assertTrue(failedSummary.contains("| Mutations | 5 discovered, 4 evaluated, 1 untested |"))
        assertTrue(failedSummary.contains("| Outcomes | 2 killed, 1 survived, 1 timed out |"))
        assertTrue(failedSummary.contains("| Reported test methods | 1 |"))
        assertTrue(failedSummary.contains("| Survived | <code>Calculator&#124;.kt:2</code> | <code>&lt;</code> -> <code>&lt;=</code> |"))
        assertTrue(failedSummary.contains("| Timed out | <code>Calculator.kt:3</code> | <code>0</code> -> <code>-1</code> |"))
    }

    @Test
    fun `shows unavailable score and escapes execution gap details`() {
        val results = MutationResultsParser.assembleResults(
            mutations = emptyList(),
            testMethods = emptyList(),
            generatedAt = 1700000000000L,
            gaps = listOf(
                ExecutionGap(
                    type = "NO_OUTPUT",
                    reason = "No reports | were found",
                    testClass = "Calculator<Test>",
                ),
            ),
        )

        val summary = MutationResultsSummary.render(results, runFailed = true)

        assertTrue(summary.contains("| Mutation score | Unavailable |"))
        assertTrue(summary.contains("| 95% Wilson CI | Unavailable |"))
        assertTrue(summary.contains("| Execution gaps | 1 |"))
        assertTrue(summary.contains("<code>Calculator&lt;Test&gt;</code>"))
        assertTrue(summary.contains("<code>No reports &#124; were found</code>"))
    }
}
