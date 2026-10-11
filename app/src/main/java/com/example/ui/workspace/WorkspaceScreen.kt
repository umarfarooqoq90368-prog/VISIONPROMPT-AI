package com.example.ui.workspace

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Timeline
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.AnalysisResult
import com.example.model.AnalysisUiState
import com.example.model.PromptTargetPlatform
import com.example.model.SampleVideoPreset
import com.example.model.SceneDetail
import com.example.model.VideoMetadata
import com.example.ui.theme.DarkBgMain
import com.example.ui.theme.DarkBgSecondary
import com.example.ui.theme.DarkCardBg
import com.example.ui.theme.DarkCardBorder
import com.example.ui.theme.DarkSurfaceElevated
import com.example.ui.theme.ElectricViolet
import com.example.ui.theme.NeonCyan
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.ui.theme.TextTertiary

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun WorkspaceScreen(
    uiState: AnalysisUiState,
    metadata: VideoMetadata?,
    currentResult: AnalysisResult?,
    activePlatform: PromptTargetPlatform,
    activeSceneIndex: Int,
    samplePresets: List<SampleVideoPreset>,
    onSelectPlatform: (PromptTargetPlatform) -> Unit,
    onSelectSceneIndex: (Int) -> Unit,
    onUpdatePrompt: (String) -> Unit,
    onAnalyzeUri: (Uri) -> Unit,
    onAnalyzePreset: (SampleVideoPreset) -> Unit,
    onCancelAnalysis: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scrollState = rememberScrollState()

    val videoPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri != null) {
            onAnalyzeUri(uri)
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(DarkBgMain)
            .verticalScroll(scrollState)
            .padding(16.dp)
            .testTag("workspace_screen_container")
    ) {
        // Workspace Top Title
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Text(
                    text = "DEEP VIDEO ANALYSIS WORKSPACE",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = NeonCyan,
                    letterSpacing = 1.2.sp
                )
                Text(
                    text = metadata?.title ?: "Multi-Shot Directorial Deconstruction",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Black,
                    color = TextPrimary,
                    maxLines = 1
                )
            }

            Button(
                onClick = {
                    videoPicker.launch(
                        PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly)
                    )
                },
                colors = ButtonDefaults.buttonColors(containerColor = DarkCardBg),
                border = androidx.compose.foundation.BorderStroke(1.dp, Brush.linearGradient(listOf(DarkCardBorder, NeonCyan))),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.testTag("workspace_pick_video_button")
            ) {
                Icon(
                    imageVector = Icons.Default.CloudUpload,
                    contentDescription = null,
                    tint = NeonCyan,
                    modifier = Modifier.size(15.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "Upload Video",
                    fontSize = 12.sp,
                    color = TextPrimary
                )
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        when (uiState) {
            is AnalysisUiState.Idle -> {
                WorkspaceIdleCard(
                    onPickVideo = {
                        videoPicker.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly)
                        )
                    },
                    samplePresets = samplePresets,
                    onSelectPreset = onAnalyzePreset
                )
            }

            is AnalysisUiState.Processing -> {
                WorkspaceProcessingCard(
                    state = uiState,
                    metadata = metadata,
                    onCancel = onCancelAnalysis
                )
            }

            is AnalysisUiState.Error -> {
                WorkspaceErrorCard(
                    errorMessage = uiState.message,
                    onRetry = {
                        videoPicker.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly)
                        )
                    }
                )
            }

            is AnalysisUiState.Success -> {
                val result = uiState.result
                val activeScene = result.scenes.getOrNull(activeSceneIndex) ?: result.scenes.firstOrNull()

                // Metadata Bar
                metadata?.let { meta ->
                    VideoMetadataBar(meta = meta, engineUsed = result.engineUsed, samplingInfo = result.adaptiveSamplingExplanation)
                    Spacer(modifier = Modifier.height(14.dp))
                }

                // 1. Scene Timeline & Keyframe Carousel
                SceneKeyframesTimeline(
                    scenes = result.scenes,
                    selectedIndex = activeSceneIndex,
                    onSelectScene = onSelectSceneIndex
                )

                Spacer(modifier = Modifier.height(14.dp))

                // 2. Active Scene Deep Inspector Card
                activeScene?.let { scene ->
                    DeepSceneInspectorCard(
                        scene = scene,
                        onCopy = { text, label -> copyToClipboard(context, text, "$label copied") }
                    )
                    Spacer(modifier = Modifier.height(14.dp))
                }

                // 3. Chronological Full-Video Prompt & Multi-Platform Syntax
                GeneratedPromptsCard(
                    result = result,
                    activePlatform = activePlatform,
                    onSelectPlatform = onSelectPlatform,
                    onUpdatePrompt = onUpdatePrompt,
                    onCopy = { text, label ->
                        copyToClipboard(context, text, "$label copied to clipboard")
                    }
                )

                Spacer(modifier = Modifier.height(14.dp))

                // 4. Character, Visual Style & Transition Consistency Notes
                ConsistencyDirectivesCard(result = result)

                Spacer(modifier = Modifier.height(14.dp))

                // 5. Export Bar
                WorkspaceExportBar(
                    result = result,
                    metadata = metadata,
                    context = context
                )
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun WorkspaceIdleCard(
    onPickVideo: () -> Unit,
    samplePresets: List<SampleVideoPreset>,
    onSelectPreset: (SampleVideoPreset) -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .border(1.dp, DarkCardBorder, RoundedCornerShape(16.dp))
            .testTag("workspace_idle_card"),
        colors = CardDefaults.cardColors(containerColor = DarkCardBg)
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier
                    .size(64.dp)
                    .clip(CircleShape)
                    .background(DarkSurfaceElevated)
                    .border(1.dp, NeonCyan.copy(alpha = 0.5f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Videocam,
                    contentDescription = null,
                    tint = NeonCyan,
                    modifier = Modifier.size(32.dp)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "Select a Video for Deep Deconstruction",
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "Extracts every shot, camera angle, subject kinematics, lighting setup, and generates production-ready prompts.",
                fontSize = 13.sp,
                color = TextSecondary,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                lineHeight = 19.sp
            )

            Spacer(modifier = Modifier.height(20.dp))

            Button(
                onClick = onPickVideo,
                colors = ButtonDefaults.buttonColors(containerColor = NeonCyan),
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier.fillMaxWidth().height(48.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.CloudUpload,
                    contentDescription = null,
                    tint = Color(0xFF070A12)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Select Video File",
                    color = Color(0xFF070A12),
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
            }

            Spacer(modifier = Modifier.height(24.dp))
            HorizontalDivider(color = DarkCardBorder)
            Spacer(modifier = Modifier.height(18.dp))

            Text(
                text = "Or analyze instantly with curated cinematic clips:",
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color = TextSecondary,
                modifier = Modifier.align(Alignment.Start)
            )

            Spacer(modifier = Modifier.height(10.dp))

            FlowRow(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                samplePresets.forEach { preset ->
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(DarkSurfaceElevated)
                            .border(1.dp, DarkCardBorder, RoundedCornerShape(8.dp))
                            .clickable { onSelectPreset(preset) }
                            .padding(horizontal = 12.dp, vertical = 8.dp)
                    ) {
                        Column {
                            Text(
                                text = preset.title,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                            Text(
                                text = "${preset.tag} • ${preset.durationText}",
                                fontSize = 10.sp,
                                color = NeonCyan
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun WorkspaceProcessingCard(
    state: AnalysisUiState.Processing,
    metadata: VideoMetadata?,
    onCancel: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .border(1.5.dp, NeonCyan.copy(alpha = 0.5f), RoundedCornerShape(16.dp))
            .testTag("workspace_processing_card"),
        colors = CardDefaults.cardColors(containerColor = DarkCardBg)
    ) {
        Column(
            modifier = Modifier.padding(22.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(NeonCyan.copy(alpha = 0.15f))
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = "STAGE ${state.currentStageIndex} OF ${state.totalStages}",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = NeonCyan,
                        letterSpacing = 1.sp
                    )
                }

                IconButton(onClick = onCancel, modifier = Modifier.size(28.dp)) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "Cancel",
                        tint = TextSecondary,
                        modifier = Modifier.size(18.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            CircularProgressIndicator(
                progress = { state.progress },
                color = NeonCyan,
                strokeWidth = 4.dp,
                modifier = Modifier.size(64.dp)
            )

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = state.stepTitle,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = state.stepDetail,
                fontSize = 12.sp,
                color = TextSecondary,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                lineHeight = 17.sp
            )

            Spacer(modifier = Modifier.height(16.dp))

            LinearProgressIndicator(
                progress = { state.progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = NeonCyan,
                trackColor = DarkSurfaceElevated
            )

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "${(state.progress * 100).toInt()}% Complete",
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    color = NeonCyan
                )

                Text(
                    text = metadata?.resolutionText ?: "Analyzing video buffer...",
                    fontSize = 11.sp,
                    color = TextTertiary
                )
            }
        }
    }
}

@Composable
private fun WorkspaceErrorCard(
    errorMessage: String,
    onRetry: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .border(1.dp, Color(0xFFF43F5E), RoundedCornerShape(16.dp)),
        colors = CardDefaults.cardColors(containerColor = DarkCardBg)
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "Analysis Interrupted",
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFF43F5E)
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = errorMessage,
                fontSize = 13.sp,
                color = TextSecondary,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = onRetry,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFF43F5E))
            ) {
                Icon(imageVector = Icons.Default.Refresh, contentDescription = null)
                Spacer(modifier = Modifier.width(6.dp))
                Text("Retry Analysis")
            }
        }
    }
}

@Composable
private fun VideoMetadataBar(meta: VideoMetadata, engineUsed: String, samplingInfo: String) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .border(1.dp, DarkCardBorder, RoundedCornerShape(12.dp)),
        colors = CardDefaults.cardColors(containerColor = DarkCardBg)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(34.dp)
                            .clip(RoundedCornerShape(8.dp))
                            .background(DarkSurfaceElevated),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Movie,
                            contentDescription = null,
                            tint = NeonCyan,
                            modifier = Modifier.size(18.dp)
                        )
                    }

                    Spacer(modifier = Modifier.width(10.dp))

                    Column {
                        Text(
                            text = meta.title,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary,
                            maxLines = 1
                        )
                        Text(
                            text = "${meta.resolutionText} • ${meta.durationFormatted} • ${meta.format}",
                            fontSize = 11.sp,
                            color = TextSecondary
                        )
                    }
                }

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(ElectricViolet.copy(alpha = 0.2f))
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = engineUsed,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = NeonCyan
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = samplingInfo,
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                color = TextTertiary
            )
        }
    }
}

@Composable
private fun SceneKeyframesTimeline(
    scenes: List<SceneDetail>,
    selectedIndex: Int,
    onSelectScene: (Int) -> Unit
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = "SCENE BREAKDOWN & TIMELINE (${scenes.size} SHOTS)",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = NeonCyan,
                letterSpacing = 1.sp
            )

            Text(
                text = "Tap to inspect shot",
                fontSize = 11.sp,
                color = TextTertiary
            )
        }

        Spacer(modifier = Modifier.height(10.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            scenes.forEachIndexed { index, scene ->
                val isSelected = index == selectedIndex
                val borderCol = if (isSelected) NeonCyan else DarkCardBorder

                Card(
                    modifier = Modifier
                        .width(170.dp)
                        .clip(RoundedCornerShape(10.dp))
                        .border(if (isSelected) 2.dp else 1.dp, borderCol, RoundedCornerShape(10.dp))
                        .clickable { onSelectScene(index) }
                        .testTag("scene_card_$index"),
                    colors = CardDefaults.cardColors(
                        containerColor = if (isSelected) DarkSurfaceElevated else DarkCardBg
                    )
                ) {
                    Column {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(95.dp)
                                .background(Color(0xFF0B0F19)),
                            contentAlignment = Alignment.Center
                        ) {
                            if (scene.extractedBitmap != null) {
                                Image(
                                    bitmap = scene.extractedBitmap.asImageBitmap(),
                                    contentDescription = "Scene ${scene.sceneNumber}",
                                    modifier = Modifier.fillMaxSize()
                                )
                            } else {
                                Icon(
                                    imageVector = Icons.Default.Movie,
                                    contentDescription = null,
                                    tint = DarkCardBorder,
                                    modifier = Modifier.size(32.dp)
                                )
                            }

                            // Timecode range pill
                            Box(
                                modifier = Modifier
                                    .align(Alignment.BottomStart)
                                    .padding(6.dp)
                                    .clip(RoundedCornerShape(4.dp))
                                    .background(Color(0xDD000000))
                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                            ) {
                                Text(
                                    text = scene.timestampRange,
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = NeonCyan
                                )
                            }

                            Box(
                                modifier = Modifier
                                    .align(Alignment.TopEnd)
                                    .padding(6.dp)
                                    .clip(RoundedCornerShape(4.dp))
                                    .background(if (isSelected) NeonCyan else DarkCardBg)
                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                            ) {
                                Text(
                                    text = "Shot 0${scene.sceneNumber}",
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isSelected) Color(0xFF070A12) else TextPrimary
                                )
                            }
                        }

                        Column(modifier = Modifier.padding(10.dp)) {
                            Text(
                                text = scene.title,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary,
                                maxLines = 1
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = scene.cameraMovement,
                                fontSize = 10.sp,
                                color = ElectricViolet,
                                maxLines = 1
                            )
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DeepSceneInspectorCard(
    scene: SceneDetail,
    onCopy: (String, String) -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(1.dp, NeonCyan.copy(alpha = 0.5f), RoundedCornerShape(14.dp))
            .testTag("scene_inspector_card"),
        colors = CardDefaults.cardColors(containerColor = DarkCardBg)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header: Shot #, Title, Timestamp range
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(6.dp))
                            .background(NeonCyan.copy(alpha = 0.2f))
                            .padding(horizontal = 8.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = "SHOT 0${scene.sceneNumber}",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = NeonCyan
                        )
                    }

                    Spacer(modifier = Modifier.width(8.dp))

                    Text(
                        text = scene.title,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                }

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(4.dp))
                        .background(DarkSurfaceElevated)
                        .padding(horizontal = 6.dp, vertical = 3.dp)
                ) {
                    Text(
                        text = "${scene.timestampRange} (${scene.durationSec}s)",
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        color = NeonCyan
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // 1. Production-Ready Self-Contained Scene Prompt
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(10.dp))
                    .background(DarkSurfaceElevated)
                    .border(1.dp, DarkCardBorder, RoundedCornerShape(10.dp))
                    .padding(12.dp)
            ) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.AutoAwesome,
                                contentDescription = null,
                                tint = NeonCyan,
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "DETAILED PRODUCTION PROMPT (SHOT 0${scene.sceneNumber}):",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = NeonCyan
                            )
                        }

                        Text(
                            text = "Copy",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = ElectricViolet,
                            modifier = Modifier.clickable {
                                onCopy(scene.selfContainedScenePrompt, "Shot 0${scene.sceneNumber} prompt")
                            }
                        )
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = scene.selfContainedScenePrompt,
                        fontSize = 12.sp,
                        fontFamily = FontFamily.Monospace,
                        color = TextPrimary,
                        lineHeight = 18.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // 2. Camera Kinematics & Lens Optics Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                DetailBox(
                    title = "Camera Kinematics",
                    value = "${scene.cameraMovement}\n${scene.framing}",
                    icon = Icons.Default.CameraAlt,
                    accentColor = NeonCyan,
                    modifier = Modifier.weight(1f)
                )

                DetailBox(
                    title = "Lens Optics & Focus",
                    value = scene.lensAndDepthOfField.ifEmpty { "35mm anamorphic, shallow depth of field, subtle barrel distortion" },
                    icon = Icons.Default.Tune,
                    accentColor = ElectricViolet,
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // 3. Subjects, Attire & Spatial Kinetics
            DetailBox(
                title = "Subjects, Attire & Movement Kinetics",
                value = "${scene.subjectAppearanceAndAttire.ifEmpty { scene.subjects.joinToString(", ") }}\nOrientation & Action: ${scene.actionAndKinetics.ifEmpty { scene.actions.joinToString(", ") }}",
                icon = Icons.Default.Person,
                accentColor = Color(0xFFF43F5E),
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(10.dp))

            // 4. Environment, Background Architecture & Lighting
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                DetailBox(
                    title = "Environment & Set Architecture",
                    value = scene.environmentAndSetPieces.ifEmpty { "High-detail set with atmospheric layers" },
                    icon = Icons.Default.Visibility,
                    accentColor = Color(0xFF10B981),
                    modifier = Modifier.weight(1f)
                )

                DetailBox(
                    title = "Lighting & Shadow Dynamics",
                    value = scene.lightingAndShadowDynamics.ifEmpty { scene.lighting },
                    icon = Icons.Default.Lightbulb,
                    accentColor = Color(0xFFF59E0B),
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // 5. Extracted Color Palette
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Palette,
                    contentDescription = null,
                    tint = NeonCyan,
                    modifier = Modifier.size(13.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "Color Palette & Atmosphere:",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TextSecondary
                )
            }
            Spacer(modifier = Modifier.height(6.dp))
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                scene.colorPaletteHexes.forEach { hex ->
                    val color = parseHexColor(hex)
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier
                            .clip(RoundedCornerShape(6.dp))
                            .background(DarkSurfaceElevated)
                            .border(0.5.dp, DarkCardBorder, RoundedCornerShape(6.dp))
                            .padding(horizontal = 6.dp, vertical = 3.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(13.dp)
                                .clip(CircleShape)
                                .background(color)
                        )
                        Spacer(modifier = Modifier.width(5.dp))
                        Text(
                            text = hex,
                            fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace,
                            color = TextSecondary
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // 6. Continuity & Transition Notes
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(DarkSurfaceElevated)
                    .padding(10.dp)
            ) {
                Column {
                    Text(
                        text = "Must-Preserve Continuity Details:",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = ElectricViolet
                    )
                    Spacer(modifier = Modifier.height(3.dp))
                    Text(
                        text = "${scene.continuityNotes}\nTransition: ${scene.transitionCues.ifEmpty { "Cut on subject action" }}",
                        fontSize = 11.sp,
                        color = TextSecondary,
                        lineHeight = 16.sp
                    )
                }
            }
        }
    }
}

@Composable
private fun DetailBox(
    title: String,
    value: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    accentColor: Color,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(DarkSurfaceElevated)
            .border(1.dp, DarkCardBorder, RoundedCornerShape(8.dp))
            .padding(10.dp)
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = accentColor,
                    modifier = Modifier.size(13.dp)
                )
                Spacer(modifier = Modifier.width(5.dp))
                Text(
                    text = title,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = accentColor
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = value,
                fontSize = 11.sp,
                color = TextPrimary,
                lineHeight = 16.sp
            )
        }
    }
}

@Composable
private fun GeneratedPromptsCard(
    result: AnalysisResult,
    activePlatform: PromptTargetPlatform,
    onSelectPlatform: (PromptTargetPlatform) -> Unit,
    onUpdatePrompt: (String) -> Unit,
    onCopy: (String, String) -> Unit
) {
    val promptForActivePlatform = when (activePlatform) {
        PromptTargetPlatform.GOOGLE_FLOW -> result.fullVideoChronologicalPrompt
        PromptTargetPlatform.RUNWAY_GEN3 -> result.runwayGen3Prompt
        PromptTargetPlatform.OPENAI_SORA -> result.soraPrompt
        PromptTargetPlatform.LUMA_DREAM -> result.lumaDreamMachinePrompt
        PromptTargetPlatform.PIKA_LABS -> result.pikaPrompt
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(1.dp, NeonCyan.copy(alpha = 0.4f), RoundedCornerShape(14.dp))
            .testTag("generated_prompts_card"),
        colors = CardDefaults.cardColors(containerColor = DarkCardBg)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.AutoAwesome,
                        contentDescription = null,
                        tint = NeonCyan,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "CHRONOLOGICAL VIDEO RECONSTRUCTION",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = NeonCyan,
                        letterSpacing = 1.sp
                    )
                }

                Button(
                    onClick = { onCopy(result.fullVideoChronologicalPrompt, "Full Video Prompt") },
                    colors = ButtonDefaults.buttonColors(containerColor = DarkSurfaceElevated),
                    shape = RoundedCornerShape(6.dp),
                    modifier = Modifier.height(32.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.ContentCopy,
                        contentDescription = "Copy",
                        tint = NeonCyan,
                        modifier = Modifier.size(13.dp)
                    )
                    Spacer(modifier = Modifier.width(5.dp))
                    Text("Copy Full", fontSize = 11.sp, color = NeonCyan)
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Platform Syntax Switcher Tabs (Runway, Sora, Luma, Pika)
            val platforms = PromptTargetPlatform.values()
            val selectedTabIndex = platforms.indexOf(activePlatform)

            TabRow(
                selectedTabIndex = selectedTabIndex,
                containerColor = DarkSurfaceElevated,
                contentColor = NeonCyan,
                indicator = { tabPositions ->
                    TabRowDefaults.SecondaryIndicator(
                        Modifier.tabIndicatorOffset(tabPositions[selectedTabIndex]),
                        color = NeonCyan
                    )
                },
                modifier = Modifier.clip(RoundedCornerShape(8.dp))
            ) {
                platforms.forEachIndexed { i, plat ->
                    Tab(
                        selected = plat == activePlatform,
                        onClick = { onSelectPlatform(plat) },
                        text = {
                            Text(
                                text = plat.displayName.split(" ").first(),
                                fontSize = 11.sp,
                                fontWeight = if (plat == activePlatform) FontWeight.Bold else FontWeight.Normal,
                                color = if (plat == activePlatform) NeonCyan else TextSecondary
                            )
                        }
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Target Syntax: ${activePlatform.badge}",
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                color = ElectricViolet
            )

            Spacer(modifier = Modifier.height(8.dp))

            OutlinedTextField(
                value = promptForActivePlatform,
                onValueChange = { onUpdatePrompt(it) },
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("prompt_edit_textfield"),
                textStyle = androidx.compose.ui.text.TextStyle(
                    fontSize = 12.sp,
                    color = TextPrimary,
                    fontFamily = FontFamily.Monospace,
                    lineHeight = 18.sp
                ),
                shape = RoundedCornerShape(10.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = DarkSurfaceElevated,
                    unfocusedContainerColor = DarkSurfaceElevated,
                    focusedBorderColor = NeonCyan,
                    unfocusedBorderColor = DarkCardBorder
                ),
                minLines = 4,
                maxLines = 8
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Negative Prompt Box
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(DarkSurfaceElevated)
                    .border(1.dp, DarkCardBorder, RoundedCornerShape(8.dp))
                    .padding(10.dp)
            ) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "NEGATIVE PROMPT (QUALITY FILTERS):",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFF43F5E),
                            letterSpacing = 0.5.sp
                        )

                        Text(
                            text = "Copy",
                            fontSize = 10.sp,
                            color = NeonCyan,
                            modifier = Modifier.clickable {
                                onCopy(result.negativePrompt, "Negative Prompt")
                            }
                        )
                    }

                    Spacer(modifier = Modifier.height(4.dp))

                    Text(
                        text = result.negativePrompt,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        color = TextSecondary,
                        lineHeight = 16.sp
                    )
                }
            }
        }
    }
}

@Composable
private fun ConsistencyDirectivesCard(result: AnalysisResult) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(1.dp, DarkCardBorder, RoundedCornerShape(14.dp)),
        colors = CardDefaults.cardColors(containerColor = DarkCardBg)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Shield,
                    contentDescription = null,
                    tint = ElectricViolet,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "CONTINUITY & CONSISTENCY DIRECTIVES",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = ElectricViolet,
                    letterSpacing = 1.sp
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = result.characterConsistencyNotes,
                fontSize = 12.sp,
                color = TextSecondary,
                lineHeight = 17.sp
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = result.cameraAndVisualConsistencyNotes,
                fontSize = 12.sp,
                color = TextSecondary,
                lineHeight = 17.sp
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = result.transitionContinuityInstructions,
                fontSize = 12.sp,
                color = TextSecondary,
                lineHeight = 17.sp
            )
        }
    }
}

@Composable
private fun WorkspaceExportBar(
    result: AnalysisResult,
    metadata: VideoMetadata?,
    context: Context
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .border(1.dp, DarkCardBorder, RoundedCornerShape(12.dp)),
        colors = CardDefaults.cardColors(containerColor = DarkCardBg)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                text = "EXPORT & INTEGRATIONS",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = TextSecondary,
                letterSpacing = 1.sp
            )

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Export JSON
                Button(
                    onClick = {
                        val json = formatAnalysisAsJson(result, metadata)
                        copyToClipboard(context, json, "Structured JSON copied to clipboard")
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = DarkSurfaceElevated),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.weight(1f).height(40.dp).testTag("export_json_button")
                ) {
                    Text("Copy JSON", fontSize = 12.sp, color = NeonCyan, fontWeight = FontWeight.Bold)
                }

                // Export TXT
                Button(
                    onClick = {
                        val txt = formatAnalysisAsTxt(result, metadata)
                        copyToClipboard(context, txt, "Formatted Text Report copied to clipboard")
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = DarkSurfaceElevated),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.weight(1f).height(40.dp).testTag("export_txt_button")
                ) {
                    Text("Copy TXT", fontSize = 12.sp, color = ElectricViolet, fontWeight = FontWeight.Bold)
                }

                // Share Intent
                Button(
                    onClick = {
                        val shareText = "${result.fullVideoChronologicalPrompt}\n\nNegative:\n${result.negativePrompt}"
                        val sendIntent = Intent().apply {
                            action = Intent.ACTION_SEND
                            putExtra(Intent.EXTRA_TEXT, shareText)
                            type = "text/plain"
                        }
                        context.startActivity(Intent.createChooser(sendIntent, "Share AI Video Prompt"))
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = NeonCyan),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.weight(1f).height(40.dp).testTag("share_prompt_button")
                ) {
                    Icon(
                        imageVector = Icons.Default.Share,
                        contentDescription = null,
                        tint = Color(0xFF070A12),
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Share", fontSize = 12.sp, color = Color(0xFF070A12), fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

private fun copyToClipboard(context: Context, text: String, toastMessage: String) {
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    val clip = ClipData.newPlainText("VisionPrompt AI", text)
    clipboard.setPrimaryClip(clip)
    Toast.makeText(context, toastMessage, Toast.LENGTH_SHORT).show()
}

private fun parseHexColor(hex: String): Color {
    return try {
        val clean = hex.removePrefix("#")
        val colorInt = android.graphics.Color.parseColor("#$clean")
        Color(colorInt)
    } catch (e: Exception) {
        NeonCyan
    }
}

private fun formatAnalysisAsJson(result: AnalysisResult, metadata: VideoMetadata?): String {
    val scenesJson = result.scenes.joinToString(",\n    ") { sc ->
        """{
      "scene": ${sc.sceneNumber},
      "start": "${sc.startTimestamp}",
      "end": "${sc.endTimestamp}",
      "duration": ${sc.durationSec},
      "title": "${sc.title.replace("\"", "\\\"")}",
      "camera": "${sc.cameraMovement.replace("\"", "\\\"")}",
      "framing": "${sc.framing.replace("\"", "\\\"")}",
      "lighting": "${sc.lighting.replace("\"", "\\\"")}",
      "palette": [${sc.colorPaletteHexes.joinToString(", ") { "\"$it\"" }}],
      "prompt": "${sc.selfContainedScenePrompt.replace("\"", "\\\"").replace("\n", " ")}"
    }"""
    }

    return """{
  "application": "VisionPrompt AI",
  "version": "1.1.0",
  "video": {
    "title": "${metadata?.title ?: result.videoTitle}",
    "duration": "${metadata?.durationFormatted ?: result.videoDurationFormatted}",
    "resolution": "${metadata?.resolutionText ?: "1920x1080"}"
  },
  "engine": "${result.engineUsed}",
  "chronologicalReconstruction": "${result.fullVideoChronologicalPrompt.replace("\"", "\\\"").replace("\n", " ")}",
  "runwayGen3Prompt": "${result.runwayGen3Prompt.replace("\"", "\\\"")}",
  "soraPrompt": "${result.soraPrompt.replace("\"", "\\\"")}",
  "lumaPrompt": "${result.lumaDreamMachinePrompt.replace("\"", "\\\"")}",
  "negativePrompt": "${result.negativePrompt.replace("\"", "\\\"")}",
  "characterConsistency": "${result.characterConsistencyNotes.replace("\"", "\\\"")}",
  "scenes": [
    $scenesJson
  ]
}"""
}

private fun formatAnalysisAsTxt(result: AnalysisResult, metadata: VideoMetadata?): String {
    return buildString {
        appendLine("==================================================")
        appendLine("VISIONPROMPT AI - DEEP SCENE DECONSTRUCTION REPORT")
        appendLine("==================================================")
        appendLine("Video: ${metadata?.title ?: result.videoTitle}")
        appendLine("Duration: ${metadata?.durationFormatted ?: result.videoDurationFormatted}")
        appendLine("Analyzed: ${result.analyzedAtFormatted}")
        appendLine("Engine: ${result.engineUsed}")
        appendLine()
        appendLine("------------- CHRONOLOGICAL VIDEO PROMPT ---------")
        appendLine(result.fullVideoChronologicalPrompt)
        appendLine()
        appendLine("------------- SCENE-BY-SCENE RECONSTRUCTION ------")
        result.scenes.forEach { sc ->
            appendLine("SHOT #${sc.sceneNumber} ${sc.timestampRange}: ${sc.title}")
            appendLine("Camera: ${sc.cameraMovement} | Optics: ${sc.framing}")
            appendLine("Prompt: ${sc.selfContainedScenePrompt}")
            appendLine("Lighting: ${sc.lighting}")
            appendLine("Continuity: ${sc.continuityNotes}")
            appendLine()
        }
        appendLine("------------- CONSISTENCY DIRECTIVES -------------")
        appendLine(result.characterConsistencyNotes)
        appendLine(result.cameraAndVisualConsistencyNotes)
        appendLine(result.transitionContinuityInstructions)
        appendLine()
        appendLine("Generated by VisionPrompt AI (AI Studio Build)")
    }
}
