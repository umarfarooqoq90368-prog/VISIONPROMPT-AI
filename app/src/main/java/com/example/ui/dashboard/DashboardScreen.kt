package com.example.ui.dashboard

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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.AnalysisResult
import com.example.model.SampleVideoPreset
import com.example.ui.components.Animated3DLogo
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
import com.example.viewmodel.AppDestination
import com.example.viewmodel.VisionPromptViewModel

/**
 * Studio Dashboard Screen
 *
 * Requirements:
 * - Upload Video button (Main CTA)
 * - Recent Projects
 * - Stats: Total Videos, Total Scenes, Total Generated Prompts
 * - Recent Prompts
 * - Professional AI SaaS Design
 */
@Composable
fun DashboardScreen(
    currentResult: AnalysisResult?,
    savedProjects: List<AnalysisResult>,
    historyProjects: List<AnalysisResult>,
    presets: List<SampleVideoPreset>,
    onNavigate: (AppDestination) -> Unit,
    onOpenProject: (AnalysisResult) -> Unit,
    onAnalyzePreset: (SampleVideoPreset) -> Unit,
    modifier: Modifier = Modifier
) {
    val clipboardManager = LocalClipboardManager.current
    var copiedNotice by remember { mutableStateOf<String?>(null) }

    // Computed Studio Metrics
    val totalVideosCount = (savedProjects.size + historyProjects.size).coerceAtLeast(1)
    val totalScenesCount = (savedProjects.sumOf { it.scenes.size } + historyProjects.sumOf { it.scenes.size })
        .coerceAtLeast(currentResult?.scenes?.size ?: 4)
    val totalPromptsCount = totalScenesCount

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(NavyBgDeep)
            .padding(horizontal = 16.dp)
            .testTag("dashboard_screen"),
        contentPadding = PaddingValues(top = 16.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp)
    ) {
        // 1. Hero Studio Banner with Primary "Upload Video" CTA
        item {
            DashboardHeroBanner(
                onUploadClick = { onNavigate(AppDestination.UPLOAD_VIDEO) },
                onExploreSceneClick = {
                    if (currentResult != null) onNavigate(AppDestination.SCENE_ANALYSIS)
                    else onNavigate(AppDestination.UPLOAD_VIDEO)
                }
            )
        }

        // 2. Metrics Row: Total Videos, Total Scenes, Total Generated Prompts
        item {
            DashboardStatsRow(
                totalVideos = totalVideosCount,
                totalScenes = totalScenesCount,
                totalPrompts = totalPromptsCount
            )
        }

        // 3. Workflow Pipeline Visualizer Card
        item {
            StudioWorkflowCard()
        }

        // 4. Recent Projects Section
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text(
                        text = "Recent Projects",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                    Text(
                        text = "Analyzed video sequences with extracted scene prompt sets",
                        fontSize = 12.sp,
                        color = TextSecondary
                    )
                }

                if (savedProjects.isNotEmpty() || historyProjects.isNotEmpty()) {
                    Text(
                        text = "View All →",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = CyberCyan,
                        modifier = Modifier
                            .clickable { onNavigate(AppDestination.SAVED_PROJECTS) }
                            .padding(4.dp)
                    )
                }
            }
        }

        item {
            val displayProjects = if (savedProjects.isNotEmpty()) savedProjects else historyProjects
            if (displayProjects.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(NavyCardBg)
                        .border(1.dp, NavyCardBorder, RoundedCornerShape(12.dp))
                        .padding(24.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "No analyzed projects yet",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextSecondary
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Button(
                            onClick = { onNavigate(AppDestination.UPLOAD_VIDEO) },
                            colors = ButtonDefaults.buttonColors(containerColor = ElectricBlue),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text("Upload Your First Video", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            } else {
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    items(displayProjects.take(6)) { project ->
                        RecentProjectCard(
                            project = project,
                            onClick = {
                                onOpenProject(project)
                            }
                        )
                    }
                }
            }
        }

        // 5. Recent Prompts (Ready for Google Flow)
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text(
                        text = "Recent Prompts",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                    Text(
                        text = "Google Flow-ready scene prompts with character & camera motion",
                        fontSize = 12.sp,
                        color = TextSecondary
                    )
                }

                Text(
                    text = "All Prompts →",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = CyberCyan,
                    modifier = Modifier
                        .clickable { onNavigate(AppDestination.GENERATED_PROMPTS) }
                        .padding(4.dp)
                )
            }
        }

        item {
            val scenesToDisplay = currentResult?.scenes?.take(4) ?: emptyList()
            if (scenesToDisplay.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(NavyCardBg)
                        .border(1.dp, NavyCardBorder, RoundedCornerShape(12.dp))
                        .padding(20.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "Upload a video to see generated scene prompts here",
                        fontSize = 13.sp,
                        color = TextSecondary
                    )
                }
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    scenesToDisplay.forEachIndexed { idx, scene ->
                        RecentPromptItemCard(
                            sceneNumber = scene.sceneNumber,
                            timeRange = scene.timestampRange,
                            title = scene.title,
                            promptText = scene.activePrompt,
                            onCopy = {
                                clipboardManager.setText(AnnotatedString(scene.activePrompt))
                                copiedNotice = "Copied Scene 0${scene.sceneNumber} prompt!"
                            },
                            onInspect = {
                                onNavigate(AppDestination.SCENE_ANALYSIS)
                            }
                        )
                    }
                }
            }
        }

        // 6. Quick Demo Video Presets
        item {
            Column {
                Text(
                    text = "Or Test With Studio Sample Videos",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                Text(
                    text = "Instant 4-shot and multi-scene analysis presets with character consistency",
                    fontSize = 11.sp,
                    color = TextSecondary
                )
            }
        }

        item {
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                items(presets) { preset ->
                    PresetQuickCard(
                        preset = preset,
                        onAnalyze = { onAnalyzePreset(preset) }
                    )
                }
            }
        }
    }
}

@Composable
private fun DashboardHeroBanner(
    onUploadClick: () -> Unit,
    onExploreSceneClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .border(
                1.dp,
                Brush.linearGradient(listOf(ElectricBlue.copy(alpha = 0.8f), RoyalViolet.copy(alpha = 0.8f))),
                RoundedCornerShape(18.dp)
            )
            .testTag("dashboard_hero_banner"),
        colors = CardDefaults.cardColors(containerColor = NavyCardBg)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.radialGradient(
                        colors = listOf(
                            RoyalViolet.copy(alpha = 0.22f),
                            NavyCardBg
                        ),
                        radius = 800f
                    )
                )
                .padding(20.dp)
        ) {
            Column {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(ElectricBlue.copy(alpha = 0.25f))
                            .padding(horizontal = 8.dp, vertical = 3.dp)
                    ) {
                        Text(
                            text = "AI VIDEO ANALYSIS STUDIO",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = CyberCyan,
                            letterSpacing = 0.8.sp
                        )
                    }

                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(RoyalViolet.copy(alpha = 0.25f))
                            .padding(horizontal = 8.dp, vertical = 3.dp)
                    ) {
                        Text(
                            text = "GOOGLE FLOW READY",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary,
                            letterSpacing = 0.8.sp
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = "Video to Scene Prompt Studio",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Black,
                    color = TextPrimary,
                    lineHeight = 30.sp
                )

                Spacer(modifier = Modifier.height(6.dp))

                Text(
                    text = "Turn Any Video Into Scene-by-Scene AI Prompts. Automated shot detection, character & style consistency, and multi-parameter generation prompts.",
                    fontSize = 13.sp,
                    color = TextSecondary,
                    lineHeight = 18.sp
                )

                Spacer(modifier = Modifier.height(18.dp))

                // Primary CTA Buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Button(
                        onClick = onUploadClick,
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = ElectricBlue,
                            contentColor = Color.White
                        ),
                        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 12.dp),
                        modifier = Modifier
                            .weight(1f)
                            .testTag("dashboard_cta_upload_video")
                    ) {
                        Icon(
                            imageVector = Icons.Default.CloudUpload,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Upload Video",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }

                    Button(
                        onClick = onExploreSceneClick,
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = NavyCardElevated,
                            contentColor = TextPrimary
                        ),
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
                        modifier = Modifier.border(1.dp, NavyBorderSubtle, RoundedCornerShape(12.dp))
                    ) {
                        Text(
                            text = "Open Studio",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DashboardStatsRow(
    totalVideos: Int,
    totalScenes: Int,
    totalPrompts: Int
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        StatCard(
            title = "Total Videos",
            count = totalVideos.toString(),
            icon = Icons.Default.VideoLibrary,
            accentColor = ElectricBlue,
            modifier = Modifier.weight(1f)
        )
        StatCard(
            title = "Total Scenes",
            count = totalScenes.toString(),
            icon = Icons.Default.Movie,
            accentColor = CyberCyan,
            modifier = Modifier.weight(1f)
        )
        StatCard(
            title = "Generated Prompts",
            count = totalPrompts.toString(),
            icon = Icons.Default.Psychology,
            accentColor = RoyalViolet,
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun StatCard(
    title: String,
    count: String,
    icon: ImageVector,
    accentColor: Color,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(14.dp))
            .background(NavyCardBg)
            .border(1.dp, NavyCardBorder, RoundedCornerShape(14.dp))
            .padding(14.dp)
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Box(
                    modifier = Modifier
                        .size(32.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(accentColor.copy(alpha = 0.2f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = accentColor,
                        modifier = Modifier.size(16.dp)
                    )
                }

                Box(
                    modifier = Modifier
                        .size(6.dp)
                        .clip(CircleShape)
                        .background(accentColor)
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = count,
                fontSize = 22.sp,
                fontWeight = FontWeight.Black,
                color = TextPrimary
            )

            Text(
                text = title,
                fontSize = 11.sp,
                color = TextSecondary,
                maxLines = 1
            )
        }
    }
}

@Composable
private fun StudioWorkflowCard() {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(1.dp, NavyCardBorder, RoundedCornerShape(14.dp)),
        colors = CardDefaults.cardColors(containerColor = NavyCardBg)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "STUDIO WORKFLOW",
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                color = CyberCyan,
                letterSpacing = 1.sp
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "UPLOAD → AI ANALYSIS → SCENE DETECTION → SCENE ANALYSIS → PROMPT GENERATION → EXPORT / GOOGLE FLOW",
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = TextSecondary,
                lineHeight = 16.sp
            )

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                WorkflowStepBadge("1", "Upload", ElectricBlue)
                Text("→", color = TextTertiary, fontSize = 12.sp)
                WorkflowStepBadge("2", "Analyze", CyberCyan)
                Text("→", color = TextTertiary, fontSize = 12.sp)
                WorkflowStepBadge("3", "Detect Cuts", RoyalViolet)
                Text("→", color = TextTertiary, fontSize = 12.sp)
                WorkflowStepBadge("4", "Prompts", MagentaAccent)
                Text("→", color = TextTertiary, fontSize = 12.sp)
                WorkflowStepBadge("5", "Flow", EmeraldSuccess)
            }
        }
    }
}

@Composable
private fun WorkflowStepBadge(step: String, label: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .size(24.dp)
                .clip(CircleShape)
                .background(color.copy(alpha = 0.2f))
                .border(1.dp, color, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Text(text = step, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = color)
        }
        Spacer(modifier = Modifier.height(3.dp))
        Text(text = label, fontSize = 10.sp, color = TextPrimary, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun RecentProjectCard(
    project: AnalysisResult,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .width(220.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(NavyCardBg)
            .border(1.dp, NavyCardBorder, RoundedCornerShape(14.dp))
            .clickable(onClick = onClick)
            .padding(14.dp)
            .testTag("recent_project_card_${project.id}")
    ) {
        Column {
            // Mock thumbnail preview
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(90.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(
                        Brush.linearGradient(
                            listOf(
                                Color(0xFF0F172A),
                                Color(0xFF1E293B)
                            )
                        )
                    )
                    .border(0.5.dp, NavyBorderSubtle, RoundedCornerShape(8.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.PlayArrow,
                    contentDescription = null,
                    tint = CyberCyan,
                    modifier = Modifier.size(28.dp)
                )

                Box(
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(6.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(Color.Black.copy(alpha = 0.7f))
                        .padding(horizontal = 4.dp, vertical = 2.dp)
                ) {
                    Text(
                        text = project.videoDurationFormatted,
                        fontSize = 9.sp,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = project.videoTitle,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            Spacer(modifier = Modifier.height(4.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "${project.scenes.size} Scenes Detected",
                    fontSize = 11.sp,
                    color = CyberCyan,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    text = project.analyzedAtFormatted,
                    fontSize = 10.sp,
                    color = TextTertiary
                )
            }
        }
    }
}

@Composable
private fun RecentPromptItemCard(
    sceneNumber: Int,
    timeRange: String,
    title: String,
    promptText: String,
    onCopy: () -> Unit,
    onInspect: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(NavyCardBg)
            .border(1.dp, NavyCardBorder, RoundedCornerShape(12.dp))
            .padding(14.dp)
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(ElectricBlue.copy(alpha = 0.25f))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = "Scene ${String.format("%02d", sceneNumber)}",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = CyberCyan
                        )
                    }

                    Spacer(modifier = Modifier.width(8.dp))

                    Text(
                        text = timeRange,
                        fontSize = 11.sp,
                        color = TextTertiary,
                        fontWeight = FontWeight.Medium
                    )

                    Spacer(modifier = Modifier.width(8.dp))

                    Text(
                        text = title,
                        fontSize = 12.sp,
                        color = TextPrimary,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(
                        onClick = onCopy,
                        modifier = Modifier.size(28.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.ContentCopy,
                            contentDescription = "Copy Prompt",
                            tint = CyberCyan,
                            modifier = Modifier.size(15.dp)
                        )
                    }

                    IconButton(
                        onClick = onInspect,
                        modifier = Modifier.size(28.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.ArrowForward,
                            contentDescription = "Inspect Scene",
                            tint = TextSecondary,
                            modifier = Modifier.size(15.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = promptText,
                fontSize = 11.5.sp,
                color = TextSecondary,
                lineHeight = 16.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

@Composable
private fun PresetQuickCard(
    preset: SampleVideoPreset,
    onAnalyze: () -> Unit
) {
    Box(
        modifier = Modifier
            .width(200.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(NavyCardBg)
            .border(1.dp, NavyCardBorder, RoundedCornerShape(12.dp))
            .clickable(onClick = onAnalyze)
            .padding(12.dp)
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(4.dp))
                        .background(Color(android.graphics.Color.parseColor(preset.accentHex)).copy(alpha = 0.25f))
                        .padding(horizontal = 6.dp, vertical = 2.dp)
                ) {
                    Text(
                        text = preset.tag,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(android.graphics.Color.parseColor(preset.accentHex))
                    )
                }

                Text(
                    text = preset.durationText,
                    fontSize = 10.sp,
                    color = TextTertiary
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = preset.title,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary,
                maxLines = 1
            )

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = preset.description,
                fontSize = 10.sp,
                color = TextSecondary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                lineHeight = 13.sp
            )

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End
            ) {
                Text(
                    text = "Analyze →",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = CyberCyan
                )
            }
        }
    }
}
