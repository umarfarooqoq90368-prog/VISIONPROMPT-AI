package com.example.ui.store

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.LocalMall
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Star
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.SampleVideoPreset
import com.example.ui.theme.DarkBgMain
import com.example.ui.theme.DarkCardBg
import com.example.ui.theme.DarkCardBorder
import com.example.ui.theme.DarkSurfaceElevated
import com.example.ui.theme.ElectricViolet
import com.example.ui.theme.NeonCyan
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.ui.theme.TextTertiary

data class PromptTemplateItem(
    val id: String,
    val title: String,
    val category: String,
    val rating: String,
    val downloads: String,
    val cameraKinematics: String,
    val lightingMood: String,
    val fullPrompt: String,
    val accentHex: String
)

@Composable
fun PromptStoreScreen(
    samplePresets: List<SampleVideoPreset>,
    onSelectPreset: (SampleVideoPreset) -> Unit,
    onGoToWorkspace: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scrollState = rememberScrollState()
    var selectedCategory by remember { mutableStateOf("All Categories") }

    val categories = listOf("All Categories", "Sci-Fi / Neon", "Cinematic Drone", "Macro / Nature", "Kinetic Action", "Anamorphic Film")

    val storeItems = remember {
        listOf(
            PromptTemplateItem(
                id = "store_cyberpunk_neon",
                title = "Neo-Tokyo Rain Alleyway 4K",
                category = "Sci-Fi / Neon",
                rating = "4.9 ★",
                downloads = "12.4k",
                cameraKinematics = "Low-Angle Forward Tracking Dolly (0.8 m/s)",
                lightingMood = "5600K Neon Cyan & 7000K Electric Violet Rim Backlight",
                fullPrompt = "A cinematic wide low-angle tracking dolly shot in 4K capturing a lone protagonist in a matte charcoal trenchcoat walking down a rain-soaked cyberpunk alleyway. Brilliant neon cyan and electric magenta holographic signs reflect in shimmering street puddles. Steam billows from grates. Arri Alexa LF 35mm anamorphic cinematography, volumetric rim lighting, deep contrast.",
                accentHex = "#00F0FF"
            ),
            PromptTemplateItem(
                id = "store_highland_fpv",
                title = "Highland Sunrise FPV Drone",
                category = "Cinematic Drone",
                rating = "5.0 ★",
                downloads = "18.1k",
                cameraKinematics = "High-Altitude Forward FPV Glide (12 m/s)",
                lightingMood = "3200K Golden Hour Sun Flare & Emerald Mist",
                fullPrompt = "A magnificent 8K aerial cinematic drone sequence gliding smoothly across misty Scottish Highland ridges at sunrise. Warm golden morning sunlight floods across emerald hills and cascading glacial waterfalls over ancient basalt cliffs. Hasselblad medium format optical clarity, natural color grading, smooth 60fps drone kinematics.",
                accentHex = "#F59E0B"
            ),
            PromptTemplateItem(
                id = "store_abyssal_biolum",
                title = "Abyssal Bioluminescent Macro",
                category = "Macro / Nature",
                rating = "4.8 ★",
                downloads = "9.6k",
                cameraKinematics = "Macro Submersible Push-In (100mm Macro Cine)",
                lightingMood = "Self-Luminous Cyan Photophore Bioluminescence (0 lux ambient)",
                fullPrompt = "Breathtaking macro cinema shot of a translucent deep-sea siphonophore pulsating with internal neon cyan and violet bioluminescence in the pitch-black abyss. Delicate glowing tendrils trail through dark water filled with gentle floating marine snow particles. 100mm macro lens, photorealistic fluid dynamics, cinematic depth of field.",
                accentHex = "#A855F7"
            ),
            PromptTemplateItem(
                id = "store_hypercar_drift",
                title = "Formula Hypercar Sunset Drift",
                category = "Kinetic Action",
                rating = "4.9 ★",
                downloads = "15.3k",
                cameraKinematics = "Chase-Car Low-Angle High-Speed Tracking (80 km/h)",
                lightingMood = "Low Sunset Backlight & Glowing Ceramic Rotors",
                fullPrompt = "High-octane tracking shot of a midnight-blue hypercar executing a high-speed drift around an apex corner on a racetrack at sunset. Dense clouds of white tire smoke billow from the rear wheels and catch the golden sunlight. Glowing orange ceramic brake rotors, authentic suspension kinematics, shutter-synchronized motion blur, 8K RED Monstro cinema camera.",
                accentHex = "#F43F5E"
            ),
            PromptTemplateItem(
                id = "store_noir_detective",
                title = "1940s Anamorphic Chiaroscuro Noir",
                category = "Anamorphic Film",
                rating = "4.7 ★",
                downloads = "8.2k",
                cameraKinematics = "Slow Push-In Dolly with Subtle Dutch Tilt",
                lightingMood = "High-Contrast Hard Venetian Blind Shadow Pattern",
                fullPrompt = "Classic cinematic film noir sequence. A trenchcoat detective sits at a mahogany desk in a dark office illuminated only by hard moonlight casting sharp venetian blind shadows across their face. A cigarette burns in a glass ashtray, smoke rising in delicate swirls through the light beam. 35mm black-and-white Tri-X film grain, deep shadows, razor-sharp optical contrast.",
                accentHex = "#10B981"
            )
        )
    }

    val filteredItems = if (selectedCategory == "All Categories") {
        storeItems
    } else {
        storeItems.filter { it.category == selectedCategory }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(DarkBgMain)
            .verticalScroll(scrollState)
            .padding(16.dp)
            .testTag("prompt_store_screen_container")
    ) {
        // Store Header
        Column {
            Text(
                text = "PROMPT REPOSITORY & STORE",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = NeonCyan,
                letterSpacing = 1.2.sp
            )
            Text(
                text = "Curated Cinematic Prompt Presets",
                fontSize = 18.sp,
                fontWeight = FontWeight.Black,
                color = TextPrimary
            )
        }

        Spacer(modifier = Modifier.height(14.dp))

        // Categories Row
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            categories.forEach { cat ->
                val isSelected = cat == selectedCategory
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(if (isSelected) NeonCyan else DarkSurfaceElevated)
                        .border(1.dp, if (isSelected) NeonCyan else DarkCardBorder, RoundedCornerShape(20.dp))
                        .clickable { selectedCategory = cat }
                        .padding(horizontal = 14.dp, vertical = 7.dp)
                ) {
                    Text(
                        text = cat,
                        fontSize = 12.sp,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                        color = if (isSelected) Color(0xFF070A12) else TextPrimary
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Prompt Cards List
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            filteredItems.forEach { item ->
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
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier = Modifier
                                        .size(34.dp)
                                        .clip(RoundedCornerShape(8.dp))
                                        .background(Color(android.graphics.Color.parseColor(item.accentHex)).copy(alpha = 0.2f)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.AutoAwesome,
                                        contentDescription = null,
                                        tint = Color(android.graphics.Color.parseColor(item.accentHex)),
                                        modifier = Modifier.size(18.dp)
                                    )
                                }

                                Spacer(modifier = Modifier.width(10.dp))

                                Column {
                                    Text(text = item.title, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                                    Text(text = item.category, fontSize = 11.sp, color = TextTertiary)
                                }
                            }

                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(6.dp))
                                    .background(DarkSurfaceElevated)
                                    .padding(horizontal = 8.dp, vertical = 3.dp)
                            ) {
                                Text(text = item.rating, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = NeonCyan)
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        // Prompt Text Box
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp))
                                .background(DarkSurfaceElevated)
                                .padding(10.dp)
                        ) {
                            Text(
                                text = item.fullPrompt,
                                fontSize = 12.sp,
                                color = TextSecondary,
                                lineHeight = 17.sp,
                                fontFamily = FontFamily.Monospace,
                                maxLines = 4
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        // Camera and Lighting Badges
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .clip(RoundedCornerShape(6.dp))
                                    .background(DarkSurfaceElevated)
                                    .padding(6.dp)
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(imageVector = Icons.Default.CameraAlt, contentDescription = null, tint = NeonCyan, modifier = Modifier.size(12.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(text = item.cameraKinematics, fontSize = 10.sp, color = TextPrimary, maxLines = 1)
                                }
                            }

                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .clip(RoundedCornerShape(6.dp))
                                    .background(DarkSurfaceElevated)
                                    .padding(6.dp)
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(imageVector = Icons.Default.Movie, contentDescription = null, tint = ElectricViolet, modifier = Modifier.size(12.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(text = item.lightingMood, fontSize = 10.sp, color = TextPrimary, maxLines = 1)
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        // Action Buttons
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.End
                        ) {
                            Button(
                                onClick = {
                                    val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                    cm.setPrimaryClip(ClipData.newPlainText("Store Prompt", item.fullPrompt))
                                    Toast.makeText(context, "Copied prompt to clipboard", Toast.LENGTH_SHORT).show()
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = DarkSurfaceElevated),
                                border = androidx.compose.foundation.BorderStroke(1.dp, DarkCardBorder),
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier.height(34.dp)
                            ) {
                                Icon(imageVector = Icons.Default.ContentCopy, contentDescription = null, tint = NeonCyan, modifier = Modifier.size(13.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Copy Prompt", fontSize = 11.sp, color = TextPrimary)
                            }

                            Spacer(modifier = Modifier.width(8.dp))

                            Button(
                                onClick = {
                                    val matchingPreset = samplePresets.find { it.title.contains(item.title.take(6), ignoreCase = true) } ?: samplePresets.first()
                                    onSelectPreset(matchingPreset)
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = NeonCyan),
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier.height(34.dp)
                            ) {
                                Icon(imageVector = Icons.Default.Download, contentDescription = null, tint = Color(0xFF070A12), modifier = Modifier.size(13.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Load in Workspace", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF070A12))
                            }
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}
