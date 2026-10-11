package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.ui.components.MainStudioSidebar
import com.example.ui.components.VisionPromptBottomNavigation
import com.example.ui.components.VisionPromptHeader
import com.example.ui.dashboard.DashboardScreen
import com.example.ui.history.HistoryScreen
import com.example.ui.prompts.GeneratedPromptsScreen
import com.example.ui.saved.SavedProjectsScreen
import com.example.ui.scene.SceneAnalysisScreen
import com.example.ui.settings.SettingsScreen
import com.example.ui.theme.NavyBgDeep
import com.example.ui.theme.VisionPromptTheme
import com.example.ui.upload.UploadVideoScreen
import com.example.viewmodel.AppDestination
import com.example.viewmodel.VisionPromptViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: VisionPromptViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            VisionPromptTheme {
                VideoToScenePromptStudioApp(viewModel = viewModel)
            }
        }
    }
}

@Composable
fun VideoToScenePromptStudioApp(viewModel: VisionPromptViewModel) {
    val destination by viewModel.currentDestination.collectAsStateWithLifecycle()
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val metadata by viewModel.selectedMetadata.collectAsStateWithLifecycle()
    val currentResult by viewModel.currentResult.collectAsStateWithLifecycle()
    val activePlatform by viewModel.activeTargetPlatform.collectAsStateWithLifecycle()
    val activeSceneIndex by viewModel.activeSceneIndex.collectAsStateWithLifecycle()
    val savedProjects by viewModel.savedProjects.collectAsStateWithLifecycle()
    val historyProjects by viewModel.historyProjects.collectAsStateWithLifecycle()

    val snackbarHostState = remember { SnackbarHostState() }
    var isSidebarOpen by remember { mutableStateOf(false) }

    // Android back navigation: Return to DASHBOARD from sub-screens
    if (destination != AppDestination.DASHBOARD) {
        BackHandler {
            if (isSidebarOpen) {
                isSidebarOpen = false
            } else {
                viewModel.navigateTo(AppDestination.DASHBOARD)
            }
        }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = NavyBgDeep,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            VisionPromptHeader(
                onNavigate = { viewModel.navigateTo(it) },
                onMenuClick = { isSidebarOpen = !isSidebarOpen }
            )
        },
        bottomBar = {
            VisionPromptBottomNavigation(
                currentDestination = destination,
                onNavigate = { viewModel.navigateTo(it) },
                savedCount = savedProjects.size
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(NavyBgDeep)
        ) {
            // Main Destination Content
            when (destination) {
                AppDestination.DASHBOARD -> {
                    DashboardScreen(
                        currentResult = currentResult,
                        savedProjects = savedProjects,
                        historyProjects = historyProjects,
                        presets = viewModel.samplePresets,
                        onNavigate = { viewModel.navigateTo(it) },
                        onOpenProject = { viewModel.loadProject(it) },
                        onAnalyzePreset = { viewModel.analyzePreset(it) }
                    )
                }

                AppDestination.UPLOAD_VIDEO -> {
                    UploadVideoScreen(
                        currentMetadata = metadata,
                        samplePresets = viewModel.samplePresets,
                        onAnalyzeUri = { uri -> viewModel.analyzeVideoUri(uri) },
                        onAnalyzePreset = { preset -> viewModel.analyzePreset(preset) }
                    )
                }

                AppDestination.SCENE_ANALYSIS -> {
                    SceneAnalysisScreen(
                        uiState = uiState,
                        metadata = metadata,
                        currentResult = currentResult,
                        activeSceneIndex = activeSceneIndex,
                        activePlatform = activePlatform,
                        onSelectSceneIndex = { viewModel.setActiveSceneIndex(it) },
                        onUpdateScenePrompt = { idx, p -> viewModel.updateScenePrompt(idx, p) },
                        onRegenerateScene = { idx -> viewModel.regenerateScenePrompt(idx) },
                        onSaveProject = { viewModel.saveCurrentProject() },
                        onCancelAnalysis = { viewModel.cancelAnalysis() }
                    )
                }

                AppDestination.GENERATED_PROMPTS -> {
                    GeneratedPromptsScreen(
                        currentResult = currentResult,
                        onUpdateScenePrompt = { idx, p -> viewModel.updateScenePrompt(idx, p) },
                        onSaveProject = { viewModel.saveCurrentProject() },
                        onBuildTxt = { viewModel.buildAllPromptsAsTxt(it) },
                        onBuildJson = { viewModel.buildAllPromptsAsJson(it) }
                    )
                }

                AppDestination.SAVED_PROJECTS -> {
                    SavedProjectsScreen(
                        savedProjects = savedProjects,
                        onOpenProject = { viewModel.loadProject(it) },
                        onDeleteProject = { viewModel.deleteSavedProject(it) },
                        onUploadNew = { viewModel.navigateTo(AppDestination.UPLOAD_VIDEO) }
                    )
                }

                AppDestination.HISTORY -> {
                    HistoryScreen(
                        historyProjects = historyProjects,
                        onLoadProject = { viewModel.loadProject(it) },
                        onDeleteProject = { viewModel.deleteHistoryProject(it) },
                        onUploadNew = { viewModel.navigateTo(AppDestination.UPLOAD_VIDEO) }
                    )
                }

                AppDestination.SETTINGS -> {
                    SettingsScreen(
                        isGeminiConfigured = viewModel.isGeminiKeyConfigured()
                    )
                }
            }

            // Slide-out Studio Main Sidebar Overlay
            if (isSidebarOpen) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.6f))
                        .clickable { isSidebarOpen = false }
                )
            }

            AnimatedVisibility(
                visible = isSidebarOpen,
                enter = slideInHorizontally { -it } + fadeIn(),
                exit = slideOutHorizontally { -it } + fadeOut()
            ) {
                MainStudioSidebar(
                    currentDestination = destination,
                    onNavigate = {
                        viewModel.navigateTo(it)
                        isSidebarOpen = false
                    },
                    savedCount = savedProjects.size,
                    historyCount = historyProjects.size,
                    onCloseSidebar = { isSidebarOpen = false }
                )
            }
        }
    }
}
