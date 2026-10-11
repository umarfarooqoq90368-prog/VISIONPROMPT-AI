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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.ui.theme.CyberCyan
import com.example.ui.theme.ElectricBlue
import com.example.ui.theme.NavyCardBg
import com.example.ui.theme.RoyalViolet
import kotlin.math.cos
import kotlin.math.sin

/**
 * Studio Logo combining a Video Play triangle + AI Sparkle / Starburst.
 * Designed with modern glowing gradient geometry for "Video to Scene Prompt Studio".
 */
@Composable
fun Animated3DLogo(
    modifier: Modifier = Modifier,
    size: Dp = 38.dp
) {
    Box(
        modifier = modifier
            .size(size)
            .clip(RoundedCornerShape(10.dp))
            .background(NavyCardBg)
            .border(
                1.dp,
                Brush.linearGradient(listOf(ElectricBlue.copy(alpha = 0.8f), RoyalViolet.copy(alpha = 0.8f))),
                RoundedCornerShape(10.dp)
            )
            .testTag("animated_3d_logo"),
        contentAlignment = Alignment.Center
    ) {
        VideoPlaySparkleLogo(size = size * 0.82f)
    }
}

@Composable
fun VideoPlaySparkleLogo(
    size: Dp,
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition(label = "logo_sparkle_anim")

    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 0.92f,
        targetValue = 1.08f,
        animationSpec = infiniteRepeatable(
            animation = tween(2200, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse_scale"
    )

    val sparkleAngle by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(6000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "sparkle_angle"
    )

    Canvas(modifier = modifier.size(size).testTag("play_sparkle_logo_canvas")) {
        val w = this.size.width
        val h = this.size.height
        val cx = w / 2f
        val cy = h / 2f

        // 1. Draw glowing Play Triangle (Video prompt core)
        val playPath = Path()
        val playRadius = (w * 0.30f) * pulseScale
        val playXOffset = -w * 0.04f

        playPath.moveTo(cx + playXOffset - playRadius * 0.7f, cy - playRadius)
        playPath.lineTo(cx + playXOffset + playRadius * 1.1f, cy)
        playPath.lineTo(cx + playXOffset - playRadius * 0.7f, cy + playRadius)
        playPath.close()

        drawPath(
            path = playPath,
            brush = Brush.linearGradient(
                colors = listOf(ElectricBlue, RoyalViolet),
                start = Offset(cx - playRadius, cy - playRadius),
                end = Offset(cx + playRadius, cy + playRadius)
            )
        )

        // 2. Draw 4-point AI Sparkle starburst at the top right apex
        val sparkCx = cx + w * 0.22f
        val sparkCy = cy - h * 0.22f
        val sparkRadius = w * 0.22f * pulseScale
        val sparkInner = sparkRadius * 0.28f

        val rad = Math.toRadians(sparkleAngle.toDouble())
        val sparkPath = Path()

        for (i in 0..7) {
            val isPeak = i % 2 == 0
            val r = if (isPeak) sparkRadius else sparkInner
            val a = rad + (i * Math.PI / 4)
            val px = sparkCx + (r * cos(a)).toFloat()
            val py = sparkCy + (r * sin(a)).toFloat()
            if (i == 0) sparkPath.moveTo(px, py) else sparkPath.lineTo(px, py)
        }
        sparkPath.close()

        drawPath(
            path = sparkPath,
            brush = Brush.radialGradient(
                colors = listOf(Color.White, CyberCyan, ElectricBlue.copy(alpha = 0.2f)),
                center = Offset(sparkCx, sparkCy),
                radius = sparkRadius * 1.2f
            )
        )

        // 3. Mini secondary sparkle in bottom left
        val miniCx = cx - w * 0.28f
        val miniCy = cy + h * 0.26f
        val miniR = w * 0.10f
        val miniInner = miniR * 0.25f
        val miniPath = Path()
        for (i in 0..7) {
            val isPeak = i % 2 == 0
            val r = if (isPeak) miniR else miniInner
            val a = -rad + (i * Math.PI / 4)
            val px = miniCx + (r * cos(a)).toFloat()
            val py = miniCy + (r * sin(a)).toFloat()
            if (i == 0) miniPath.moveTo(px, py) else miniPath.lineTo(px, py)
        }
        miniPath.close()

        drawPath(
            path = miniPath,
            brush = Brush.radialGradient(
                colors = listOf(Color.White, CyberCyan),
                center = Offset(miniCx, miniCy),
                radius = miniR
            )
        )
    }
}
