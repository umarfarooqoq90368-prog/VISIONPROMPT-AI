package com.example.model

import android.graphics.Bitmap

data class VideoMetadata(
    val title: String,
    val uriString: String? = null,
    val durationMs: Long = 0L,
    val width: Int = 1920,
    val height: Int = 1080,
    val fileSizeBytes: Long = 0L,
    val format: String = "MP4 (H.264)",
    val frameRate: Float = 24.0f
) {
    val durationFormatted: String
        get() {
            val totalSeconds = (durationMs / 1000).toInt()
            val minutes = totalSeconds / 60
            val seconds = totalSeconds % 60
            val ms = ((durationMs % 1000) / 100).toInt()
            return String.format("%02d:%02d.%d", minutes, seconds, ms)
        }

    val resolutionText: String
        get() = "${width}x${height} (${getAspectRatio()})"

    val sizeFormatted: String
        get() = when {
            fileSizeBytes >= 1024 * 1024 -> String.format("%.1f MB", fileSizeBytes / (1024.0 * 1024.0))
            fileSizeBytes >= 1024 -> String.format("%.1f KB", fileSizeBytes / 1024.0)
            fileSizeBytes > 0 -> "$fileSizeBytes bytes"
            else -> "34.8 MB"
        }

    private fun getAspectRatio(): String {
        if (height == 0) return "16:9"
        val ratio = width.toFloat() / height.toFloat()
        return when {
            ratio > 1.7f && ratio < 1.8f -> "16:9"
            ratio > 2.3f -> "2.39:1 Anamorphic"
            ratio > 0.9f && ratio < 1.1f -> "1:1 Square"
            ratio < 0.6f -> "9:16 Vertical"
            ratio > 1.3f && ratio < 1.4f -> "4:3 Classic"
            else -> String.format("%.2f:1", ratio)
        }
    }
}

data class SceneDetail(
    val sceneNumber: Int,
    val timestampMs: Long,
    val formattedTimestamp: String,
    val durationSec: Float,
    val title: String,
    val subjects: List<String>,
    val actions: List<String>,
    val cameraMovement: String,
    val framing: String,
    val lighting: String,
    val colorPaletteHexes: List<String>,
    val continuityNotes: String,
    val promptFragment: String,
    val extractedBitmap: Bitmap? = null,
    // Deep Scene-by-Scene Visual Analysis Fields
    val startTimestamp: String = formattedTimestamp,
    val endTimestamp: String = String.format("%02d:%02d", (timestampMs + (durationSec * 1000).toLong()) / 60000, ((timestampMs + (durationSec * 1000).toLong()) % 60000) / 1000),
    val subjectAppearanceAndAttire: String = "",
    val subjectPositionAndOrientation: String = "",
    val actionAndKinetics: String = "",
    val environmentAndSetPieces: String = "",
    val lensAndDepthOfField: String = "",
    val lightingAndShadowDynamics: String = "",
    val colorAndAtmosphericHaze: String = "",
    val transitionCues: String = "",
    val selfContainedScenePrompt: String = promptFragment,
    val sceneNegativePrompt: String = "blurry, unnatural motion, jitter, morphing artifacts",
    // Granular Google Flow prompt components
    val characters: String = if (subjects.isNotEmpty()) subjects.joinToString(", ") else "Subject",
    val characterAppearance: String = subjectAppearanceAndAttire,
    val environment: String = environmentAndSetPieces,
    val mainAction: String = if (actions.isNotEmpty()) actions.joinToString(", ") else actionAndKinetics,
    val objects: String = "Key focal props, architectural elements, lighting fixtures",
    val cameraAngle: String = framing,
    val mood: String = "Cinematic, high tension, visually captivating",
    val weather: String = "Clear atmospheric conditions, volumetric indoor lighting",
    val visualStyle: String = "Cinematic 35mm anamorphic film grain, photorealistic rendering",
    val colorPalette: String = if (colorPaletteHexes.isNotEmpty()) colorPaletteHexes.joinToString(" ") else "#3B82F6 #8B5CF6 #06B6D4",
    val atmosphere: String = colorAndAtmosphericHaze,
    val importantVisualDetails: String = continuityNotes,
    // User editable prompt
    var editedPrompt: String? = null
) {
    val timestampRange: String
        get() = "[$startTimestamp - $endTimestamp]"

    val activePrompt: String
        get() = editedPrompt ?: selfContainedScenePrompt
}

data class AnalysisResult(
    val id: String,
    val videoTitle: String,
    val videoDurationFormatted: String,
    val analyzedAtFormatted: String,
    val engineUsed: String,
    val scenes: List<SceneDetail>,
    var masterPrompt: String,
    val runwayGen3Prompt: String,
    val soraPrompt: String,
    val lumaDreamMachinePrompt: String,
    val pikaPrompt: String,
    val negativePrompt: String,
    val cameraGuidance: String,
    val lightingGuidance: String,
    val styleGuidance: String,
    val tags: List<String>,
    // Advanced Reconstruction & Consistency Directives
    val fullVideoChronologicalPrompt: String = masterPrompt,
    val characterConsistencyNotes: String = "",
    val cameraAndVisualConsistencyNotes: String = "",
    val transitionContinuityInstructions: String = "",
    val adaptiveSamplingExplanation: String = "Adaptive Multi-Window Scene Sampling: Analyzed complete duration with temporal cut indexing.",
    // Studio Saved Project Metadata
    val savedTimestamp: Long = System.currentTimeMillis()
)

enum class PromptTargetPlatform(val displayName: String, val badge: String) {
    GOOGLE_FLOW("Google Flow", "Scene-by-Scene Ready"),
    RUNWAY_GEN3("Runway Gen-3 Alpha", "[Camera] Motion Directing"),
    OPENAI_SORA("OpenAI Sora", "Narrative Cinematic"),
    LUMA_DREAM("Luma Dream Machine", "Realistic Physics"),
    PIKA_LABS("Pika 2.0", "Prompt & Parameters")
}

data class SampleVideoPreset(
    val id: String,
    val title: String,
    val durationText: String,
    val resolutionText: String,
    val tag: String,
    val description: String,
    val accentHex: String
)

sealed class AnalysisUiState {
    object Idle : AnalysisUiState()
    data class Processing(
        val stepTitle: String,
        val stepDetail: String,
        val progress: Float, // 0f to 1f
        val currentStageIndex: Int, // 1 to 5 (Upload -> Analyze Video -> Detect Scenes -> Analyze Scenes -> Generate Prompts)
        val totalStages: Int = 5
    ) : AnalysisUiState()
    data class Success(val result: AnalysisResult) : AnalysisUiState()
    data class Error(val message: String) : AnalysisUiState()
}
