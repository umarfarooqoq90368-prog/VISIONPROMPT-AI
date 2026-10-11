package com.example.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.GraphicEq
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.DarkCardBg
import com.example.ui.theme.DarkCardBorder
import com.example.ui.theme.DarkSurfaceElevated
import com.example.ui.theme.ElectricViolet
import com.example.ui.theme.NeonCyan
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.ui.theme.TextTertiary

@Composable
fun HeroVisualizer(
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition(label = "hero_anim")

    // Laser scan position
    val scanOffset by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(3500, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "scan_offset"
    )

    // Waveform phase
    val wavePhase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 6.28f,
        animationSpec = infiniteRepeatable(
            animation = tween(2200, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "wave_phase"
    )

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(DarkCardBg)
            .border(1.dp, DarkCardBorder, RoundedCornerShape(16.dp))
            .padding(16.dp)
            .testTag("hero_visualizer_card")
    ) {
        // Visualizer Top Bar
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(DarkSurfaceElevated)
                    .border(0.5.dp, NeonCyan.copy(alpha = 0.5f), RoundedCornerShape(4.dp))
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Movie,
                        contentDescription = null,
                        tint = NeonCyan,
                        modifier = Modifier.size(13.dp)
                    )
                    Spacer(modifier = Modifier.width(5.dp))
                    Text(
                        text = "NEURAL VISION PIPELINE",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = NeonCyan,
                        letterSpacing = 1.sp
                    )
                }
            }

            Spacer(modifier = Modifier.weight(1f))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.CameraAlt,
                    contentDescription = null,
                    tint = ElectricViolet,
                    modifier = Modifier.size(13.dp)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = "CAM: DOLLY IN (0.8m/s)",
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    color = TextSecondary
                )
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // Animated Canvas: Keyframes, Scene Tracking, Camera Trajectory Vector, Scanning Laser
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(170.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Color(0xFF070B14))
                .testTag("hero_animation_canvas")
        ) {
            val w = size.width
            val h = size.height

            // 1. Draw subtle background coordinate grid
            val gridStep = 32f
            var gx = 0f
            while (gx < w) {
                drawLine(
                    color = Color(0x1500F0FF),
                    start = Offset(gx, 0f),
                    end = Offset(gx, h),
                    strokeWidth = 1f
                )
                gx += gridStep
            }
            var gy = 0f
            while (gy < h) {
                drawLine(
                    color = Color(0x1500F0FF),
                    start = Offset(0f, gy),
                    end = Offset(w, gy),
                    strokeWidth = 1f
                )
                gy += gridStep
            }

            // 2. Draw 3 Simulated Filmstrip Video Keyframe Blocks
            val frameMargin = 14f
            val totalFrames = 3
            val frameW = (w - (frameMargin * (totalFrames + 1))) / totalFrames
            val frameH = 88f
            val frameY = 16f

            for (i in 0 until totalFrames) {
                val fx = frameMargin + i * (frameW + frameMargin)

                // Frame container
                drawRoundRect(
                    color = Color(0xFF111827),
                    topLeft = Offset(fx, frameY),
                    size = Size(frameW, frameH),
                    cornerRadius = CornerRadius(8f, 8f)
                )

                // Frame border
                val isHoveredByScan = (scanOffset * w >= fx && scanOffset * w <= fx + frameW)
                val frameBorderColor = if (isHoveredByScan) NeonCyan else Color(0xFF1F293D)
                drawRoundRect(
                    color = frameBorderColor,
                    topLeft = Offset(fx, frameY),
                    size = Size(frameW, frameH),
                    cornerRadius = CornerRadius(8f, 8f),
                    style = Stroke(width = if (isHoveredByScan) 2f else 1f)
                )

                // Inner scene badge inside frame
                drawRoundRect(
                    color = Color(0x800A0E1A),
                    topLeft = Offset(fx + 6f, frameY + 6f),
                    size = Size(frameW - 12f, 18f),
                    cornerRadius = CornerRadius(4f, 4f)
                )

                // Viewfinder lines inside frame
                val cx = fx + frameW / 2f
                val cy = frameY + frameH / 2f + 6f
                drawLine(
                    color = if (isHoveredByScan) NeonCyan.copy(alpha = 0.8f) else Color(0x4000F0FF),
                    start = Offset(cx - 16f, cy),
                    end = Offset(cx + 16f, cy),
                    strokeWidth = 1.5f
                )
                drawLine(
                    color = if (isHoveredByScan) NeonCyan.copy(alpha = 0.8f) else Color(0x4000F0FF),
                    start = Offset(cx, cy - 12f),
                    end = Offset(cx, cy + 12f),
                    strokeWidth = 1.5f
                )
            }

            // 3. Camera Movement Trajectory Vector (Curved Path between frames)
            val trajectoryPath = Path().apply {
                moveTo(frameMargin + frameW * 0.5f, frameY + frameH + 12f)
                cubicTo(
                    frameMargin + frameW * 1.2f, frameY + frameH + 34f,
                    frameMargin + frameW * 1.8f, frameY + frameH - 6f,
                    frameMargin * 3 + frameW * 2.5f, frameY + frameH + 20f
                )
            }

            drawPath(
                path = trajectoryPath,
                color = ElectricViolet.copy(alpha = 0.85f),
                style = Stroke(width = 2.5f)
            )

            // Trajectory target dot
            val dotX = frameMargin + (w - frameMargin * 2) * scanOffset
            val dotY = frameY + frameH + 18f + (kotlin.math.sin(scanOffset * 6.28f) * 12f).toFloat()
            drawCircle(
                color = ElectricViolet,
                radius = 5.5f,
                center = Offset(dotX, dotY)
            )
            drawCircle(
                color = NeonCyan,
                radius = 2.5f,
                center = Offset(dotX, dotY)
            )

            // 4. Prompt Synthesis Waveform Stream along bottom
            val waveY = h - 22f
            val wavePath = Path()
            wavePath.moveTo(0f, waveY)
            var wx = 0f
            while (wx <= w) {
                val amp = 9f + 6f * kotlin.math.sin(wx * 0.05f + wavePhase).toFloat()
                val wy = waveY + kotlin.math.sin(wx * 0.07f + wavePhase).toFloat() * amp
                wavePath.lineTo(wx, wy)
                wx += 6f
            }

            drawPath(
                path = wavePath,
                brush = Brush.horizontalGradient(
                    listOf(NeonCyan, ElectricViolet, Color(0xFFF43F5E), NeonCyan)
                ),
                style = Stroke(width = 2f)
            )

            // 5. Laser Scan Beam
            val beamX = w * scanOffset
            drawLine(
                brush = Brush.verticalGradient(
                    listOf(Color.Transparent, NeonCyan, Color.Transparent),
                    startY = 0f,
                    endY = h
                ),
                start = Offset(beamX, 0f),
                end = Offset(beamX, h),
                strokeWidth = 2.5f
            )

            // Laser glow line
            drawLine(
                color = NeonCyan.copy(alpha = 0.2f),
                start = Offset(beamX - 4f, 0f),
                end = Offset(beamX - 4f, h),
                strokeWidth = 8f
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Visualizer Status & Prompt Tokens Output Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Default.Psychology,
                contentDescription = null,
                tint = NeonCyan,
                modifier = Modifier.size(15.dp)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = "Live Prompt Reconstruction:",
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color = TextPrimary
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = "[Dolly In, 24mm] Lone trenchcoat figure in rain...",
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                color = NeonCyan,
                maxLines = 1
            )
        }
    }
}
