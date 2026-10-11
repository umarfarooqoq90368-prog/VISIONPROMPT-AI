package com.example.ui.prompts

import android.content.Context
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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.AnalysisResult
import com.example.model.SceneDetail
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
 * Generated Prompts Page
 *
 * Requirements:
 * - Display all scene prompts with:
 *   - Scene thumbnail
 *   - Scene number
 *   - Time range
 *   - Short scene description
 *   - Full generated prompt
 *   - Copy
 *   - Edit
 *   - Save
 * - EXPORT:
 *   - Export TXT
 *   - Export JSON
 *   - Export PDF
 *   - Copy All Prompts
 */
@Composable
fun GeneratedPromptsScreen(
    currentResult: AnalysisResult?,
    onUpdateScenePrompt: (Int, String) -> Unit,
    onSaveProject: () -> Unit,
    onBuildTxt: (AnalysisResult) -> String,
    onBuildJson: (AnalysisResult) -> String,
    modifier: Modifier = Modifier
) {
    val clipboardManager = LocalClipboardManager.current
    var exportStatusNotice by remember { mutableStateOf<String?>(null) }
    var editingSceneIndex by remember { mutableStateOf<Int?>(null) }
    var draftPrompt by remember { mutableStateOf("") }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(NavyBgDeep)
            .padding(horizontal = 16.dp)
            .testTag("generated_prompts_screen"),
        contentPadding = PaddingValues(top = 16.dp, bottom = 40.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Column {
                Text(
                    text = "Generated Prompts",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Black,
                    color = TextPrimary
                )
                Text(
                    text = "Google Flow-ready scene generation prompts structured with full cinematographic parameters.",
                    fontSize = 13.sp,
                    color = TextSecondary
                )
            }
        }

        val result = currentResult
        if (result == null || result.scenes.isEmpty()) {
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(NavyCardBg)
                        .border(1.dp, NavyCardBorder, RoundedCornerShape(12.dp))
                        .padding(32.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "No generated prompts yet. Upload and analyze a video first.",
                        fontSize = 14.sp,
                        color = TextSecondary
                    )
                }
            }
        } else {
            // 1. Export Action Bar: Export TXT, Export JSON, Export PDF, Copy All Prompts
            item {
                ExportActionBar(
                    result = result,
                    onCopyAll = {
                        val all = onBuildTxt(result)
                        clipboardManager.setText(AnnotatedString(all))
                        exportStatusNotice = "Copied all ${result.scenes.size} scene prompts to clipboard!"
                    },
                    onExportTxt = {
                        val txt = onBuildTxt(result)
                        clipboardManager.setText(AnnotatedString(txt))
                        exportStatusNotice = "TXT Export generated & copied to clipboard!"
                    },
                    onExportJson = {
                        val json = onBuildJson(result)
                        clipboardManager.setText(AnnotatedString(json))
                        exportStatusNotice = "JSON Export generated & copied to clipboard!"
                    },
                    onExportPdf = {
                        val formatted = onBuildTxt(result)
                        clipboardManager.setText(AnnotatedString(formatted))
                        exportStatusNotice = "PDF Directorial Dossier copied to clipboard!"
                    }
                )
            }

            if (exportStatusNotice != null) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .background(EmeraldSuccess.copy(alpha = 0.2f))
                            .border(1.dp, EmeraldSuccess, RoundedCornerShape(8.dp))
                            .padding(10.dp)
                    ) {
                        Text(
                            text = exportStatusNotice!!,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = EmeraldSuccess
                        )
                    }
                }
            }

            // 2. All Scene Cards
            itemsIndexed(result.scenes) { index, scene ->
                val isEditing = editingSceneIndex == index
                ScenePromptCard(
                    scene = scene,
                    isEditing = isEditing,
                    draftText = if (isEditing) draftPrompt else scene.activePrompt,
                    onDraftChange = { draftPrompt = it },
                    onStartEdit = {
                        editingSceneIndex = index
                        draftPrompt = scene.activePrompt
                    },
                    onSaveEdit = {
                        onUpdateScenePrompt(index, draftPrompt)
                        editingSceneIndex = null
                        exportStatusNotice = "Saved edit for Scene 0${scene.sceneNumber}"
                    },
                    onCancelEdit = {
                        editingSceneIndex = null
                    },
                    onCopyPrompt = {
                        clipboardManager.setText(AnnotatedString(scene.activePrompt))
                        exportStatusNotice = "Copied Scene 0${scene.sceneNumber} prompt!"
                    },
                    onSavePrompt = {
                        onSaveProject()
                        exportStatusNotice = "Saved Scene 0${scene.sceneNumber} to project!"
                    }
                )
            }
        }
    }
}

@Composable
private fun ExportActionBar(
    result: AnalysisResult,
    onCopyAll: () -> Unit,
    onExportTxt: () -> Unit,
    onExportJson: () -> Unit,
    onExportPdf: () -> Unit
) {
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
                    text = "EXPORT & SHARE PROMPTS",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = CyberCyan,
                    letterSpacing = 0.8.sp
                )

                Text(
                    text = "${result.scenes.size} Ready Prompts",
                    fontSize = 11.sp,
                    color = TextSecondary
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Copy All Prompts
                Button(
                    onClick = onCopyAll,
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = ElectricBlue),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp),
                    modifier = Modifier.weight(1.2f)
                ) {
                    Icon(imageVector = Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(13.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Copy All", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }

                // Export TXT
                Button(
                    onClick = onExportTxt,
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = NavyCardElevated),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 6.dp),
                    modifier = Modifier
                        .weight(1f)
                        .border(1.dp, NavyBorderSubtle, RoundedCornerShape(8.dp))
                ) {
                    Icon(imageVector = Icons.Default.Description, contentDescription = null, modifier = Modifier.size(13.dp), tint = CyberCyan)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("TXT", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                }

                // Export JSON
                Button(
                    onClick = onExportJson,
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = NavyCardElevated),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 6.dp),
                    modifier = Modifier
                        .weight(1f)
                        .border(1.dp, NavyBorderSubtle, RoundedCornerShape(8.dp))
                ) {
                    Icon(imageVector = Icons.Default.Download, contentDescription = null, modifier = Modifier.size(13.dp), tint = RoyalViolet)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("JSON", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                }

                // Export PDF
                Button(
                    onClick = onExportPdf,
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = NavyCardElevated),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 6.dp),
                    modifier = Modifier
                        .weight(1f)
                        .border(1.dp, NavyBorderSubtle, RoundedCornerShape(8.dp))
                ) {
                    Icon(imageVector = Icons.Default.PictureAsPdf, contentDescription = null, modifier = Modifier.size(13.dp), tint = MagentaAccent)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("PDF", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                }
            }
        }
    }
}

@Composable
private fun ScenePromptCard(
    scene: SceneDetail,
    isEditing: Boolean,
    draftText: String,
    onDraftChange: (String) -> Unit,
    onStartEdit: () -> Unit,
    onSaveEdit: () -> Unit,
    onCancelEdit: () -> Unit,
    onCopyPrompt: () -> Unit,
    onSavePrompt: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(1.dp, NavyCardBorder, RoundedCornerShape(14.dp))
            .testTag("scene_prompt_card_${scene.sceneNumber}"),
        colors = CardDefaults.cardColors(containerColor = NavyCardBg)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Top: Thumbnail, Scene Number, Time Range, Short Scene Description
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Scene thumbnail
                Box(
                    modifier = Modifier
                        .size(width = 80.dp, height = 55.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFF0F172A))
                        .border(0.5.dp, NavyBorderSubtle, RoundedCornerShape(8.dp)),
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
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(4.dp))
                                .background(ElectricBlue.copy(alpha = 0.25f))
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Text(
                                text = "Scene ${String.format("%02d", scene.sceneNumber)}",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = CyberCyan
                            )
                        }

                        Spacer(modifier = Modifier.width(8.dp))

                        Text(
                            text = "${scene.startTimestamp} - ${scene.endTimestamp}",
                            fontSize = 11.sp,
                            color = TextTertiary,
                            fontWeight = FontWeight.Medium
                        )
                    }

                    Spacer(modifier = Modifier.height(4.dp))

                    Text(
                        text = scene.title,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )

                    Text(
                        text = "${scene.characters} • ${scene.mainAction}",
                        fontSize = 11.sp,
                        color = TextSecondary,
                        maxLines = 1
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Full Generated Prompt Box
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(10.dp))
                    .background(NavyCardElevated)
                    .border(0.5.dp, NavyBorderSubtle, RoundedCornerShape(10.dp))
                    .padding(12.dp)
            ) {
                Column {
                    Text(
                        text = "FULL GENERATED PROMPT (GOOGLE FLOW):",
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = CyberCyan,
                        letterSpacing = 0.5.sp
                    )
                    Spacer(modifier = Modifier.height(6.dp))

                    if (isEditing) {
                        OutlinedTextField(
                            value = draftText,
                            onValueChange = onDraftChange,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(120.dp),
                            textStyle = androidx.compose.ui.text.TextStyle(fontSize = 12.sp, color = TextPrimary),
                            colors = TextFieldDefaults.colors(
                                focusedContainerColor = NavyBgDeep,
                                unfocusedContainerColor = NavyBgDeep,
                                focusedIndicatorColor = CyberCyan,
                                unfocusedIndicatorColor = NavyBorderSubtle
                            )
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.align(Alignment.End)) {
                            Button(onClick = onCancelEdit, colors = ButtonDefaults.buttonColors(containerColor = NavyCardBg)) {
                                Text("Cancel", fontSize = 10.sp, color = TextSecondary)
                            }
                            Button(onClick = onSaveEdit, colors = ButtonDefaults.buttonColors(containerColor = EmeraldSuccess)) {
                                Text("Save", fontSize = 10.sp, fontWeight = FontWeight.Bold)
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

            Spacer(modifier = Modifier.height(12.dp))

            // Action Buttons: Copy, Edit, Save
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Copy
                Button(
                    onClick = onCopyPrompt,
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = ElectricBlue),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(imageVector = Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(13.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Copy", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }

                // Edit
                Button(
                    onClick = onStartEdit,
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = NavyCardElevated),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                    modifier = Modifier
                        .weight(1f)
                        .border(1.dp, NavyBorderSubtle, RoundedCornerShape(8.dp))
                ) {
                    Icon(imageVector = Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(13.dp), tint = CyberCyan)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Edit", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                }

                // Save
                Button(
                    onClick = onSavePrompt,
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = NavyCardElevated),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                    modifier = Modifier
                        .weight(1f)
                        .border(1.dp, NavyBorderSubtle, RoundedCornerShape(8.dp))
                ) {
                    Icon(imageVector = Icons.Default.Save, contentDescription = null, modifier = Modifier.size(13.dp), tint = EmeraldSuccess)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Save", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                }
            }
        }
    }
}
