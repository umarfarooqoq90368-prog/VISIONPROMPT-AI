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
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.CyberCyan
import com.example.ui.theme.ElectricBlue
import com.example.ui.theme.NavyCardBg
import com.example.ui.theme.NavyCardBorder
import com.example.ui.theme.NavyCardElevated
import com.example.ui.theme.RoyalViolet
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.viewmodel.AppDestination
import kotlin.math.cos
import kotlin.math.sin

/**
 * Mobile-responsive bottom navigation bar for the 7 Studio sections:
 * - Dashboard, Upload Video, Scene Analysis, Generated Prompts, Saved Projects, History, Settings
 */
@Composable
fun VisionPromptBottomNavigation(
    currentDestination: AppDestination,
    onNavigate: (AppDestination) -> Unit,
    savedCount: Int = 0,
    modifier: Modifier = Modifier
) {
    val scrollState = rememberScrollState()

    val navItems = remember {
        listOf(
            AppDestination.DASHBOARD,
            AppDestination.UPLOAD_VIDEO,
            AppDestination.SCENE_ANALYSIS,
            AppDestination.GENERATED_PROMPTS,
            AppDestination.SAVED_PROJECTS,
            AppDestination.HISTORY,
            AppDestination.SETTINGS
        )
    }

    LaunchedEffect(currentDestination) {
        val selectedIdx = navItems.indexOf(currentDestination)
        if (selectedIdx != -1) {
            val approximateItemWidthPx = 180
            val targetScroll = (selectedIdx * approximateItemWidthPx - approximateItemWidthPx / 2).coerceAtLeast(0)
            scrollState.animateScrollTo(targetScroll)
        }
    }

    Surface(
        modifier = modifier
            .fillMaxWidth()
            .wrapContentHeight()
            .background(NavyCardBg)
            .border(width = 1.dp, color = NavyCardBorder)
            .navigationBarsPadding()
            .testTag("bottom_navigation_bar"),
        color = NavyCardBg,
        tonalElevation = 8.dp
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 4.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(scrollState)
                    .padding(horizontal = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                navItems.forEach { destination ->
                    val isSelected = destination == currentDestination
                    val badgeCount = if (destination == AppDestination.SAVED_PROJECTS) savedCount else 0

                    BottomNav3DItem(
                        destination = destination,
                        title = destination.title,
                        isSelected = isSelected,
                        badgeCount = badgeCount,
                        onClick = { onNavigate(destination) }
                    )
                }
            }
        }
    }
}

@Composable
private fun BottomNav3DItem(
    destination: AppDestination,
    title: String,
    isSelected: Boolean,
    badgeCount: Int,
    onClick: () -> Unit
) {
    val backgroundShape = RoundedCornerShape(10.dp)
    val itemBg = if (isSelected) NavyCardElevated else Color.Transparent
    val itemBorder = if (isSelected) {
        Brush.horizontalGradient(listOf(ElectricBlue.copy(alpha = 0.8f), RoyalViolet.copy(alpha = 0.8f)))
    } else {
        Brush.horizontalGradient(listOf(Color.Transparent, Color.Transparent))
    }

    Box(
        modifier = Modifier
            .width(72.dp)
            .clip(backgroundShape)
            .background(itemBg)
            .border(if (isSelected) 1.dp else 0.dp, itemBorder, backgroundShape)
            .clickable(onClick = onClick)
            .padding(vertical = 6.dp, horizontal = 2.dp)
            .testTag("bottom_nav_${destination.name.lowercase()}"),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            if (badgeCount > 0) {
                BadgedBox(
                    badge = {
                        Badge(
                            containerColor = RoyalViolet,
                            contentColor = Color.White
                        ) {
                            Text(
                                text = badgeCount.toString(),
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                ) {
                    Animated3DNavIcon(
                        destination = destination,
                        isSelected = isSelected,
                        size = 24.dp
                    )
                }
            } else {
                Animated3DNavIcon(
                    destination = destination,
                    isSelected = isSelected,
                    size = 24.dp
                )
            }

            Spacer(modifier = Modifier.height(3.dp))

            Text(
                text = title,
                fontSize = 9.5.sp,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                color = if (isSelected) CyberCyan else TextSecondary,
                maxLines = 1,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(2.dp))
            Box(
                modifier = Modifier
                    .size(width = if (isSelected) 14.dp else 3.dp, height = 2.dp)
                    .clip(RoundedCornerShape(1.dp))
                    .background(if (isSelected) ElectricBlue else Color.Transparent)
            )
        }
    }
}

@Composable
fun Animated3DNavIcon(
    destination: AppDestination,
    isSelected: Boolean,
    size: Dp = 24.dp,
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition(label = "3d_nav_icon_anim")

    val rotationAngle by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(if (isSelected) 3000 else 6000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "icon_rot"
    )

    Canvas(
        modifier = modifier
            .size(size)
            .testTag("icon_canvas_${destination.name.lowercase()}")
    ) {
        val cx = this.size.width / 2f
        val cy = this.size.height / 2f
        val r = this.size.minDimension * 0.40f

        val rad = Math.toRadians(rotationAngle.toDouble())
        val primaryCol = if (isSelected) CyberCyan else ElectricBlue
        val secondaryCol = if (isSelected) RoyalViolet else TextSecondary

        when (destination) {
            AppDestination.DASHBOARD -> {
                // 3D Rotating Cube / Grid
                val cosA = cos(rad).toFloat()
                val sinA = sin(rad).toFloat()
                val p1 = Offset(cx - r * 0.7f * cosA, cy - r * 0.7f)
                val p2 = Offset(cx + r * 0.7f * cosA, cy - r * 0.7f)
                val p3 = Offset(cx + r * 0.7f * cosA, cy + r * 0.7f)
                val p4 = Offset(cx - r * 0.7f * cosA, cy + r * 0.7f)

                drawLine(primaryCol, p1, p2, strokeWidth = 1.8f)
                drawLine(primaryCol, p2, p3, strokeWidth = 1.8f)
                drawLine(primaryCol, p3, p4, strokeWidth = 1.8f)
                drawLine(primaryCol, p4, p1, strokeWidth = 1.8f)
                drawCircle(secondaryCol, radius = 2f, center = Offset(cx, cy))
            }
            AppDestination.UPLOAD_VIDEO -> {
                // Cloud / Up arrow with pulsing beacon
                val pTop = Offset(cx, cy - r * 0.8f)
                val pL = Offset(cx - r * 0.6f, cy - r * 0.1f)
                val pR = Offset(cx + r * 0.6f, cy - r * 0.1f)
                drawLine(primaryCol, pTop, pL, strokeWidth = 2f)
                drawLine(primaryCol, pTop, pR, strokeWidth = 2f)
                drawLine(secondaryCol, Offset(cx, cy - r * 0.8f), Offset(cx, cy + r * 0.7f), strokeWidth = 2f)
            }
            AppDestination.SCENE_ANALYSIS -> {
                // Film strip frame + lens aperture
                drawCircle(secondaryCol, radius = r * 0.85f, style = Stroke(width = 1.4f))
                val cosA = cos(rad).toFloat()
                val sinA = sin(rad).toFloat()
                drawLine(primaryCol, Offset(cx - r * 0.6f * cosA, cy - r * 0.6f * sinA), Offset(cx + r * 0.6f * cosA, cy + r * 0.6f * sinA), strokeWidth = 2f)
                drawCircle(primaryCol, radius = 2.5f, center = Offset(cx, cy))
            }
            AppDestination.GENERATED_PROMPTS -> {
                // AI Sparkle + Play symbol
                val sparkR = r * 0.75f
                for (i in 0..3) {
                    val a = rad + (i * Math.PI / 2)
                    val px = cx + (sparkR * cos(a)).toFloat()
                    val py = cy + (sparkR * sin(a)).toFloat()
                    drawLine(primaryCol, Offset(cx, cy), Offset(px, py), strokeWidth = 1.8f)
                }
                drawCircle(secondaryCol, radius = 2f, center = Offset(cx, cy))
            }
            AppDestination.SAVED_PROJECTS -> {
                // Project bookmark card
                val path = Path()
                path.moveTo(cx - r * 0.6f, cy - r * 0.8f)
                path.lineTo(cx + r * 0.6f, cy - r * 0.8f)
                path.lineTo(cx + r * 0.6f, cy + r * 0.8f)
                path.lineTo(cx, cy + r * 0.3f)
                path.lineTo(cx - r * 0.6f, cy + r * 0.8f)
                path.close()
                drawPath(path, primaryCol, style = Stroke(width = 1.6f))
            }
            AppDestination.HISTORY -> {
                // Clock / Chronological rewind
                drawCircle(secondaryCol, radius = r * 0.8f, style = Stroke(width = 1.4f))
                val hrAngle = rad * 0.5
                val minAngle = rad * 1.5
                drawLine(primaryCol, Offset(cx, cy), Offset(cx + (r * 0.4f * cos(hrAngle)).toFloat(), cy + (r * 0.4f * sin(hrAngle)).toFloat()), strokeWidth = 1.8f)
                drawLine(primaryCol, Offset(cx, cy), Offset(cx + (r * 0.65f * cos(minAngle)).toFloat(), cy + (r * 0.65f * sin(minAngle)).toFloat()), strokeWidth = 1.6f)
            }
            AppDestination.SETTINGS -> {
                // 3D Gear / Settings polygon
                val gearSteps = 6
                for (i in 0 until gearSteps) {
                    val theta = rad + (i * (Math.PI * 2 / gearSteps))
                    val px = cx + (r * 0.8f * cos(theta)).toFloat()
                    val py = cy + (r * 0.8f * sin(theta)).toFloat()
                    drawCircle(primaryCol, radius = 2f, center = Offset(px, py))
                }
                drawCircle(secondaryCol, radius = r * 0.45f, style = Stroke(width = 1.4f))
            }
        }
    }
}
