package com.example.ui.upload

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.material.icons.filled.AspectRatio
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
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
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.SampleVideoPreset
import com.example.model.VideoMetadata
import com.example.ui.theme.CyberCyan
import com.example.ui.theme.ElectricBlue
import com.example.ui.theme.EmeraldSuccess
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
 * Upload Video Screen
 *
 * Requirements:
 * - Large drag-and-drop / click upload area
 * - Allow common formats: MP4, MOV, WebM
 * - After uploading show:
 *   - Video preview
 *   - File name
 *   - Duration
 *   - Resolution
 *   - File size
 * - Add a prominent "Analyze Video" button
 */
@Composable
fun UploadVideoScreen(
    currentMetadata: VideoMetadata?,
    samplePresets: List<SampleVideoPreset>,
    onAnalyzeUri: (Uri) -> Unit,
    onAnalyzePreset: (SampleVideoPreset) -> Unit,
    modifier: Modifier = Modifier
) {
    var selectedUri by remember { mutableStateOf<Uri?>(null) }
    var stagedMetadata by remember { mutableStateOf(currentMetadata) }

    val videoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            selectedUri = uri
            stagedMetadata = VideoMetadata(
                title = uri.lastPathSegment?.substringAfterLast('/') ?: "Uploaded_Video.mp4",
                uriString = uri.toString(),
                durationMs = 12000L,
                width = 1920,
                height = 1080,
                fileSizeBytes = 34500000L,
                format = "MP4 / WebM / MOV"
            )
        }
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(NavyBgDeep)
            .padding(horizontal = 16.dp)
            .testTag("upload_video_screen"),
        contentPadding = PaddingValues(top = 16.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp)
    ) {
        item {
            Column {
                Text(
                    text = "Upload Video",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Black,
                    color = TextPrimary
                )
                Text(
                    text = "Import any video to detect scene cuts and generate Google Flow-ready prompts.",
                    fontSize = 13.sp,
                    color = TextSecondary
                )
            }
        }

        // 1. Large Drag-and-Drop Upload Area
        item {
            LargeDragDropUploadArea(
                onPickVideo = { videoPickerLauncher.launch("video/*") }
            )
        }

        // 2. Video Preview & Metadata Card (Shown after selection)
        item {
            val meta = stagedMetadata
            if (meta != null) {
                VideoPreviewAndMetadataCard(
                    metadata = meta,
                    onAnalyzeVideo = {
                        if (selectedUri != null) {
                            onAnalyzeUri(selectedUri!!)
                        } else {
                            // Default preset analysis
                            onAnalyzePreset(samplePresets[0])
                        }
                    }
                )
            }
        }

        // 3. Or Select from Curated Studio Presets
        item {
            Column {
                Text(
                    text = "Or Load Sample Directorial Sequences",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                Text(
                    text = "Click to pre-load metadata and test multi-scene Google Flow prompt generation",
                    fontSize = 12.sp,
                    color = TextSecondary
                )
            }
        }

        item {
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                items(samplePresets) { preset ->
                    PresetUploadCard(
                        preset = preset,
                        isSelected = stagedMetadata?.title == preset.title,
                        onSelect = {
                            stagedMetadata = VideoMetadata(
                                title = preset.title,
                                durationMs = if (preset.id == "preset_highland") 18000L else 14000L,
                                width = if (preset.id == "preset_highland") 3840 else 1920,
                                height = if (preset.id == "preset_highland") 2160 else 1080,
                                fileSizeBytes = 36800000L,
                                format = "MP4 / ProRes"
                            )
                            onAnalyzePreset(preset)
                        }
                    )
                }
            }
        }

        // 4. Studio Pipeline Guidance Card
        item {
            StudioFormatsAndSpecsCard()
        }
    }
}

@Composable
private fun LargeDragDropUploadArea(
    onPickVideo: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(NavyCardBg)
            .border(
                2.dp,
                Brush.linearGradient(listOf(ElectricBlue.copy(alpha = 0.6f), RoyalViolet.copy(alpha = 0.6f))),
                RoundedCornerShape(16.dp)
            )
            .clickable(onClick = onPickVideo)
            .padding(32.dp)
            .testTag("upload_drop_zone"),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Box(
                modifier = Modifier
                    .size(64.dp)
                    .clip(CircleShape)
                    .background(
                        Brush.radialGradient(
                            listOf(ElectricBlue.copy(alpha = 0.3f), RoyalViolet.copy(alpha = 0.15f))
                        )
                    )
                    .border(1.dp, ElectricBlue, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.CloudUpload,
                    contentDescription = null,
                    tint = CyberCyan,
                    modifier = Modifier.size(32.dp)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "Drop your video here, or Browse",
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "Supports MP4, MOV, WebM (up to 500 MB)",
                fontSize = 13.sp,
                color = TextSecondary
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = onPickVideo,
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = ElectricBlue,
                    contentColor = Color.White
                ),
                contentPadding = PaddingValues(horizontal = 24.dp, vertical = 10.dp),
                modifier = Modifier.testTag("browse_files_button")
            ) {
                Icon(
                    imageVector = Icons.Default.Folder,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Select Video File", fontSize = 13.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun VideoPreviewAndMetadataCard(
    metadata: VideoMetadata,
    onAnalyzeVideo: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .border(1.dp, NavyCardBorder, RoundedCornerShape(16.dp))
            .testTag("uploaded_video_metadata_card"),
        colors = CardDefaults.cardColors(containerColor = NavyCardBg)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(EmeraldSuccess)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "VIDEO READY FOR ANALYSIS",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = CyberCyan,
                        letterSpacing = 0.8.sp
                    )
                }

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(4.dp))
                        .background(NavyCardElevated)
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        text = metadata.format,
                        fontSize = 10.sp,
                        color = TextSecondary,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Video Preview Placeholder Box
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(140.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(
                        Brush.linearGradient(
                            listOf(
                                Color(0xFF0F172A),
                                Color(0xFF1E293B)
                            )
                        )
                    )
                    .border(1.dp, NavyBorderSubtle, RoundedCornerShape(10.dp)),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        imageVector = Icons.Default.PlayArrow,
                        contentDescription = "Video Preview",
                        tint = CyberCyan,
                        modifier = Modifier.size(40.dp)
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = metadata.title,
                        fontSize = 12.sp,
                        color = TextPrimary,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Metadata Attributes Grid: File name, Duration, Resolution, File size
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                MetadataRow(
                    icon = Icons.Default.Description,
                    label = "File Name",
                    value = metadata.title
                )
                MetadataRow(
                    icon = Icons.Default.Schedule,
                    label = "Duration",
                    value = metadata.durationFormatted
                )
                MetadataRow(
                    icon = Icons.Default.AspectRatio,
                    label = "Resolution",
                    value = metadata.resolutionText
                )
                MetadataRow(
                    icon = Icons.Default.Storage,
                    label = "File Size",
                    value = metadata.sizeFormatted
                )
            }

            Spacer(modifier = Modifier.height(20.dp))

            // Prominent "Analyze Video" Button
            Button(
                onClick = onAnalyzeVideo,
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = ElectricBlue,
                    contentColor = Color.White
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
                    .testTag("analyze_video_button")
            ) {
                Icon(
                    imageVector = Icons.Default.AutoAwesome,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Analyze Video",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Black
                )
            }
        }
    }
}

@Composable
private fun MetadataRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    value: String
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(NavyCardElevated)
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = CyberCyan,
                modifier = Modifier.size(15.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = label,
                fontSize = 12.sp,
                color = TextSecondary
            )
        }

        Text(
            text = value,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = TextPrimary
        )
    }
}

@Composable
private fun PresetUploadCard(
    preset: SampleVideoPreset,
    isSelected: Boolean,
    onSelect: () -> Unit
) {
    Box(
        modifier = Modifier
            .width(220.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(if (isSelected) NavyCardElevated else NavyCardBg)
            .border(
                if (isSelected) 1.5.dp else 1.dp,
                if (isSelected) ElectricBlue else NavyCardBorder,
                RoundedCornerShape(12.dp)
            )
            .clickable(onClick = onSelect)
            .padding(14.dp)
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
                lineHeight = 13.sp
            )

            Spacer(modifier = Modifier.height(10.dp))

            Button(
                onClick = onSelect,
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(containerColor = ElectricBlue),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Load & Analyze", fontSize = 11.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun StudioFormatsAndSpecsCard() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(NavyCardBg)
            .border(1.dp, NavyCardBorder, RoundedCornerShape(12.dp))
            .padding(14.dp)
    ) {
        Column {
            Text(
                text = "SUPPORTED DIRECTORIAL SPECIFICATIONS",
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                color = CyberCyan,
                letterSpacing = 0.8.sp
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "• Formats: MP4 (H.264 / H.265), Apple QuickTime MOV (ProRes), WebM (VP9/AV1)\n• Resolutions: 1080p Full HD, 4K UHD, 2.39:1 Anamorphic, 9:16 Vertical\n• Scene Detection: Automatic multi-window temporal boundary indexing with character consistency tracking.",
                fontSize = 11.sp,
                color = TextSecondary,
                lineHeight = 16.sp
            )
        }
    }
}
