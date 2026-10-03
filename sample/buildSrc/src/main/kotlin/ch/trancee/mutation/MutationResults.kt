package ch.trancee.mutation

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Quality band thresholds, matching the original mutation-results.gradle.kts logic:
 *   Excellent: >80%, Good: >60%, Fair: >30%, Poor: ≤30%
 */
enum class QualityBand {
    @SerialName("Excellent") Excellent,
    @SerialName("Good") Good,
    @SerialName("Fair") Fair,
    @SerialName("Poor") Poor,
}

/**
 * Confidence level based on mutation count:
 *   Low: <10, Medium: 10–50, High: >50
 */
enum class ConfidenceLevel {
    @SerialName("Low") Low,
    @SerialName("Medium") Medium,
    @SerialName("High") High,
}

/**
 * An infrastructure failure record, often at test-class granularity.
 * It is not an unevaluated mutation and must never subtract recorded outcomes.
 */
@Serializable
data class ExecutionGap(
    @SerialName("type") val type: String,
    @SerialName("reason") val reason: String? = null,
    @SerialName("testClass") val testClass: String? = null,
    @SerialName("affectedSourceLocation") val affectedSourceLocation: String? = null,
    @SerialName("gradleExitCode") val gradleExitCode: Int? = null,
)

/**
 * A group of tests that share an identical failure signature (same set of
 * mutations they killed), indicating they can be consolidated.
 */
@Serializable
data class RedundantGroup(
    @SerialName("tests") val tests: List<String>,
    @SerialName("count") val count: Int,
    @SerialName("failureSignature") val failureSignature: List<String>,
)

/**
 * Intermediate metrics computed from a list of mutation results.
 * Not serialized directly — its fields are spread into [MutationResults].
 */
data class MutationStats(
    val score: Double?,
    val band: QualityBand,
    val confidence: ConfidenceLevel,
    val total: Int,
    val killed: Int,
    val survived: Int,
    val timedOut: Int,
    val gaps: Int = 0,
    val mutationsEvaluated: Int = 0,
    val confidenceIntervalLow: Double? = null,
    val confidenceIntervalHigh: Double? = null,
)

/**
 * The complete mutation testing results output, serialized to
 * `mutation-results.json` for consumption by the test-auditor agent.
 *
 * Schema 2 versions corrected counts and class-qualified test identities.
 */
@Serializable
data class MutationResults(
    @SerialName("generatedAt") val generatedAt: Long,
    @SerialName("mutationScore") val mutationScore: Double? = null,
    @SerialName("qualityBand") val qualityBand: QualityBand,
    @SerialName("confidence") val confidence: ConfidenceLevel,
    @SerialName("totalMutations") val totalMutations: Int,
    @SerialName("killed") val killed: Int,
    @SerialName("survived") val survived: Int,
    @SerialName("timedOut") val timedOut: Int,
    @SerialName("gaps") val gaps: Int = 0,
    @SerialName("mutationsEvaluated") val mutationsEvaluated: Int = 0,
    @SerialName("confidenceIntervalLow") val confidenceIntervalLow: Double? = null,
    @SerialName("confidenceIntervalHigh") val confidenceIntervalHigh: Double? = null,
    @SerialName("testMethods") val testMethods: List<String>,
    @SerialName("testKillerMatrix") val testKillerMatrix: Map<String, List<String>>,
    @SerialName("mutations") val mutations: List<MutationResult>,
    @SerialName("executionGaps") val executionGaps: List<ExecutionGap> = emptyList(),
    @SerialName("redundantGroups") val redundantGroups: List<RedundantGroup> = emptyList(),
    @SerialName("schemaVersion") val schemaVersion: Int = 2,
    @SerialName("untestedMutations") val untestedMutations: Int = 0,
)
