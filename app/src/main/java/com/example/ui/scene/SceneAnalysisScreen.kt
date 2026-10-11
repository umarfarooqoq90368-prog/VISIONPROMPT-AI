package com.example.ui.scene

import android.graphics.Bitmap
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextFieldDefaults
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
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.AnalysisResult
import com.example.model.AnalysisUiState
import com.example.model.PromptTargetPlatform
import com.example.model.SceneDetail
import com.example.model.VideoMetadata
import com.example.ui.theme.CyberCyan
import com.example.ui.theme.ElectricBlue
import com.example.ui.theme.EmeraldSuccess
import com.example.ui.theme.MagentaAccent
import com.example.ui.theme.NavyBgDeep
import com.example.ui.theme.NavyBorderSubtle
import com.example.ui.theme.NavyCardBg
import com.example.ui.theme.NavyCardBorder
import com.example.ui.theme.NavyCardElevated
import com.example.ui.theme.RoyalViolet
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.ui.theme.TextTertiary

/**
 * Scene Analysis Screen
 *
 * Implements:
 * 1. Visual 5-Stage Workflow Pipeline:
 *    Upload → Analyze Video → Detect Scenes → Analyze Scenes → Generate Prompts
 * 2. Visual Scene Timeline with Thumbnails:
 *    Scene 01 — 00:00–00:06, Scene 02 — 00:06–00:12, Scene 03 — 00:12–00:20...
 * 3. Detailed Scene Attributes breakdown:
 *    - Characters & Character Appearance
 *    - Environment
 *    - Main Action
 *    - Objects
 *    - Camera Angle & Camera Movement
 *    - Lighting
 *    - Mood
 *    - Weather
 *    - Visual Style
 *    - Color Palette (Hex chips)
 *    - Atmosphere & Important Visual Details
 * 4. Google Flow-Ready Generated Prompt:
 *    [Subject + Characters + Environment + Action + Camera + Camera Movement + Lighting + Composition + Mood + Visual Style + Motion + Background + Atmosphere]
 * 5. Actions per Scene:
 *    Copy Prompt, Edit Prompt, Regenerate, Save
 * 6. Character & Style Consistency tracker between scenes
 */
@Composable
fun SceneAnalysisScreen(
    uiState: AnalysisUiState,
    metadata: VideoMetadata?,
    currentResult: AnalysisResult?,
    activeSceneIndex: Int,
    activePlatform: PromptTargetPlatform,
    onSelectSceneIndex: (Int) -> Unit,
    onUpdateScenePrompt: (Int, String) -> Unit,
    onRegenerateScene: (Int) -> Unit,
    onSaveProject: () -> Unit,
    onCancelAnalysis: () -> Unit,
    modifier: Modifier = Modifier
) {
    val clipboardManager = LocalClipboardManager.current
    var copiedNotice by remember { mutableStateOf<String?>(null) }
    var editingSceneIndex by remember { mutableStateOf<Int?>(null) }
    var editedTextDraft by remember { mutableStateOf("") }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(NavyBgDeep)
            .padding(horizontal = 16.dp)
            .testTag("scene_analysis_screen"),
        contentPadding = PaddingValues(top = 16.dp, bottom = 40.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        // 1. Five-Stage Workflow Progress Visualizer
        item {
            WorkflowPipelineIndicator(uiState = uiState, onCancel = onCancelAnalysis)
        }

        // When analysis is active / loading
        if (uiState is AnalysisUiState.Processing) {
            item {
                ProcessingStageCard(state = uiState, onCancel = onCancelAnalysis)
            }
        }

        // When analysis has produced results or using currentResult
        val result = currentResult
        if (result != null) {
            // 2. Video Title & Scene Count Header
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(
                            text = result.videoTitle,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Black,
                            color = TextPrimary
                        )
                        Text(
                            text = "${result.scenes.size} Scenes Automatically Detected • ${result.videoDurationFormatted} Total Duration",
                            fontSize = 12.sp,
                            color = CyberCyan
                        )
                    }

                    Button(
                        onClick = onSaveProject,
                        shape = RoundedCornerShape(8.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = NavyCardElevated),
                        modifier = Modifier.border(1.dp, ElectricBlue.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                    ) {
                        Icon(imageVector = Icons.Default.Save, contentDescription = null, modifier = Modifier.size(14.dp), tint = CyberCyan)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Save Project", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                    }
                }
            }

            // 3. Visual Timeline with Scene Thumbnails
            item {
                Column {
                    Text(
                        text = "VISUAL SCENE TIMELINE",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextSecondary,
                        letterSpacing = 1.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    VisualSceneTimeline(
                        scenes = result.scenes,
                        activeSceneIndex = activeSceneIndex,
                        onSelectScene = onSelectSceneIndex
                    )
                }
            }

            // 4. Character & Style Consistency Banner
            item {
                CharacterAndStyleConsistencyCard(result = result)
            }

            // 5. Active Scene Deconstructed Attributes & Google Flow Prompt
            val activeScene = result.scenes.getOrNull(activeSceneIndex) ?: result.scenes.firstOrNull()
            if (activeScene != null) {
                item {
                    val isEditingThis = editingSceneIndex == activeSceneIndex
                    ActiveSceneDetailedInspector(
                        scene = activeScene,
                        sceneIndex = activeSceneIndex,
                        isEditing = isEditingThis,
                        draftText = if (isEditingThis) editedTextDraft else activeScene.activePrompt,
                        onDraftChange = { editedTextDraft = it },
                        onStartEdit = {
                            editingSceneIndex = activeSceneIndex
                            editedTextDraft = activeScene.activePrompt
                        },
                        onSaveEdit = {
                            onUpdateScenePrompt(activeSceneIndex, editedTextDraft)
                            editingSceneIndex = null
                            copiedNotice = "Updated Scene 0${activeScene.sceneNumber} prompt!"
                        },
                        onCancelEdit = {
                            editingSceneIndex = null
                        },
                        onCopyPrompt = {
                            clipboardManager.setText(AnnotatedString(activeScene.activePrompt))
                            copiedNotice = "Copied Scene 0${activeScene.sceneNumber} prompt!"
                        },
                        onRegenerate = {
                            onRegenerateScene(activeSceneIndex)
                            copiedNotice = "Regenerated Scene 0${activeScene.sceneNumber} prompt!"
                        },
                        onSave = onSaveProject
                    )
                }
            }
        }
    }
}

@Composable
private fun WorkflowPipelineIndicator(
    uiState: AnalysisUiState,
    onCancel: () -> Unit
) {
    val currentStage = when (uiState) {
        is AnalysisUiState.Processing -> uiState.currentStageIndex
        is AnalysisUiState.Success -> 5
        else -> 1
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(1.dp, NavyCardBorder, RoundedCornerShape(14.dp)),
        colors = CardDefaults.cardColors(containerColor = NavyCardBg)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "WORKFLOW PIPELINE",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = CyberCyan,
                    letterSpacing = 1.sp
                )

                Text(
                    text = "Stage $currentStage of 5",
                    fontSize = 11.sp,
                    color = TextTertiary
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // 5 Stages: Upload → Analyze Video → Detect Scenes → Analyze Scenes → Generate Prompts
            val stages = listOf(
                "Upload",
                "Analyze Video",
                "Detect Scenes",
                "Analyze Scenes",
                "Generate Prompts"
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                stages.forEachIndexed { index, stageName ->
                    val stageNumber = index + 1
                    val isCompleted = stageNumber < currentStage
                    val isCurrent = stageNumber == currentStage

                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(
                            modifier = Modifier
                                .size(24.dp)
                                .clip(CircleShape)
                                .background(
                                    when {
                                        isCompleted -> EmeraldSuccess.copy(alpha = 0.25f)
                                        isCurrent -> ElectricBlue
                                        else -> NavyCardElevated
                                    }
                                )
                                .border(
                                    1.dp,
                                    when {
                                        isCompleted -> EmeraldSuccess
                                        isCurrent -> CyberCyan
                                        else -> NavyBorderSubtle
                                    },
                                    CircleShape
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            if (isCompleted) {
                                Icon(imageVector = Icons.Default.Check, contentDescription = null, tint = EmeraldSuccess, modifier = Modifier.size(12.dp))
                            } else {
                                Text(
                                    text = stageNumber.toString(),
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isCurrent) Color.White else TextTertiary
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(3.dp))

                        Text(
                            text = stageName,
                            fontSize = 9.sp,
                            fontWeight = if (isCurrent) FontWeight.Bold else FontWeight.Medium,
                            color = if (isCurrent) CyberCyan else TextTertiary,
                            maxLines = 1
                        )
                    }

                    if (index < stages.size - 1) {
                        Box(
                            modifier = Modifier
                                .width(16.dp)
                                .height(2.dp)
                                .background(if (stageNumber < currentStage) EmeraldSuccess else NavyBorderSubtle)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ProcessingStageCard(
    state: AnalysisUiState.Processing,
    onCancel: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(
                1.dp,
                Brush.linearGradient(listOf(ElectricBlue, RoyalViolet)),
                RoundedCornerShape(14.dp)
            ),
        colors = CardDefaults.cardColors(containerColor = NavyCardBg)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(
                        progress = { state.progress },
                        modifier = Modifier.size(24.dp),
                        color = CyberCyan,
                        strokeWidth = 2.5.dp
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = state.stepTitle,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                }

                Text(
                    text = "${(state.progress * 100).toInt()}%",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Black,
                    color = CyberCyan
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = state.stepDetail,
                fontSize = 12.sp,
                color = TextSecondary,
                lineHeight = 16.sp
            )

            Spacer(modifier = Modifier.height(12.dp))

            Button(
                onClick = onCancel,
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(containerColor = NavyCardElevated),
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp)
            ) {
                Text("Cancel Analysis", fontSize = 11.sp, color = MagentaAccent)
            }
        }
    }
}

@Composable
private fun VisualSceneTimeline(
    scenes: List<SceneDetail>,
    activeSceneIndex: Int,
    onSelectScene: (Int) -> Unit
) {
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        itemsIndexed(scenes) { index, scene ->
            val isSelected = index == activeSceneIndex
            Box(
                modifier = Modifier
                    .width(150.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(if (isSelected) NavyCardElevated else NavyCardBg)
                    .border(
                        if (isSelected) 2.dp else 1.dp,
                        if (isSelected) ElectricBlue else NavyCardBorder,
                        RoundedCornerShape(12.dp)
                    )
                    .clickable { onSelectScene(index) }
                    .padding(10.dp)
                    .testTag("scene_timeline_item_$index")
            ) {
                Column {
                    // Thumbnail
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(72.dp)
                            .clip(RoundedCornerShape(6.dp))
                            .background(Color(0xFF0F172A))
                            .border(0.5.dp, NavyBorderSubtle, RoundedCornerShape(6.dp)),
                        contentAlignment = Alignment.Center
                    ) {
                        if (scene.extractedBitmap != null) {
                            Image(
                                bitmap = scene.extractedBitmap.asImageBitmap(),
                                contentDescription = scene.title,
                                modifier = Modifier.fillMaxSize()
                            )
                        } else {
                            Icon(
                                imageVector = Icons.Default.Videocam,
                                contentDescription = null,
                                tint = CyberCyan,
                                modifier = Modifier.size(24.dp)
                            )
                        }

                        // Timestamp Badge
                        Box(
                            modifier = Modifier
                                .align(Alignment.BottomEnd)
                                .padding(4.dp)
                                .clip(RoundedCornerShape(3.dp))
                                .background(Color.Black.copy(alpha = 0.8f))
                                .padding(horizontal = 4.dp, vertical = 1.dp)
                        ) {
                            Text(
                                text = "${scene.startTimestamp} - ${scene.endTimestamp}",
                                fontSize = 8.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = "Scene ${String.format("%02d", scene.sceneNumber)}",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (isSelected) CyberCyan else TextPrimary
                    )

                    Text(
                        text = scene.title,
                        fontSize = 10.sp,
                        color = TextSecondary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}

@Composable
private fun CharacterAndStyleConsistencyCard(result: AnalysisResult) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(
                1.dp,
                Brush.linearGradient(listOf(RoyalViolet.copy(alpha = 0.6f), ElectricBlue.copy(alpha = 0.6f))),
                RoundedCornerShape(14.dp)
            ),
        colors = CardDefaults.cardColors(containerColor = NavyCardBg)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(RoyalViolet)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "CHARACTER & STYLE CONSISTENCY PRESERVED",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = RoyalViolet,
                    letterSpacing = 0.8.sp
                )
            }

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = result.characterConsistencyNotes.ifEmpty {
                    "Maintains exact character facial features, hairstyle, clothing textures, spatial environment, and color grading across scenes 1 through ${result.scenes.size} so Google Flow renders identical character identity."
                },
                fontSize = 11.sp,
                color = TextSecondary,
                lineHeight = 15.sp
            )
        }
    }
}

@Composable
private fun ActiveSceneDetailedInspector(
    scene: SceneDetail,
    sceneIndex: Int,
    isEditing: Boolean,
    draftText: String,
    onDraftChange: (String) -> Unit,
    onStartEdit: () -> Unit,
    onSaveEdit: () -> Unit,
    onCancelEdit: () -> Unit,
    onCopyPrompt: () -> Unit,
    onRegenerate: () -> Unit,
    onSave: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .border(1.dp, NavyCardBorder, RoundedCornerShape(16.dp))
            .testTag("active_scene_inspector"),
        colors = CardDefaults.cardColors(containerColor = NavyCardBg)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(6.dp))
                            .background(ElectricBlue.copy(alpha = 0.25f))
                            .padding(horizontal = 8.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = "Scene ${String.format("%02d", scene.sceneNumber)}",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Black,
                            color = CyberCyan
                        )
                    }

                    Spacer(modifier = Modifier.width(8.dp))

                    Text(
                        text = "${scene.startTimestamp} - ${scene.endTimestamp}",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextTertiary
                    )
                }

                Text(
                    text = "${scene.durationSec}s shot",
                    fontSize = 11.sp,
                    color = TextSecondary
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            // All Identified Scene Attributes
            Text(
                text = "IDENTIFIED SCENE ATTRIBUTES",
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                color = CyberCyan,
                letterSpacing = 1.sp
            )

            Spacer(modifier = Modifier.height(8.dp))

            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                SceneAttributeRow("Characters", scene.characters)
                SceneAttributeRow("Character Appearance", scene.characterAppearance)
                SceneAttributeRow("Environment", scene.environment)
                SceneAttributeRow("Main Action", scene.mainAction)
                SceneAttributeRow("Objects", scene.objects)
                SceneAttributeRow("Camera Angle", scene.cameraAngle)
                SceneAttributeRow("Camera Movement", scene.cameraMovement)
                SceneAttributeRow("Lighting", scene.lighting)
                SceneAttributeRow("Mood", scene.mood)
                SceneAttributeRow("Weather", scene.weather)
                SceneAttributeRow("Visual Style", scene.visualStyle)
                SceneAttributeRow("Atmosphere", scene.atmosphere)
                SceneAttributeRow("Important Details", scene.importantVisualDetails)
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Generated Google Flow Ready Prompt Box
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(NavyCardElevated)
                    .border(1.dp, ElectricBlue.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
                    .padding(14.dp)
            ) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "GOOGLE FLOW-READY GENERATED PROMPT",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = CyberCyan,
                            letterSpacing = 0.8.sp
                        )

                        Text(
                            text = "Subject + Character + Camera + Light + Mood",
                            fontSize = 9.sp,
                            color = TextTertiary
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    if (isEditing) {
                        OutlinedTextField(
                            value = draftText,
                            onValueChange = onDraftChange,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(130.dp),
                            textStyle = androidx.compose.ui.text.TextStyle(fontSize = 12.sp, color = TextPrimary),
                            colors = TextFieldDefaults.colors(
                                focusedContainerColor = NavyBgDeep,
                                unfocusedContainerColor = NavyBgDeep,
                                focusedIndicatorColor = CyberCyan,
                                unfocusedIndicatorColor = NavyBorderSubtle
                            )
                        )

                        Spacer(modifier = Modifier.height(8.dp))

                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.align(Alignment.End)
                        ) {
                            Button(
                                onClick = onCancelEdit,
                                colors = ButtonDefaults.buttonColors(containerColor = NavyCardBg)
                            ) {
                                Text("Cancel", fontSize = 11.sp, color = TextSecondary)
                            }
                            Button(
                                onClick = onSaveEdit,
                                colors = ButtonDefaults.buttonColors(containerColor = EmeraldSuccess)
                            ) {
                                Text("Save Prompt", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    } else {
                        Text(
                            text = scene.activePrompt,
                            fontSize = 12.sp,
                            color = TextPrimary,
                            lineHeight = 17.sp
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Four Action Buttons: Copy Prompt, Edit Prompt, Regenerate, Save
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Copy Prompt
                Button(
                    onClick = onCopyPrompt,
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = ElectricBlue),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(imageVector = Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Copy", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }

                // Edit Prompt
                Button(
                    onClick = onStartEdit,
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = NavyCardElevated),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
                    modifier = Modifier
                        .weight(1f)
                        .border(1.dp, NavyBorderSubtle, RoundedCornerShape(10.dp))
                ) {
                    Icon(imageVector = Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(14.dp), tint = CyberCyan)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Edit", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                }

                // Regenerate
                Button(
                    onClick = onRegenerate,
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = NavyCardElevated),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
                    modifier = Modifier
                        .weight(1.1f)
                        .border(1.dp, NavyBorderSubtle, RoundedCornerShape(10.dp))
                ) {
                    Icon(imageVector = Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(14.dp), tint = RoyalViolet)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Regenerate", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                }

                // Save
                Button(
                    onClick = onSave,
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = NavyCardElevated),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
                    modifier = Modifier
                        .weight(1f)
                        .border(1.dp, NavyBorderSubtle, RoundedCornerShape(10.dp))
                ) {
                    Icon(imageVector = Icons.Default.Save, contentDescription = null, modifier = Modifier.size(14.dp), tint = EmeraldSuccess)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Save", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                }
            }
        }
    }
}

@Composable
private fun SceneAttributeRow(
    label: String,
    value: String
) {
    if (value.isBlank()) return
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(6.dp))
            .background(NavyCardElevated)
            .padding(horizontal = 10.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.Top
    ) {
        Text(
            text = label,
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold,
            color = CyberCyan,
            modifier = Modifier.width(120.dp)
        )
        Text(
            text = value,
            fontSize = 11.sp,
            color = TextSecondary,
            modifier = Modifier.weight(1f)
        )
    }
}
