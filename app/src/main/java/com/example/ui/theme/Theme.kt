package com.example.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val ScenePromptStudioDarkColorScheme = darkColorScheme(
    primary = ElectricBlue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFF1E3A8A),
    onPrimaryContainer = Color(0xFFBFDBFE),
    secondary = RoyalViolet,
    onSecondary = Color.White,
    secondaryContainer = Color(0xFF4C1D95),
    onSecondaryContainer = Color(0xFFDDD6FE),
    tertiary = CyberCyan,
    onTertiary = Color(0xFF042F2E),
    background = NavyBgDeep,
    onBackground = TextPrimary,
    surface = NavyBgSurface,
    onSurface = TextPrimary,
    surfaceVariant = NavyCardBg,
    onSurfaceVariant = TextSecondary,
    outline = NavyCardBorder,
    outlineVariant = NavyBorderSubtle
)

@Composable
fun VisionPromptTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = ScenePromptStudioDarkColorScheme,
        typography = Typography,
        content = content
    )
}
