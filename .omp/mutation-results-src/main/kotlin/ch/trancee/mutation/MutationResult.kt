package ch.trancee.mutation

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * The result of a single mutation analysis.
 *
 * Each mutation is serialized to a flat JSON object with all fields present
 * (killedByTest is null and killedByTests is empty for Survived/TimedOut).
 * This matches the backward-compatible mutation-results.json schema.
 */
@Serializable
data class MutationResult(
    @SerialName("sourceLocation") val sourceLocation: String,
    @SerialName("originalOperator") val originalOperator: String,
    @SerialName("variantOperator") val variantOperator: String,
    @SerialName("result") val result: MutationResultType,
    @SerialName("killedByTest") val killedByTest: String? = null,
    @SerialName("killedByTests") val killedByTests: List<String> = emptyList(),
    @SerialName("testClass") val testClass: String? = null,
)

/**
 * The outcome of a mutation run.
 */
enum class MutationResultType {
    @SerialName("Killed") Killed,
    @SerialName("Survived") Survived,
    @SerialName("TimedOut") TimedOut,
}
