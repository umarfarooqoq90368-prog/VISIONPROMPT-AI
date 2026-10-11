package com.example.ui.landing

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
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
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material.icons.filled.FindInPage
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.SmartDisplay
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Timeline
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.SampleVideoPreset
import com.example.ui.components.HeroVisualizer
import com.example.ui.theme.DarkBgMain
import com.example.ui.theme.DarkBgSecondary
import com.example.ui.theme.DarkCardBg
import com.example.ui.theme.DarkCardBorder
import com.example.ui.theme.DarkSurfaceElevated
import com.example.ui.theme.ElectricViolet
import com.example.ui.theme.NeonCyan
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.ui.theme.TextTertiary
import com.example.viewmodel.AppDestination
import kotlinx.coroutines.launch

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun LandingScreen(
    onNavigate: (AppDestination) -> Unit,
    onAnalyzeUri: (Uri) -> Unit,
    onAnalyzePreset: (SampleVideoPreset) -> Unit,
    presets: List<SampleVideoPreset>,
    modifier: Modifier = Modifier
) {
    val scrollState = rememberScrollState()
    val scope = rememberCoroutineScope()

    // Android Zero-permission Photo/Video Picker
    val videoPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri != null) {
            onAnalyzeUri(uri)
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(DarkBgMain)
            .verticalScroll(scrollState)
            .padding(bottom = 32.dp)
            .testTag("landing_screen_container")
    ) {
        // ---------------- HERO SECTION ----------------
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Pill tag
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(20.dp))
                    .background(DarkCardBg)
                    .border(1.dp, NeonCyan.copy(alpha = 0.5f), RoundedCornerShape(20.dp))
                    .padding(horizontal = 14.dp, vertical = 6.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.AutoAwesome,
                        contentDescription = null,
                        tint = NeonCyan,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "NEXT-GEN VIDEO REVERSE-ENGINEERING",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.2.sp,
                        color = NeonCyan
                    )
                }
            }

            Spacer(modifier = Modifier.height(18.dp))

            // Headline
            Text(
                text = "Turn Any Video Into a Production-Ready AI Prompt.",
                fontSize = 28.sp,
                fontWeight = FontWeight.Black,
                color = TextPrimary,
                textAlign = TextAlign.Center,
                lineHeight = 36.sp,
                modifier = Modifier.testTag("hero_headline")
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Subtitle
            Text(
                text = "Deconstruct scenes, camera trajectories, cinematic lighting, and physical actions into precise, structured prompts for Runway Gen-3, OpenAI Sora, Luma Dream Machine, and Pika.",
                fontSize = 14.sp,
                color = TextSecondary,
                textAlign = TextAlign.Center,
                lineHeight = 22.sp
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Primary & Secondary CTAs
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Button(
                    onClick = {
                        videoPicker.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly)
                        )
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = NeonCyan),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .weight(1f)
                        .height(48.dp)
                        .testTag("cta_analyze_video_button")
                ) {
                    Icon(
                        imageVector = Icons.Default.CloudUpload,
                        contentDescription = null,
                        tint = Color(0xFF03141F),
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Upload Video",
                        color = Color(0xFF03141F),
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                }

                OutlinedButton(
                    onClick = {
                        scope.launch {
                            // Scroll down to features
                            scrollState.animateScrollTo(900)
                        }
                    },
                    shape = RoundedCornerShape(12.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Brush.linearGradient(listOf(DarkCardBorder, ElectricViolet))),
                    modifier = Modifier
                        .weight(1f)
                        .height(48.dp)
                        .testTag("cta_explore_features_button")
                ) {
                    Text(
                        text = "Explore Features",
                        color = TextPrimary,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 14.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Video Upload Drag & Drop Zone Card
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(DarkCardBg)
                    .border(
                        width = 1.5.dp,
                        brush = Brush.horizontalGradient(listOf(NeonCyan.copy(alpha = 0.6f), ElectricViolet.copy(alpha = 0.6f))),
                        shape = RoundedCornerShape(16.dp)
                    )
                    .clickable {
                        videoPicker.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly)
                        )
                    }
                    .padding(20.dp)
                    .testTag("upload_dropzone_card"),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        modifier = Modifier
                            .size(54.dp)
                            .clip(CircleShape)
                            .background(DarkSurfaceElevated),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.CloudUpload,
                            contentDescription = "Upload icon",
                            tint = NeonCyan,
                            modifier = Modifier.size(28.dp)
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = "Tap to Select Video from Device",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )

                    Spacer(modifier = Modifier.height(4.dp))

                    Text(
                        text = "Supports MP4, MOV, MKV, WEBM (up to 500 MB)",
                        fontSize = 12.sp,
                        color = TextSecondary
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Or Quick Presets Selector
            Column(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Or analyze instantly with curated cinematic clips:",
                    fontSize = 12.sp,
                    color = TextTertiary,
                    modifier = Modifier.padding(bottom = 8.dp)
                )

                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    presets.forEach { preset ->
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(DarkCardBg)
                                .border(1.dp, DarkCardBorder, RoundedCornerShape(8.dp))
                                .clickable { onAnalyzePreset(preset) }
                                .padding(horizontal = 10.dp, vertical = 7.dp)
                                .testTag("preset_chip_${preset.id}")
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = Icons.Default.SmartDisplay,
                                    contentDescription = null,
                                    tint = NeonCyan,
                                    modifier = Modifier.size(14.dp)
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = preset.title,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = TextPrimary
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = preset.durationText,
                                    fontSize = 10.sp,
                                    color = TextSecondary
                                )
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(28.dp))

            // Animated Visualizer
            HeroVisualizer()
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ---------------- FEATURES SECTION (EXACTLY FOUR MAIN CARDS) ----------------
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(DarkBgSecondary)
                .padding(horizontal = 20.dp, vertical = 32.dp)
                .testTag("features_section")
        ) {
            Text(
                text = "CORE CAPABILITIES",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = ElectricViolet,
                letterSpacing = 1.2.sp
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "Engineered for Film Directors & AI Prompt Artists",
                fontSize = 22.sp,
                fontWeight = FontWeight.Black,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Four dedicated neural vision layers break down your video from pixel-level frame analysis into production prompt directives.",
                fontSize = 13.sp,
                color = TextSecondary,
                lineHeight = 20.sp
            )

            Spacer(modifier = Modifier.height(20.dp))

            // Feature Card 1: Advanced Scene Detection
            FeatureCard(
                index = "01",
                title = "Advanced Scene Detection",
                description = "Automated multi-shot boundary cut recognition, timestamp indexing, and 4K keyframe extraction that indexes distinct cinematic cuts.",
                icon = Icons.Default.Movie,
                accentColor = NeonCyan,
                tag = "feature_card_scene_detection"
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Feature Card 2: Camera Movement Analysis
            FeatureCard(
                index = "02",
                title = "Camera Movement Analysis",
                description = "Dynamic optical flow tracking of pans, tilts, dollies, pedestal crane shots, rolls, drone trajectories, and focal length depth shifts.",
                icon = Icons.Default.CameraAlt,
                accentColor = ElectricViolet,
                tag = "feature_card_camera_movement"
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Feature Card 3: Action and Object Recognition
            FeatureCard(
                index = "03",
                title = "Action and Object Recognition",
                description = "Deep visual understanding of primary subjects, spatial choreography, environmental physics, and kinetic interactions across time.",
                icon = Icons.Default.Visibility,
                accentColor = Color(0xFFF43F5E),
                tag = "feature_card_action_recognition"
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Feature Card 4: AI Video Prompt Generation
            FeatureCard(
                index = "04",
                title = "AI Video Prompt Generation",
                description = "Synthesizes structured, production-ready prompts tailored with native directorial syntax for Runway Gen-3, OpenAI Sora, Luma Dream Machine, and Pika.",
                icon = Icons.Default.Psychology,
                accentColor = Color(0xFFF59E0B),
                tag = "feature_card_prompt_generation"
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        // ---------------- WORKFLOW SECTION (EXACTLY 6 STEPS) ----------------
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 16.dp)
                .testTag("workflow_section")
        ) {
            Text(
                text = "DIRECTORIAL PIPELINE",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = NeonCyan,
                letterSpacing = 1.2.sp
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "How VisionPrompt Deconstructs Video",
                fontSize = 22.sp,
                fontWeight = FontWeight.Black,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Six systematic stages convert visual motion into executable text prompts.",
                fontSize = 13.sp,
                color = TextSecondary
            )

            Spacer(modifier = Modifier.height(20.dp))

            val steps = listOf(
                Pair("1. Upload Video", "Select local MP4, MOV, or preset video clips with automatic format and resolution validation."),
                Pair("2. Analyze Scenes", "Computer vision scans temporal cuts, duration boundaries, and extracts sharp reference frames."),
                Pair("3. Understand Visual Details", "Decomposes foreground subjects, background sets, volumetric lighting angles, and color swatches."),
                Pair("4. Reconstruct the Prompt", "Synthesizes directorial language with motion constraints and exact camera velocities."),
                Pair("5. Review Results", "Inspect scene-by-scene timeline breakdown, edit prompt fragments, and inspect negative prompts."),
                Pair("6. Export Results", "Copy directly to clipboard or export formatted JSON, TXT, and Markdown to external applications.")
            )

            steps.forEachIndexed { i, step ->
                WorkflowStepRow(
                    stepNumber = i + 1,
                    title = step.first,
                    description = step.second
                )
                if (i < steps.size - 1) {
                    Spacer(modifier = Modifier.height(14.dp))
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // ---------------- PRICING SECTION ----------------
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(DarkBgSecondary)
                .padding(horizontal = 20.dp, vertical = 32.dp)
                .testTag("pricing_section")
        ) {
            Text(
                text = "PROPOSED PLANS",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = ElectricViolet,
                letterSpacing = 1.2.sp
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "Transparent SaaS Tiers",
                fontSize = 22.sp,
                fontWeight = FontWeight.Black,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Proposed commercial tiers. In AI Studio, configure GEMINI_API_KEY in the Secrets panel for live multimodal analysis.",
                fontSize = 12.sp,
                color = TextSecondary,
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(20.dp))

            // Starter / Free Explorer
            PricingPlanCard(
                name = "Explorer Plan",
                price = "Free Demo",
                badge = "Included",
                features = listOf(
                    "VisionPrompt Neural Scene Engine",
                    "Multi-scene timeline & keyframe extraction",
                    "Full prompt generation for Sora & Runway",
                    "Local device export (JSON / TXT)",
                    "3 Saved History projects"
                ),
                isPopular = false,
                buttonText = "Use Current Tier",
                onClick = { onNavigate(AppDestination.WORKSPACE) }
            )

            Spacer(modifier = Modifier.height(14.dp))

            // Pro Studio
            PricingPlanCard(
                name = "Pro Studio",
                price = "$29 / mo",
                badge = "Proposed Tier",
                features = listOf(
                    "Direct Gemini 2.5 / 3.5 Vision AI Integration",
                    "High-resolution 4K keyframe inspection",
                    "Custom negative prompt tuning",
                    "Camera trajectory vectors & 3D speed metrics",
                    "Unlimited saved projects and batch export"
                ),
                isPopular = true,
                buttonText = "Configure API Key",
                onClick = { onNavigate(AppDestination.SETTINGS) }
            )

            Spacer(modifier = Modifier.height(14.dp))

            // Production Enterprise
            PricingPlanCard(
                name = "Production Enterprise",
                price = "$99 / mo",
                badge = "Proposed Tier",
                features = listOf(
                    "All Pro Studio capabilities",
                    "Custom LoRA & fine-tuned prompt syntax rules",
                    "Automated batch processing pipeline",
                    "Webhook integrations for cloud rendering",
                    "Dedicated prompt engineering support"
                ),
                isPopular = false,
                buttonText = "Enterprise Overview",
                onClick = { onNavigate(AppDestination.SETTINGS) }
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        // ---------------- FOOTER SECTION ----------------
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 16.dp)
                .testTag("footer_section")
        ) {
            HorizontalDivider(color = DarkCardBorder)

            Spacer(modifier = Modifier.height(18.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "VISIONPROMPT AI",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    color = NeonCyan
                )

                Text(
                    text = "v1.0.4 Android Production",
                    fontSize = 11.sp,
                    color = TextTertiary
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = "Directorial reverse-engineering suite for video-to-prompt reconstruction. Formatted specifically for Runway Gen-3 Alpha, OpenAI Sora, Luma Dream Machine, and Pika 2.0.",
                fontSize = 12.sp,
                color = TextSecondary,
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text(
                    text = "Workspace",
                    fontSize = 12.sp,
                    color = NeonCyan,
                    modifier = Modifier.clickable { onNavigate(AppDestination.WORKSPACE) }
                )
                Text(
                    text = "Storyboard",
                    fontSize = 12.sp,
                    color = NeonCyan,
                    modifier = Modifier.clickable { onNavigate(AppDestination.STORYBOARD) }
                )
                Text(
                    text = "Settings & API",
                    fontSize = 12.sp,
                    color = NeonCyan,
                    modifier = Modifier.clickable { onNavigate(AppDestination.SETTINGS) }
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "© 2026 VisionPrompt AI. All rights reserved. Powered by Google AI Studio.",
                fontSize = 11.sp,
                color = TextTertiary
            )
        }
    }
}

@Composable
private fun FeatureCard(
    index: String,
    title: String,
    description: String,
    icon: ImageVector,
    accentColor: Color,
    tag: String
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(1.dp, DarkCardBorder, RoundedCornerShape(14.dp))
            .testTag(tag),
        colors = CardDefaults.cardColors(containerColor = DarkCardBg)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(RoundedCornerShape(10.dp))
                        .background(accentColor.copy(alpha = 0.15f))
                        .border(1.dp, accentColor.copy(alpha = 0.35f), RoundedCornerShape(10.dp)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = accentColor,
                        modifier = Modifier.size(22.dp)
                    )
                }

                Text(
                    text = index,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Black,
                    color = accentColor.copy(alpha = 0.8f)
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = title,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = description,
                fontSize = 13.sp,
                color = TextSecondary,
                lineHeight = 19.sp
            )
        }
    }
}

@Composable
private fun WorkflowStepRow(
    stepNumber: Int,
    title: String,
    description: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top
    ) {
        Box(
            modifier = Modifier
                .size(32.dp)
                .clip(CircleShape)
                .background(DarkCardBg)
                .border(1.dp, NeonCyan, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "$stepNumber",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = NeonCyan
            )
        }

        Spacer(modifier = Modifier.width(14.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )
            Spacer(modifier = Modifier.height(3.dp))
            Text(
                text = description,
                fontSize = 12.sp,
                color = TextSecondary,
                lineHeight = 17.sp
            )
        }
    }
}

@Composable
private fun PricingPlanCard(
    name: String,
    price: String,
    badge: String,
    features: List<String>,
    isPopular: Boolean,
    buttonText: String,
    onClick: () -> Unit
) {
    val borderColor = if (isPopular) NeonCyan else DarkCardBorder
    val bg = if (isPopular) DarkSurfaceElevated else DarkCardBg

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(if (isPopular) 1.5.dp else 1.dp, borderColor, RoundedCornerShape(14.dp)),
        colors = CardDefaults.cardColors(containerColor = bg)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = name,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(if (isPopular) NeonCyan.copy(alpha = 0.2f) else DarkCardBg)
                        .border(0.5.dp, if (isPopular) NeonCyan else DarkCardBorder, RoundedCornerShape(6.dp))
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        text = badge,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = if (isPopular) NeonCyan else TextSecondary
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = price,
                fontSize = 24.sp,
                fontWeight = FontWeight.Black,
                color = if (isPopular) NeonCyan else TextPrimary
            )

            Spacer(modifier = Modifier.height(14.dp))

            features.forEach { feat ->
                Row(
                    modifier = Modifier.padding(vertical = 3.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = null,
                        tint = if (isPopular) NeonCyan else ElectricViolet,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = feat,
                        fontSize = 12.sp,
                        color = TextSecondary
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = onClick,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isPopular) NeonCyan else DarkCardBg
                ),
                border = if (!isPopular) androidx.compose.foundation.BorderStroke(1.dp, DarkCardBorder) else null,
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = buttonText,
                    color = if (isPopular) Color(0xFF070A12) else TextPrimary,
                    fontWeight = FontWeight.Bold,
                    fontSize = 13.sp
                )
            }
        }
    }
}
