package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.model.PromptTargetPlatform
import com.example.model.SceneDetail
import com.example.model.VideoMetadata
import com.example.service.VideoFrameExtractor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [36])
class ExampleUnitTest {
    @Test
    fun testVideoMetadataFormatting() {
        val meta = VideoMetadata(
            title = "cyberpunk_test.mp4",
            durationMs = 8400L,
            width = 1920,
            height = 1080,
            fileSizeBytes = 25000000L
        )

        assertEquals("00:08.4", meta.durationFormatted)
        assertTrue(meta.resolutionText.contains("1920x1080"))
        assertTrue(meta.sizeFormatted.contains("MB"))
    }

    @Test
    fun testPromptPlatforms() {
        val platforms = PromptTargetPlatform.values()
        assertEquals(4, platforms.size)
        assertEquals("Runway Gen-3 Alpha", PromptTargetPlatform.RUNWAY_GEN3.displayName)
        assertEquals("OpenAI Sora", PromptTargetPlatform.OPENAI_SORA.displayName)
    }

    @Test
    fun testSceneDetailDeepFields() {
        val scene = SceneDetail(
            sceneNumber = 1,
            timestampMs = 0L,
            formattedTimestamp = "00:00.0",
            durationSec = 2.8f,
            title = "Alleyway Opening",
            subjects = listOf("Courier"),
            actions = listOf("Walking"),
            cameraMovement = "Low-Angle Tracking Dolly",
            framing = "Wide 24mm Anamorphic",
            lighting = "Neon Cyan Rim",
            colorPaletteHexes = listOf("#00F0FF", "#A855F7"),
            continuityNotes = "Rain density constant",
            promptFragment = "Courier walking down alleyway",
            startTimestamp = "00:00.0",
            endTimestamp = "00:02.8",
            selfContainedScenePrompt = "Detailed 4K production prompt for alleyway scene"
        )

        assertEquals("[00:00.0 - 00:02.8]", scene.timestampRange)
        assertEquals("Detailed 4K production prompt for alleyway scene", scene.selfContainedScenePrompt)
    }

    @Test
    fun testAdaptiveSampleCount() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val extractor = VideoFrameExtractor(context)

        // With granular analysis enabled:
        val sampleCount12s = extractor.calculateAdaptiveSampleCount(12000L, isGranular = true)
        assertEquals(7, sampleCount12s)

        val sampleCount5s = extractor.calculateAdaptiveSampleCount(5000L, isGranular = true)
        assertEquals(4, sampleCount5s)

        // Standard mode:
        assertEquals(5, extractor.calculateAdaptiveSampleCount(12000L, isGranular = false))
        assertEquals(3, extractor.calculateAdaptiveSampleCount(5000L, isGranular = false))
    }

    @Test
    fun testAppDestinations() {
        val dests = com.example.viewmodel.AppDestination.values()
        assertEquals(7, dests.size)
        assertEquals("Explore", com.example.viewmodel.AppDestination.EXPLORE.title)
        assertEquals("Workspace", com.example.viewmodel.AppDestination.WORKSPACE.title)
        assertEquals("Play", com.example.viewmodel.AppDestination.PLAY.title)
        assertEquals("Store", com.example.viewmodel.AppDestination.STORE.title)
        assertEquals("Board", com.example.viewmodel.AppDestination.BOARD.title)
        assertEquals("History", com.example.viewmodel.AppDestination.HISTORY.title)
        assertEquals("Citation", com.example.viewmodel.AppDestination.CITATION.title)

        // Compatibility aliases
        assertEquals(com.example.viewmodel.AppDestination.EXPLORE, com.example.viewmodel.AppDestination.LANDING)
        assertEquals(com.example.viewmodel.AppDestination.BOARD, com.example.viewmodel.AppDestination.STORYBOARD)
        assertEquals(com.example.viewmodel.AppDestination.CITATION, com.example.viewmodel.AppDestination.SETTINGS)
    }
}
