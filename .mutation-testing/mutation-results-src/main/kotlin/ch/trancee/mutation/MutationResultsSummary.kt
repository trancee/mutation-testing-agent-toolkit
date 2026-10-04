package ch.trancee.mutation

import java.util.Locale

object MutationResultsSummary {

    fun render(results: MutationResults, runFailed: Boolean): String = buildString {
        appendLine("## Mutation testing results")
        appendLine()
        appendLine("| Metric | Result |")
        appendLine("| --- | --- |")
        appendLine("| Gradle task | ${if (runFailed) "FAILED" else "PASSED"} |")
        appendLine("| Mutation score | ${results.mutationScore?.let { "${percent(it)} (${results.qualityBand})" } ?: "Unavailable"} |")
        appendLine("| Confidence | ${results.confidence} |")
        appendLine("| 95% Wilson CI | ${confidenceInterval(results)} |")
        appendLine("| Mutations | ${results.totalMutations} discovered, ${results.mutationsEvaluated} evaluated, ${results.untestedMutations} untested |")
        appendLine("| Outcomes | ${results.killed} killed, ${results.survived} survived, ${results.timedOut} timed out |")
        appendLine("| Execution gaps | ${results.gaps} |")
        appendLine("| Reported test methods | ${results.testMethods.size} |")
        appendLine()
        appendLine("### Survivors and timeouts")
        appendLine()
        val reviewMutations = results.mutations
            .filter { it.result != MutationResultType.Killed }
            .sortedWith(
                compareBy<MutationResult>(
                    { it.sourceLocation },
                    { it.originalOperator },
                    { it.variantOperator },
                ),
            )
        if (reviewMutations.isEmpty()) {
            appendLine("None.")
        } else {
            appendLine("| Outcome | Location | Mutation |")
            appendLine("| --- | --- | --- |")
            reviewMutations.forEach { mutation ->
                appendLine(
                    "| ${outcomeLabel(mutation.result)} | ${code(mutation.sourceLocation)} | " +
                        "${code(mutation.originalOperator)} -> ${code(mutation.variantOperator)} |",
                )
            }
        }
        appendLine()
        appendLine("### Execution gaps")
        appendLine()
        val orderedGaps = results.executionGaps.sortedWith(
            compareBy<ExecutionGap>(
                { it.type },
                { it.testClass.orEmpty() },
                { it.affectedSourceLocation.orEmpty() },
                { it.reason.orEmpty() },
            ),
        )
        if (orderedGaps.isEmpty()) {
            appendLine("None.")
        } else {
            appendLine("| Type | Test class | Location | Details |")
            appendLine("| --- | --- | --- | --- |")
            orderedGaps.forEach { gap ->
                appendLine(
                    "| ${code(gap.type)} | ${code(gap.testClass)} | " +
                        "${code(gap.affectedSourceLocation)} | ${code(gap.reason)} |",
                )
            }
        }
    }.trimEnd()

    private fun confidenceInterval(results: MutationResults): String {
        val low = results.confidenceIntervalLow ?: return "Unavailable"
        val high = results.confidenceIntervalHigh ?: return "Unavailable"
        return "${percent(low)} - ${percent(high)}"
    }

    private fun percent(value: Double): String = String.format(Locale.ROOT, "%.2f%%", value * 100)

    private fun outcomeLabel(result: MutationResultType): String = when (result) {
        MutationResultType.Killed -> "Killed"
        MutationResultType.Survived -> "Survived"
        MutationResultType.TimedOut -> "Timed out"
    }

    private fun code(value: String?): String = value?.let { "<code>${escapeHtml(it)}</code>" } ?: "-"

    private fun escapeHtml(value: String): String = value
        .replace("\r\n", " ")
        .replace('\r', ' ')
        .replace('\n', ' ')
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "&#124;")
}
