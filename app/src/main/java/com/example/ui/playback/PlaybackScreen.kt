package com.example.ui.playback

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.material.icons.filled.FastForward
import androidx.compose.material.icons.filled.FastRewind
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Repeat
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
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
import com.example.model.SampleVideoPreset
import com.example.model.VideoMetadata
import com.example.ui.theme.DarkBgMain
import com.example.ui.theme.DarkCardBg
import com.example.ui.theme.DarkCardBorder
import com.example.ui.theme.DarkSurfaceElevated
import com.example.ui.theme.ElectricViolet
import com.example.ui.theme.NeonCyan
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.ui.theme.TextTertiary
import kotlinx.coroutines.delay

@Composable
fun PlaybackScreen(
    result: AnalysisResult?,
    metadata: VideoMetadata?,
    samplePresets: List<SampleVideoPreset>,
    onGoToWorkspace: () -> Unit,
    onSelectPreset: (SampleVideoPreset) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scrollState = rememberScrollState()

    var isPlaying by remember { mutableStateOf(true) }
    var currentSceneIndex by remember { mutableIntStateOf(0) }
    var scrubProgress by remember { mutableFloatStateOf(0f) }

    val scenes = result?.scenes.orEmpty()
    val totalScenes = scenes.size.coerceAtLeast(1)

    // Playback loop simulation
    LaunchedEffect(isPlaying, scenes.size) {
        while (isPlaying && scenes.isNotEmpty()) {
            delay(1800)
            currentSceneIndex = (currentSceneIndex + 1) % scenes.size
            scrubProgress = currentSceneIndex.toFloat() / (scenes.size - 1).coerceAtLeast(1)
        }
    }

    val activeScene = scenes.getOrNull(currentSceneIndex)

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(DarkBgMain)
            .verticalScroll(scrollState)
            .padding(16.dp)
            .testTag("playback_screen_container")
    ) {
        // Screen Header
        Column {
            Text(
                text = "CINEMATIC RECONSTRUCTION PLAYER",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = NeonCyan,
                letterSpacing = 1.2.sp
            )
            Text(
                text = "Real-Time Scene & Vector Playback",
                fontSize = 18.sp,
                fontWeight = FontWeight.Black,
                color = TextPrimary
            )
        }

        Spacer(modifier = Modifier.height(14.dp))

        if (scenes.isEmpty()) {
            // Empty State Card
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .border(1.dp, DarkCardBorder, RoundedCornerShape(14.dp)),
                colors = CardDefaults.cardColors(containerColor = DarkCardBg)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Box(
                        modifier = Modifier
                            .size(56.dp)
                            .clip(CircleShape)
                            .background(DarkSurfaceElevated),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.PlayArrow,
                            contentDescription = null,
                            tint = NeonCyan,
                            modifier = Modifier.size(32.dp)
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = "No Video Analysis Loaded",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = "Upload a video or select a cinematic preset below to inspect dynamic frame playback and camera kinematics.",
                        fontSize = 12.sp,
                        color = TextSecondary,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                        lineHeight = 18.sp
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    Button(
                        onClick = onGoToWorkspace,
                        colors = ButtonDefaults.buttonColors(containerColor = DarkSurfaceElevated),
                        border = androidx.compose.foundation.BorderStroke(1.dp, NeonCyan)
                    ) {
                        Icon(imageVector = Icons.Default.Movie, contentDescription = null, tint = NeonCyan)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Open Workspace", color = TextPrimary)
                    }
                }
            }
        } else {
            // Video Viewport Card
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .border(1.dp, Brush.linearGradient(listOf(NeonCyan.copy(alpha = 0.7f), ElectricViolet.copy(alpha = 0.7f))), RoundedCornerShape(16.dp)),
                colors = CardDefaults.cardColors(containerColor = DarkCardBg)
            ) {
                Column {
                    // Video Viewport Screen
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(220.dp)
                            .background(Color(0xFF070B14)),
                        contentAlignment = Alignment.Center
                    ) {
                        if (activeScene?.extractedBitmap != null) {
                            Image(
                                bitmap = activeScene.extractedBitmap.asImageBitmap(),
                                contentDescription = "Active Shot",
                                modifier = Modifier.fillMaxSize()
                            )
                        } else {
                            Icon(
                                imageVector = Icons.Default.Movie,
                                contentDescription = null,
                                tint = DarkCardBorder,
                                modifier = Modifier.size(64.dp)
                            )
                        }

                        // Gradient cinematic overlay
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(
                                    Brush.verticalGradient(
                                        listOf(
                                            Color.Transparent,
                                            Color(0xBB070A12)
                                        )
                                    )
                                )
                        )

                        // Top Overlay badges
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .align(Alignment.TopCenter)
                                .padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(6.dp))
                                    .background(Color(0xDD000000))
                                    .padding(horizontal = 8.dp, vertical = 4.dp)
                            ) {
                                Text(
                                    text = "SHOT 0${(activeScene?.sceneNumber ?: 1)} / 0$totalScenes",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = NeonCyan
                                )
                            }

                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(6.dp))
                                    .background(Color(0xDD000000))
                                    .padding(horizontal = 8.dp, vertical = 4.dp)
                            ) {
                                Text(
                                    text = activeScene?.timestampRange ?: "[00:00.0 - 00:02.5]",
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = ElectricViolet
                                )
                            }
                        }

                        // Bottom Viewport Vector HUD
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .align(Alignment.BottomStart)
                                .padding(12.dp)
                        ) {
                            Text(
                                text = activeScene?.title ?: "Scene Playback",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = Icons.Default.CameraAlt,
                                    contentDescription = null,
                                    tint = NeonCyan,
                                    modifier = Modifier.size(13.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = activeScene?.cameraMovement ?: "Dynamic Tracking",
                                    fontSize = 11.sp,
                                    color = NeonCyan
                                )
                            }
                        }
                    }

                    // Scrubber & Controls
                    Column(modifier = Modifier.padding(14.dp)) {
                        Slider(
                            value = scrubProgress,
                            onValueChange = { frac ->
                                scrubProgress = frac
                                currentSceneIndex = (frac * (scenes.size - 1)).toInt().coerceIn(0, scenes.size - 1)
                            },
                            colors = SliderDefaults.colors(
                                thumbColor = NeonCyan,
                                activeTrackColor = NeonCyan,
                                inactiveTrackColor = DarkCardBorder
                            ),
                            modifier = Modifier.fillMaxWidth()
                        )

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = activeScene?.startTimestamp ?: "00:00.0",
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                color = TextTertiary
                            )

                            // Playback transport buttons
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                IconButton(
                                    onClick = {
                                        currentSceneIndex = (currentSceneIndex - 1 + scenes.size) % scenes.size
                                        scrubProgress = currentSceneIndex.toFloat() / (scenes.size - 1).coerceAtLeast(1)
                                    }
                                ) {
                                    Icon(imageVector = Icons.Default.FastRewind, contentDescription = "Prev Shot", tint = TextPrimary)
                                }

                                Box(
                                    modifier = Modifier
                                        .size(44.dp)
                                        .clip(CircleShape)
                                        .background(NeonCyan)
                                        .clickable { isPlaying = !isPlaying },
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                                        contentDescription = if (isPlaying) "Pause" else "Play",
                                        tint = Color(0xFF070A12),
                                        modifier = Modifier.size(24.dp)
                                    )
                                }

                                IconButton(
                                    onClick = {
                                        currentSceneIndex = (currentSceneIndex + 1) % scenes.size
                                        scrubProgress = currentSceneIndex.toFloat() / (scenes.size - 1).coerceAtLeast(1)
                                    }
                                ) {
                                    Icon(imageVector = Icons.Default.FastForward, contentDescription = "Next Shot", tint = TextPrimary)
                                }
                            }

                            Text(
                                text = metadata?.durationFormatted ?: "00:08.4",
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                color = TextTertiary
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Active Scene Kinematics & Prompt HUD
            activeScene?.let { sc ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(14.dp))
                        .border(1.dp, DarkCardBorder, RoundedCornerShape(14.dp)),
                    colors = CardDefaults.cardColors(containerColor = DarkCardBg)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "ACTIVE SHOT DIRECTORIAL HUD",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = NeonCyan,
                                letterSpacing = 1.sp
                            )

                            Text(
                                text = "Copy Prompt",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = ElectricViolet,
                                modifier = Modifier.clickable {
                                    val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                    cm.setPrimaryClip(ClipData.newPlainText("Shot Prompt", sc.selfContainedScenePrompt))
                                    Toast.makeText(context, "Shot prompt copied to clipboard", Toast.LENGTH_SHORT).show()
                                }
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp))
                                .background(DarkSurfaceElevated)
                                .padding(10.dp)
                        ) {
                            Text(
                                text = sc.selfContainedScenePrompt,
                                fontSize = 12.sp,
                                color = TextPrimary,
                                lineHeight = 18.sp,
                                fontFamily = FontFamily.Monospace
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        // Kinematics details
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(DarkSurfaceElevated)
                                    .padding(8.dp)
                            ) {
                                Column {
                                    Text("Camera Motion", fontSize = 10.sp, color = TextTertiary)
                                    Text(sc.cameraMovement, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = NeonCyan)
                                }
                            }

                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(DarkSurfaceElevated)
                                    .padding(8.dp)
                            ) {
                                Column {
                                    Text("Lighting Kelvin", fontSize = 10.sp, color = TextTertiary)
                                    Text(sc.lightingAndShadowDynamics.ifEmpty { "5600K Daylight Neon" }, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = ElectricViolet, maxLines = 1)
                                }
                            }
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Preset Library Quick Switch
        Text(
            text = "PLAY PRESET RECONSTRUCTIONS",
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            color = NeonCyan,
            letterSpacing = 1.sp
        )

        Spacer(modifier = Modifier.height(8.dp))

        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            samplePresets.forEach { preset ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .border(1.dp, DarkCardBorder, RoundedCornerShape(10.dp))
                        .clickable { onSelectPreset(preset) },
                    colors = CardDefaults.cardColors(containerColor = DarkCardBg)
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .clip(RoundedCornerShape(6.dp))
                                .background(Color(android.graphics.Color.parseColor(preset.accentHex)).copy(alpha = 0.2f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.PlayArrow,
                                contentDescription = null,
                                tint = Color(android.graphics.Color.parseColor(preset.accentHex)),
                                modifier = Modifier.size(20.dp)
                            )
                        }

                        Spacer(modifier = Modifier.width(10.dp))

                        Column(modifier = Modifier.weight(1f)) {
                            Text(text = preset.title, fontSize = 13.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                            Text(text = "${preset.tag} • ${preset.durationText}", fontSize = 11.sp, color = TextTertiary)
                        }

                        Icon(imageVector = Icons.Default.Speed, contentDescription = null, tint = TextTertiary, modifier = Modifier.size(16.dp))
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}
