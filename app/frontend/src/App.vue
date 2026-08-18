<script setup lang="ts">
import { ref, onMounted } from "vue";
import ChatInput from "./components/ChatInput.vue";
import TourContent from "./components/TourContent.vue";
import TourLibrary from "./components/TourLibrary.vue";
import TourMap from "./components/TourMap.vue";
import { useChat } from "./composables/useChat";
import { type Tour, fetchTourDetail } from "./api";
import { t, type Lang } from "./i18n";

// Chat state from composable
const {
  tourMarkdown,
  gpxContent,
  isLoading,
  errorMessage,
  statusMessages,
  mapData,
  hasMapData,
  sendMessage,
  loadTour,
  clearError,
  sessionId,
} = useChat();

// UI state
const language = ref<Lang>("de");
const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null);
const showMap = ref(false);
const selectedTourId = ref<string | null>(null);

/**
 * Generate a unique session ID (UUID v4).
 */
function generateSessionId(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Initialize session and load last viewed tour if available.
 */
async function initializeSession() {
  let sid = localStorage.getItem("session_id");
  if (!sid) {
    sid = generateSessionId();
    localStorage.setItem("session_id", sid);
  }
  sessionId.value = sid;

  // Attempt to load last viewed tour
  try {
    const response = await fetch(`/api/sessions/${sid}/last-viewed`);
    if (!response.ok) return;

    const data = await response.json();
    if (data.tour) {
      // Load tour details and display
      try {
        const tour = await fetchTourDetail(data.tour.tour_type, data.tour.slug);
        if (tour) {
          selectedTourId.value = data.tour.id;
          await loadTour({
            id: data.tour.id,
            tour_type: data.tour.tour_type,
            slug: data.tour.slug,
          } as Tour);
        }
      } catch {
        // Silently fail if unable to load tour
      }
    }
  } catch {
    // Silently fail if unable to fetch last viewed tour
  }
}

onMounted(() => {
  initializeSession();
});

async function handleSend(message: string) {
  await sendMessage(message, language.value);
  chatInputRef.value?.clear();
}

async function handleSelectTour(tour: Tour) {
  selectedTourId.value = tour.id;
  await loadTour(tour);
}

function handleTourDeleted() {
  // Clear current view when selected tour is deleted
  selectedTourId.value = null;
  tourMarkdown.value = "";
  gpxContent.value = "";
}
</script>

<template>
  <div class="flex h-screen">
    <!-- Tour Library Sidebar -->
    <TourLibrary
      :language="language"
      :selected-tour-id="selectedTourId"
      @select="handleSelectTour"
      @deleted="handleTourDeleted"
    />

    <!-- Main Content -->
    <div class="flex-1 flex flex-col min-h-0">
      <!-- Fixed Header + Chat Input -->
      <div class="shrink-0 bg-white border-b border-gray-200">
        <div class="max-w-7xl mx-auto px-4 py-4">
          <!-- Header -->
          <header class="mb-4 flex items-center justify-between">
            <div>
              <h1 class="text-2xl font-bold text-gray-800">Gerrit on Tour</h1>
              <p class="text-gray-600 mt-1">
                {{ t("subtitle", language) }}
              </p>
            </div>
            <div class="flex items-center gap-1 bg-gray-100 rounded-md p-0.5">
              <button
                :class="[
                  'px-2 py-1 text-sm rounded transition',
                  language === 'de'
                    ? 'bg-white shadow text-gray-900'
                    : 'text-gray-500 hover:text-gray-700',
                ]"
                @click="language = 'de'"
              >
                DE
              </button>
              <button
                :class="[
                  'px-2 py-1 text-sm rounded transition',
                  language === 'en'
                    ? 'bg-white shadow text-gray-900'
                    : 'text-gray-500 hover:text-gray-700',
                ]"
                @click="language = 'en'"
              >
                EN
              </button>
            </div>
          </header>

          <!-- Chat Input -->
          <ChatInput
            ref="chatInputRef"
            :is-loading="isLoading"
            :language="language"
            @send="handleSend"
          />

          <!-- Status Feed (live tool calls) -->
          <div
            v-if="isLoading && statusMessages.length > 0"
            class="mt-3 px-4 py-2 bg-blue-50 border border-blue-100 rounded-lg"
          >
            <p
              v-for="(msg, i) in statusMessages"
              :key="i"
              class="text-xs text-blue-700 font-mono truncate"
            >
              {{ msg }}
            </p>
          </div>

          <!-- Error Display -->
          <div
            v-if="errorMessage"
            class="mt-3 px-4 py-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3"
          >
            <span class="text-red-500 text-lg leading-none"
              >&#9888;&#65039;</span
            >
            <div class="flex-1">
              <p class="text-sm text-red-800">{{ errorMessage }}</p>
            </div>
            <button
              @click="clearError"
              class="text-red-400 hover:text-red-600 text-lg leading-none"
            >
              &#10005;
            </button>
          </div>
        </div>
      </div>

      <!-- Scrollable Tour Content -->
      <div class="flex-1 overflow-auto bg-gray-50">
        <div class="max-w-7xl mx-auto px-4 py-6">
          <!-- Tour Result + Map -->
          <div v-if="tourMarkdown || hasMapData">
            <!-- Map Toggle Button -->
            <div v-if="hasMapData" class="mb-4">
              <button
                @click="showMap = !showMap"
                class="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-md transition"
              >
                <span v-if="showMap">▼</span>
                <span v-else>▶</span>
                {{ showMap ? t("hideMap", language) : t("showMap", language) }}
              </button>
            </div>

            <!-- Map (collapsible, above markdown) -->
            <div
              v-if="hasMapData && showMap"
              class="mb-6 h-[450px] rounded-lg overflow-hidden shadow"
            >
              <TourMap
                :waypoints="mapData.waypoints"
                :routes="mapData.routes"
                :pois="mapData.pois"
                :elevation="mapData.elevation"
              />
            </div>

            <!-- Markdown Content -->
            <div v-if="tourMarkdown">
              <TourContent :markdown="tourMarkdown" :gpx="gpxContent" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
