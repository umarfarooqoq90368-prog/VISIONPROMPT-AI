package com.example.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.CyberCyan
import com.example.ui.theme.ElectricBlue
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

data class SidebarNavItem(
    val destination: AppDestination,
    val icon: ImageVector,
    val badge: String? = null
)

/**
 * Main Studio Sidebar containing the 7 requested sections:
 * - Dashboard
 * - Upload Video
 * - Scene Analysis
 * - Generated Prompts
 * - Saved Projects
 * - History
 * - Settings
 */
@Composable
fun MainStudioSidebar(
    currentDestination: AppDestination,
    onNavigate: (AppDestination) -> Unit,
    savedCount: Int = 0,
    historyCount: Int = 0,
    onCloseSidebar: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val items = listOf(
        SidebarNavItem(AppDestination.DASHBOARD, Icons.Default.Dashboard),
        SidebarNavItem(AppDestination.UPLOAD_VIDEO, Icons.Default.CloudUpload, "New"),
        SidebarNavItem(AppDestination.SCENE_ANALYSIS, Icons.Default.Movie),
        SidebarNavItem(AppDestination.GENERATED_PROMPTS, Icons.Default.Psychology, "Flow"),
        SidebarNavItem(AppDestination.SAVED_PROJECTS, Icons.Default.Bookmark, if (savedCount > 0) savedCount.toString() else null),
        SidebarNavItem(AppDestination.HISTORY, Icons.Default.History, if (historyCount > 0) historyCount.toString() else null),
        SidebarNavItem(AppDestination.SETTINGS, Icons.Default.Settings)
    )

    Column(
        modifier = modifier
            .fillMaxHeight()
            .width(260.dp)
            .background(NavyCardBg)
            .border(width = 1.dp, color = NavyCardBorder)
            .padding(16.dp)
            .testTag("main_sidebar")
    ) {
        // Studio Brand Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Animated3DLogo(size = 32.dp)
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = "SCENE PROMPT",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Black,
                        color = TextPrimary
                    )
                    Text(
                        text = "STUDIO",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = CyberCyan
                    )
                }
            }

            if (onCloseSidebar != null) {
                IconButton(
                    onClick = onCloseSidebar,
                    modifier = Modifier.size(32.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "Close Sidebar",
                        tint = TextSecondary,
                        modifier = Modifier.size(18.dp)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(18.dp))

        // Workflow Banner
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(8.dp))
                .background(Brush.horizontalGradient(listOf(ElectricBlue.copy(alpha = 0.15f), RoyalViolet.copy(alpha = 0.15f))))
                .border(0.5.dp, ElectricBlue.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                .padding(horizontal = 10.dp, vertical = 8.dp)
        ) {
            Column {
                Text(
                    text = "STUDIO PIPELINE",
                    fontSize = 9.sp,
                    fontWeight = FontWeight.Bold,
                    color = CyberCyan,
                    letterSpacing = 0.5.sp
                )
                Text(
                    text = "Video → Scene Cuts → Flow Prompts",
                    fontSize = 10.sp,
                    color = TextSecondary,
                    maxLines = 1
                )
            }
        }

        Spacer(modifier = Modifier.height(18.dp))

        Text(
            text = "MAIN NAVIGATION",
            fontSize = 10.sp,
            fontWeight = FontWeight.SemiBold,
            color = TextTertiary,
            letterSpacing = 1.sp,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp)
        )

        // Nav items list
        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            items.forEach { item ->
                val isSelected = item.destination == currentDestination
                SidebarItemRow(
                    item = item,
                    isSelected = isSelected,
                    onClick = {
                        onNavigate(item.destination)
                        onCloseSidebar?.invoke()
                    }
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Google Flow compatibility pill
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(8.dp))
                .background(NavyCardElevated)
                .border(1.dp, NavyBorderSubtle, RoundedCornerShape(8.dp))
                .padding(10.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(CyberCyan)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(
                        text = "Google Flow Mode",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                    Text(
                        text = "Scene-by-scene ready prompts",
                        fontSize = 9.sp,
                        color = TextSecondary
                    )
                }
            }
        }
    }
}

@Composable
private fun SidebarItemRow(
    item: SidebarNavItem,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    val bg = if (isSelected) {
        Brush.horizontalGradient(listOf(ElectricBlue.copy(alpha = 0.22f), RoyalViolet.copy(alpha = 0.14f)))
    } else {
        Brush.horizontalGradient(listOf(Color.Transparent, Color.Transparent))
    }
    val borderCol = if (isSelected) ElectricBlue.copy(alpha = 0.6f) else Color.Transparent

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(bg)
            .border(if (isSelected) 1.dp else 0.dp, borderCol, RoundedCornerShape(10.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp)
            .testTag("sidebar_${item.destination.name.lowercase()}"),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = item.icon,
                contentDescription = null,
                tint = if (isSelected) CyberCyan else TextSecondary,
                modifier = Modifier.size(19.dp)
            )
            Spacer(modifier = Modifier.width(12.dp))
            Text(
                text = item.destination.title,
                fontSize = 13.sp,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                color = if (isSelected) TextPrimary else TextSecondary
            )
        }

        if (item.badge != null) {
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(
                        if (isSelected) RoyalViolet else NavyCardElevated
                    )
                    .padding(horizontal = 6.dp, vertical = 2.dp)
            ) {
                Text(
                    text = item.badge,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (isSelected) Color.White else CyberCyan
                )
            }
        }
    }
}
