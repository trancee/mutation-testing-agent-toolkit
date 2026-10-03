package ch.trancee.mutation

import kotlinx.serialization.json.Json

/**
 * JSON serialization for [MutationResults].
 *
 * Uses kotlinx.serialization's default pretty-print (4-space indentation) to match
 * the current string-template output format. The `encodeDefaults = true` flag
 * ensures that default-valued fields (killedByTest = null, killedByTests = [])
 * are still emitted, matching the backward-compatible schema.
 */
object MutationResultsSerializer {

    private val json = Json {
        prettyPrint = true
        encodeDefaults = true
        isLenient = true
    }

    /**
     * Serializes [MutationResults] to a JSON string matching the
     * `mutation-results.json` schema consumed by test-auditor.
     */
    fun toJson(results: MutationResults): String = json.encodeToString(
        MutationResults.serializer(),
        results,
    )
}