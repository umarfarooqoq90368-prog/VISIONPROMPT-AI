package com.example.viewmodel

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.BuildConfig
import com.example.model.AnalysisResult
import com.example.model.AnalysisUiState
import com.example.model.PromptTargetPlatform
import com.example.model.SampleVideoPreset
import com.example.model.SceneDetail
import com.example.model.VideoMetadata
import com.example.service.VideoFrameExtractor
import com.example.service.VisionPromptAiService
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Main Studio Navigation Destinations as requested:
 * - Dashboard
 * - Upload Video
 * - Scene Analysis
 * - Generated Prompts
 * - Saved Projects
 * - History
 * - Settings
 */
enum class AppDestination(val title: String) {
    DASHBOARD("Dashboard"),
    UPLOAD_VIDEO("Upload Video"),
    SCENE_ANALYSIS("Scene Analysis"),
    GENERATED_PROMPTS("Generated Prompts"),
    SAVED_PROJECTS("Saved Projects"),
    HISTORY("History"),
    SETTINGS("Settings");

    companion object {
        // Compatibility aliases
        val EXPLORE: AppDestination get() = DASHBOARD
        val WORKSPACE: AppDestination get() = SCENE_ANALYSIS
        val PLAY: AppDestination get() = GENERATED_PROMPTS
        val STORE: AppDestination get() = UPLOAD_VIDEO
        val BOARD: AppDestination get() = SAVED_PROJECTS
        val STORYBOARD: AppDestination get() = SAVED_PROJECTS
        val CITATION: AppDestination get() = SETTINGS
        val LANDING: AppDestination get() = DASHBOARD
    }
}

class VisionPromptViewModel(application: Application) : AndroidViewModel(application) {

    companion object {
        const val PRODUCT_NAME = "Video to Scene Prompt Studio"
        const val PRODUCT_TAGLINE = "Turn Any Video Into Scene-by-Scene AI Prompts"
        const val HIGH_TOKEN_BUDGET = 8192
        const val ANALYSIS_TEMPERATURE = 0.35

        /**
         * Comprehensive Director of Photography & Google Flow Prompt System Instruction.
         */
        const val DEFAULT_GEMINI_SYSTEM_PROMPT = """You are "Video to Scene Prompt Studio", the premier AI engine converting any uploaded video into scene-by-scene, production-ready AI video prompts for Google Flow, Runway Gen-3, and Sora.

Workflow Pipeline:
UPLOAD VIDEO → AI ANALYSIS → AUTOMATIC SCENE DETECTION → SCENE-BY-SCENE ANALYSIS → GENERATE AI VIDEO PROMPTS → COPY/EDIT/SAVE/EXPORT → USE PROMPTS IN GOOGLE FLOW

### DIRECTIVES FOR EVERY SCENE:
For every meaningful detected scene segment across the timeline, you MUST identify and format:
1. Exact Timestamps: startTimestamp & endTimestamp down to tenths of a second (e.g. 00:00.0 to 00:06.0).
2. Characters: Named archetype, count, posture, orientation, emotional expression.
3. Character Appearance: Exact facial features, hairstyle, skin tone, clothing fabrics and color (Must maintain strict cross-scene character consistency if the same subject appears later).
4. Environment: Architectural setting, spatial geometry, background props, depth layers, indoors vs outdoor acoustics.
5. Main Action: Concrete bodily kinetics, velocity, gestures, physical interactions.
6. Objects: Notable props, vehicles, tech items, spatial anchors.
7. Camera Angle: High angle, low angle, eye level, bird's eye, Dutch roll angle.
8. Camera Movement: Granular pan rate, vertical tilt elevation, dolly velocity, 3-axis gimbal or handheld stabilization.
9. Lighting: Motivated key light, fill ratio, rim backlight, Kelvin color temperature (3200K warm vs 5600K daylight).
10. Mood: Tension, wonder, serenity, suspense, cinematic urgency.
11. Weather: Meteorological condition, precipitation, volumetric haze, atmospheric density.
12. Visual Style: 35mm anamorphic prime lens, aperture f/1.8, bokeh quality, cinematic film grain.
13. Color Palette: 3 to 4 dominant hex codes (e.g. ["#3B82F6", "#8B5CF6", "#06B6D4"]).
14. Atmosphere: Smoke, dust particles, reflections, lighting falloff.
15. Important Visual Details & Continuity: Continuity anchors that prevent AI morphing or flickering when generated in Google Flow.

### GOOGLE FLOW READY PROMPT:
Every scene must have a rich, self-contained prompt synthesizing:
[Subject + Characters + Environment + Action + Camera + Camera Movement + Lighting + Composition + Mood + Visual Style + Motion + Background + Atmosphere]

Return ONLY a valid JSON object matching the requested schema.
"""

        fun buildGranularUserPrompt(metadata: VideoMetadata, sceneCount: Int): String {
            return """
Analyze keyframes across '${metadata.title}' (Duration: ${metadata.durationFormatted}, ${metadata.resolutionText}).
Detect and deconstruct this video into $sceneCount consecutive chronological scenes.
Maintain strict character identity and visual style consistency across scenes.

Output a JSON object with this structure:
{
  "scenes": [
    {
      "sceneNumber": 1,
      "startTimestamp": "00:00.0",
      "endTimestamp": "00:06.0",
      "title": "Scene 01",
      "subjects": ["Cyber detective in trenchcoat"],
      "characters": "Male detective, late 30s, intense watchful gaze",
      "characterAppearance": "Charcoal weathered microfiber trenchcoat, glowing optic eyepiece, dark dampened hair",
      "environment": "Rain-slicked alleyway flanked by neon noodle stall facades and holographic billboards",
      "mainAction": "Walking briskly forward toward camera while scanning portable datapad",
      "objects": "Translucent holographic datapad, dripping fire escape ladders",
      "cameraAngle": "Low-angle medium tracking shot",
      "cameraMovement": "Smooth backward dolly at 1.2 m/s matching subject walking pace with subtle handheld micro-shake",
      "lighting": "Motivated cyan neon overhead signage with warm amber fill from food cart, 4800K split lighting",
      "mood": "Cinematic neo-noir suspense and anticipation",
      "weather": "Heavy misty drizzle, wet puddles reflecting saturated neon",
      "visualStyle": "Cinematic 35mm anamorphic widescreen, shallow depth of field, f/1.8 optical streak flares",
      "colorPaletteHexes": ["#06B6D4", "#8B5CF6", "#1E293B"],
      "atmosphere": "Dense volumetric steam rising from street grates, glistening raindrops",
      "importantVisualDetails": "Keep trenchcoat color and left glowing eyepiece identical in subsequent scenes",
      "continuityNotes": "Consistent cybernetic eyepiece on left eye, charcoal coat texture",
      "selfContainedScenePrompt": "Low-angle medium tracking shot of a 30s cyber detective in a charcoal weathered trenchcoat walking through a rain-drenched neon alleyway. Smooth backward dolly at 1.2 m/s. Wet asphalt reflecting vibrant cyan and violet holograms. Volumetric steam, 35mm anamorphic lens, f/1.8 bokeh, cinematic neo-noir atmosphere.",
      "sceneNegativePrompt": "blurry, unnatural motion, morphing coat color, extra limbs, cartoonish rendering"
    }
  ],
  "fullVideoChronologicalPrompt": "Chronological multi-scene sequence prompt for Google Flow video generation...",
  "masterPrompt": "Master sequence prompt across all scenes",
  "runwayGen3Prompt": "[Camera: Dolly In, Low Angle] Cyber detective walks through rain alleyway",
  "soraPrompt": "Cinematic photorealistic 4K sequence of cyber detective in neo-noir rain",
  "lumaDreamMachinePrompt": "Realistic physics fluid camera motion of detective in rainy street",
  "pikaPrompt": "Cyberpunk detective rain alleyway -camera dolly -motion 5",
  "negativePrompt": "blurry, morphing subjects, flickering lights, warped faces, artifacts",
  "cameraGuidance": "Maintain smooth Steadicam tracking and consistent 35mm anamorphic focal length",
  "lightingGuidance": "Maintain balanced cyan-violet split-lighting with high contrast shadows",
  "styleGuidance": "Realistic cinematic film grain, anamorphic flare, photorealistic textures",
  "characterConsistencyNotes": "Protagonist: cybernetic blue left eye, charcoal collar coat, wet swept hair",
  "cameraAndVisualConsistencyNotes": "Consistent 2.39:1 widescreen framing and cool color temperature",
  "transitionContinuityInstructions": "Match cut forward motion velocity between scene boundaries",
  "tags": ["Google Flow Ready", "Cyberpunk", "Cinematic", "Scene-by-Scene"]
}
Only output valid JSON.
""".trimIndent()
        }
    }

    private val frameExtractor = VideoFrameExtractor(application.applicationContext)
    private val aiService = VisionPromptAiService()

    private val _currentDestination = MutableStateFlow(AppDestination.DASHBOARD)
    val currentDestination: StateFlow<AppDestination> = _currentDestination.asStateFlow()

    private val _uiState = MutableStateFlow<AnalysisUiState>(AnalysisUiState.Idle)
    val uiState: StateFlow<AnalysisUiState> = _uiState.asStateFlow()

    private val _selectedMetadata = MutableStateFlow<VideoMetadata?>(null)
    val selectedMetadata: StateFlow<VideoMetadata?> = _selectedMetadata.asStateFlow()

    private val _currentResult = MutableStateFlow<AnalysisResult?>(null)
    val currentResult: StateFlow<AnalysisResult?> = _currentResult.asStateFlow()

    private val _activeTargetPlatform = MutableStateFlow(PromptTargetPlatform.GOOGLE_FLOW)
    val activeTargetPlatform: StateFlow<PromptTargetPlatform> = _activeTargetPlatform.asStateFlow()

    private val _activeSceneIndex = MutableStateFlow(0)
    val activeSceneIndex: StateFlow<Int> = _activeSceneIndex.asStateFlow()

    private val _savedProjects = MutableStateFlow<List<AnalysisResult>>(emptyList())
    val savedProjects: StateFlow<List<AnalysisResult>> = _savedProjects.asStateFlow()

    // History of all analyses performed
    private val _historyProjects = MutableStateFlow<List<AnalysisResult>>(emptyList())
    val historyProjects: StateFlow<List<AnalysisResult>> = _historyProjects.asStateFlow()

    val systemPrompt: String = DEFAULT_GEMINI_SYSTEM_PROMPT
    val tokenBudget: Int = HIGH_TOKEN_BUDGET

    private var analysisJob: Job? = null

    // Sample video presets showcasing real scene-by-scene analysis
    val samplePresets = listOf(
        SampleVideoPreset(
            id = "preset_cyberpunk",
            title = "Neo-Tokyo Alleyway Rain",
            durationText = "00:14.0",
            resolutionText = "1920x1080 (16:9)",
            tag = "Sci-Fi / Cinematic",
            description = "Multi-shot sequence: detective walks through alley, encounters contact at noodle stall, flees approaching security drone.",
            accentHex = "#06B6D4"
        ),
        SampleVideoPreset(
            id = "preset_highland",
            title = "Highland Castle Drone Odyssey",
            durationText = "00:18.0",
            resolutionText = "3840x2160 (4K)",
            tag = "Landscape / Aerial",
            description = "Three-scene aerial sequence over Scottish loch, ascending rugged crag, skimming ancient fortress battlements at dawn.",
            accentHex = "#8B5CF6"
        ),
        SampleVideoPreset(
            id = "preset_hypercar",
            title = "Monaco Coastal Drift Chase",
            durationText = "00:12.5",
            resolutionText = "2560x1440 (2K)",
            tag = "Action / Automotive",
            description = "Chasing supercar around coastal switchback hairpin, driver cockpit reaction, cinematic slow-motion exit into sunset.",
            accentHex = "#EC4899"
        ),
        SampleVideoPreset(
            id = "preset_abyssal",
            title = "Deep Mariana Bioluminescence",
            durationText = "00:10.0",
            resolutionText = "1920x1080 (16:9)",
            tag = "Macro / Creature",
            description = "Submersible camera spots pulsing translucent jelly organism, macro tentacle ripples, disappearing into deep abyss.",
            accentHex = "#3B82F6"
        )
    )

    init {
        loadInitialPresetDemo()
    }

    private fun loadInitialPresetDemo() {
        viewModelScope.launch {
            val preset = samplePresets[0]
            val durMs = 14000L
            val meta = VideoMetadata(
                title = preset.title,
                durationMs = durMs,
                width = 1920,
                height = 1080,
                fileSizeBytes = 36800000L,
                format = "MP4 (H.264)",
                frameRate = 24f
            )
            _selectedMetadata.value = meta

            val keyframes = listOf(
                Pair(1000L, frameExtractor.createSyntheticKeyframe(1, "Scene 01: Alley Entrance", 0xFF0B132B.toInt(), 0xFF1C2541.toInt())),
                Pair(4500L, frameExtractor.createSyntheticKeyframe(2, "Scene 02: Neon Market Stall", 0xFF1B1B3A.toInt(), 0xFF3D2645.toInt())),
                Pair(8500L, frameExtractor.createSyntheticKeyframe(3, "Scene 03: The Informant Pass", 0xFF0D1B2A.toInt(), 0xFF1B4965.toInt())),
                Pair(12500L, frameExtractor.createSyntheticKeyframe(4, "Scene 04: Drone Departure", 0xFF1C0A35.toInt(), 0xFF511845.toInt()))
            )
            val userPrompt = buildGranularUserPrompt(meta, keyframes.size)
            val result = aiService.analyzeVideo(
                metadata = meta,
                keyframes = keyframes,
                systemPrompt = systemPrompt,
                promptTemplate = userPrompt,
                maxOutputTokens = tokenBudget
            ) { _, _, _, _ -> }

            _currentResult.value = result
            _savedProjects.value = listOf(result)
            _historyProjects.value = listOf(result)
        }
    }

    fun navigateTo(destination: AppDestination) {
        _currentDestination.value = destination
    }

    fun setTargetPlatform(platform: PromptTargetPlatform) {
        _activeTargetPlatform.value = platform
    }

    fun setActiveSceneIndex(index: Int) {
        _activeSceneIndex.value = index
    }

    fun updateScenePrompt(sceneIndex: Int, newPrompt: String) {
        val curr = _currentResult.value ?: return
        val updatedScenes = curr.scenes.mapIndexed { idx, scene ->
            if (idx == sceneIndex) scene.copy(editedPrompt = newPrompt) else scene
        }
        val updatedResult = curr.copy(scenes = updatedScenes)
        _currentResult.value = updatedResult
        updateInSavedAndHistory(updatedResult)
    }

    fun regenerateScenePrompt(sceneIndex: Int) {
        val curr = _currentResult.value ?: return
        if (sceneIndex in curr.scenes.indices) {
            val scene = curr.scenes[sceneIndex]
            val regenerated = """Scene ${String.format("%02d", scene.sceneNumber)} [${scene.startTimestamp}-${scene.endTimestamp}]: ${scene.characters} in ${scene.environment}. ${scene.mainAction}. Camera: ${scene.cameraAngle}, ${scene.cameraMovement}. Lighting: ${scene.lighting}. Mood: ${scene.mood}. Atmosphere: ${scene.atmosphere}. Ultra-detailed 4K photorealistic Google Flow video generation prompt."""
            updateScenePrompt(sceneIndex, regenerated)
        }
    }

    fun saveCurrentProject() {
        val curr = _currentResult.value ?: return
        val list = _savedProjects.value.toMutableList()
        list.removeAll { it.id == curr.id || it.videoTitle == curr.videoTitle }
        list.add(0, curr)
        _savedProjects.value = list
    }

    fun deleteSavedProject(id: String) {
        _savedProjects.value = _savedProjects.value.filter { it.id != id }
    }

    fun deleteHistoryProject(id: String) {
        _historyProjects.value = _historyProjects.value.filter { it.id != id }
    }

    fun loadProject(result: AnalysisResult) {
        _currentResult.value = result
        _selectedMetadata.value = VideoMetadata(
            title = result.videoTitle,
            durationMs = 14000L,
            width = 1920,
            height = 1080
        )
        _uiState.value = AnalysisUiState.Success(result)
        _currentDestination.value = AppDestination.SCENE_ANALYSIS
    }

    private fun updateInSavedAndHistory(updated: AnalysisResult) {
        _savedProjects.value = _savedProjects.value.map { if (it.id == updated.id) updated else it }
        _historyProjects.value = _historyProjects.value.map { if (it.id == updated.id) updated else it }
    }

    fun analyzeVideoUri(uri: Uri) {
        analysisJob?.cancel()
        _currentDestination.value = AppDestination.SCENE_ANALYSIS

        analysisJob = viewModelScope.launch {
            try {
                // Stage 1: Upload
                _uiState.value = AnalysisUiState.Processing(
                    stepTitle = "Uploading Video File",
                    stepDetail = "Reading byte stream, validating MP4/MOV/WebM container integrity...",
                    progress = 0.10f,
                    currentStageIndex = 1
                )

                val meta = frameExtractor.extractMetadataFromUri(uri)
                _selectedMetadata.value = meta

                // Stage 2: Analyze Video
                _uiState.value = AnalysisUiState.Processing(
                    stepTitle = "Analyzing Video Structure",
                    stepDetail = "Parsing timeline, resolution (${meta.resolutionText}), duration (${meta.durationFormatted})...",
                    progress = 0.30f,
                    currentStageIndex = 2
                )

                val sampleCount = frameExtractor.calculateAdaptiveSampleCount(meta.durationMs, isGranular = true)

                // Stage 3: Detect Scenes
                _uiState.value = AnalysisUiState.Processing(
                    stepTitle = "Detecting Scenes & Shot Boundaries",
                    stepDetail = "Locating $sampleCount cut boundaries with temporal timestamps [00:00 - ${meta.durationFormatted}]...",
                    progress = 0.50f,
                    currentStageIndex = 3
                )

                val keyframes = frameExtractor.extractKeyframes(uri, count = sampleCount)

                // Stage 4: Analyze Scenes
                _uiState.value = AnalysisUiState.Processing(
                    stepTitle = "Deconstructing Scene Attributes",
                    stepDetail = "Identifying characters, lighting, camera kinematics, and tracking character consistency...",
                    progress = 0.70f,
                    currentStageIndex = 4
                )

                val userPrompt = buildGranularUserPrompt(meta, sampleCount)

                // Stage 5: Generate Prompts
                val result = aiService.analyzeVideo(
                    metadata = meta,
                    keyframes = keyframes,
                    systemPrompt = systemPrompt,
                    promptTemplate = userPrompt,
                    maxOutputTokens = tokenBudget
                ) { stepTitle, stepDetail, progress, _ ->
                    _uiState.value = AnalysisUiState.Processing(
                        stepTitle = stepTitle,
                        stepDetail = stepDetail,
                        progress = progress,
                        currentStageIndex = 5
                    )
                }

                _currentResult.value = result
                _uiState.value = AnalysisUiState.Success(result)
                saveCurrentToHistory(result)
            } catch (e: Exception) {
                _uiState.value = AnalysisUiState.Error("Video analysis failed: ${e.message ?: "Unknown error"}")
            }
        }
    }

    fun analyzePreset(preset: SampleVideoPreset) {
        analysisJob?.cancel()
        _currentDestination.value = AppDestination.SCENE_ANALYSIS

        analysisJob = viewModelScope.launch {
            try {
                val durMs = when (preset.id) {
                    "preset_cyberpunk" -> 14000L
                    "preset_highland" -> 18000L
                    "preset_hypercar" -> 12500L
                    else -> 10000L
                }

                val meta = VideoMetadata(
                    title = preset.title,
                    durationMs = durMs,
                    width = if (preset.id == "preset_highland") 3840 else 1920,
                    height = if (preset.id == "preset_highland") 2160 else 1080,
                    fileSizeBytes = 36800000L,
                    format = "MP4 (H.264 / ProRes)",
                    frameRate = 24f
                )
                _selectedMetadata.value = meta

                val sceneCount = frameExtractor.calculateAdaptiveSampleCount(durMs, isGranular = true)
                val keyframes = mutableListOf<Pair<Long, Bitmap>>()
                for (s in 1..sceneCount) {
                    val timeMs = ((s - 0.5f) / sceneCount * durMs).toLong()
                    val colA = when (s % 4) {
                        1 -> 0xFF0B132B.toInt()
                        2 -> 0xFF1B1B3A.toInt()
                        3 -> 0xFF0D1B2A.toInt()
                        else -> 0xFF1C0A35.toInt()
                    }
                    val colB = when (s % 4) {
                        1 -> 0xFF1C2541.toInt()
                        2 -> 0xFF3D2645.toInt()
                        3 -> 0xFF1B4965.toInt()
                        else -> 0xFF511845.toInt()
                    }
                    keyframes.add(Pair(timeMs, frameExtractor.createSyntheticKeyframe(s, "${preset.title} Scene 0$s", colA, colB)))
                }

                val userPrompt = buildGranularUserPrompt(meta, sceneCount)

                val result = aiService.analyzeVideo(
                    metadata = meta,
                    keyframes = keyframes,
                    systemPrompt = systemPrompt,
                    promptTemplate = userPrompt,
                    maxOutputTokens = tokenBudget
                ) { stepTitle, stepDetail, progress, stage ->
                    _uiState.value = AnalysisUiState.Processing(
                        stepTitle = stepTitle,
                        stepDetail = stepDetail,
                        progress = progress,
                        currentStageIndex = stage
                    )
                }

                _currentResult.value = result
                _uiState.value = AnalysisUiState.Success(result)
                saveCurrentToHistory(result)
            } catch (e: Exception) {
                _uiState.value = AnalysisUiState.Error("Preset analysis error: ${e.localizedMessage}")
            }
        }
    }

    private fun saveCurrentToHistory(result: AnalysisResult) {
        val list = _historyProjects.value.toMutableList()
        list.removeAll { it.id == result.id || it.videoTitle == result.videoTitle }
        list.add(0, result)
        _historyProjects.value = list

        val savedList = _savedProjects.value.toMutableList()
        if (savedList.none { it.id == result.id }) {
            savedList.add(0, result)
            _savedProjects.value = savedList
        }
    }

    fun cancelAnalysis() {
        analysisJob?.cancel()
        _uiState.value = AnalysisUiState.Idle
    }

    fun isGeminiKeyConfigured(): Boolean {
        val key = BuildConfig.GEMINI_API_KEY.trim()
        return key.isNotEmpty() && key != "MY_GEMINI_API_KEY"
    }

    // Export formats helper
    fun buildAllPromptsAsTxt(result: AnalysisResult): String {
        val sb = StringBuilder()
        sb.appendLine("====================================================")
        sb.appendLine("${PRODUCT_NAME.uppercase()} - EXPORT")
        sb.appendLine("Video: ${result.videoTitle}")
        sb.appendLine("Duration: ${result.videoDurationFormatted} | Scenes: ${result.scenes.size}")
        sb.appendLine("Engine: ${result.engineUsed} | Analyzed: ${result.analyzedAtFormatted}")
        sb.appendLine("Target: Google Flow Scene-by-Scene Ready")
        sb.appendLine("====================================================\n")

        sb.appendLine("--- CHARACTER & STYLE CONSISTENCY NOTES ---")
        sb.appendLine(result.characterConsistencyNotes)
        sb.appendLine(result.cameraAndVisualConsistencyNotes)
        sb.appendLine("\n--- SCENE-BY-SCENE GOOGLE FLOW PROMPTS ---")

        result.scenes.forEach { scene ->
            sb.appendLine("SCENE ${String.format("%02d", scene.sceneNumber)} [${scene.startTimestamp} - ${scene.endTimestamp}]: ${scene.title}")
            sb.appendLine("Characters: ${scene.characters}")
            sb.appendLine("Appearance: ${scene.characterAppearance}")
            sb.appendLine("Environment: ${scene.environment}")
            sb.appendLine("Action: ${scene.mainAction}")
            sb.appendLine("Camera: ${scene.cameraAngle} | Motion: ${scene.cameraMovement}")
            sb.appendLine("Lighting: ${scene.lighting}")
            sb.appendLine("Mood & Atmosphere: ${scene.mood} | ${scene.atmosphere}")
            sb.appendLine("PROMPT:")
            sb.appendLine(scene.activePrompt)
            sb.appendLine("NEGATIVE PROMPT: ${scene.sceneNegativePrompt}")
            sb.appendLine("----------------------------------------------------\n")
        }

        sb.appendLine("--- FULL VIDEO CHRONOLOGICAL PROMPT ---")
        sb.appendLine(result.fullVideoChronologicalPrompt)
        return sb.toString()
    }

    fun buildAllPromptsAsJson(result: AnalysisResult): String {
        val scenesJson = result.scenes.joinToString(",\n") { scene ->
            """    {
      "sceneNumber": ${scene.sceneNumber},
      "startTimestamp": "${scene.startTimestamp}",
      "endTimestamp": "${scene.endTimestamp}",
      "title": "${escapeJson(scene.title)}",
      "characters": "${escapeJson(scene.characters)}",
      "characterAppearance": "${escapeJson(scene.characterAppearance)}",
      "environment": "${escapeJson(scene.environment)}",
      "mainAction": "${escapeJson(scene.mainAction)}",
      "camera": "${escapeJson(scene.cameraAngle)}",
      "cameraMovement": "${escapeJson(scene.cameraMovement)}",
      "lighting": "${escapeJson(scene.lighting)}",
      "mood": "${escapeJson(scene.mood)}",
      "googleFlowPrompt": "${escapeJson(scene.activePrompt)}",
      "negativePrompt": "${escapeJson(scene.sceneNegativePrompt)}"
    }"""
        }

        return """{
  "product": "${PRODUCT_NAME}",
  "videoTitle": "${escapeJson(result.videoTitle)}",
  "duration": "${result.videoDurationFormatted}",
  "totalScenes": ${result.scenes.size},
  "characterConsistency": "${escapeJson(result.characterConsistencyNotes)}",
  "scenes": [
$scenesJson
  ]
}"""
    }

    private fun escapeJson(str: String): String {
        return str.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ")
    }
}
