<script setup lang="ts">
import { AlertTriangle, WifiOff, X } from "@lucide/vue";
import { computed, ref } from "vue";
import type { Tour } from "./api";
import ActivityFeed from "./components/ActivityFeed.vue";
import AppHeader from "./components/AppHeader.vue";
import ChatInput from "./components/ChatInput.vue";
import CommandPalette from "./components/CommandPalette.vue";
import ToastContainer from "./components/ToastContainer.vue";
import TourActionBar from "./components/TourActionBar.vue";
import TourContent from "./components/TourContent.vue";
import TourLibrary from "./components/TourLibrary.vue";
import TourMap from "./components/TourMap.vue";
import Welcome from "./components/Welcome.vue";
import { useAppLayout } from "./composables/useAppLayout";
import { useAppLifecycle } from "./composables/useAppLifecycle";
import { useAppPreferences } from "./composables/useAppPreferences";
import { useChat } from "./composables/useChat";
import { useSession } from "./composables/useSession";
import { useToast } from "./composables/useToast";
import { useTourSession } from "./composables/useTourSession";
import { t } from "./i18n";
import { buildTourMetaItems } from "./utils/tourMeta";

// Chat state from composable
const {
  tourMarkdown,
  gpxContent,
  tourMetrics,
  isLoading,
  errorMessage,
  activityEvents,
  mapData,
  hasMapData,
  sendMessage,
  cancelRequest,
  loadTour,
  loadSession,
  saveCurrentTour,
  clearError,
  sessionId,
  generatedTourType,
  isTourSaved,
} = useChat();

const { toasts, removeToast } = useToast();

const tourMapRef = ref<InstanceType<typeof TourMap> | null>(null);

function handleFocusPoi(poi: { lat: number; lon: number; name: string }) {
  tourMapRef.value?.focusPoi(poi.lat, poi.lon, poi.name);
}

const { isMapVisible, splitRatio, splitContainerRef, startDragging, resetSplitRatio } =
  useAppLayout();

// ── UI state ────────────────────────────────────────────────────────────────

const { language, isDark, setLanguage, toggleTheme, updateDarkClass } = useAppPreferences();

const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null);
const {
  activityFeedExpanded,
  selectedTourId,
  libraryRefreshKey,
  isCommandPaletteOpen,
  isMobileSidebarOpen,
  setSelectedTourId,
  refreshLibrary,
  setActivityFeedExpanded,
  openSidebar,
  closeSidebar,
  openCommandPalette,
  closeCommandPalette,
} = useTourSession();

const isLibraryCollapsed = ref(localStorage.getItem("tourpilot_library_collapsed") === "true");

function handleToggleLibrary() {
  if (isMobileSidebarOpen.value) {
    closeSidebar();
  } else if (typeof window !== "undefined" && window.innerWidth < 640) {
    openSidebar();
  } else {
    isLibraryCollapsed.value = !isLibraryCollapsed.value;
    try {
      localStorage.setItem("tourpilot_library_collapsed", String(isLibraryCollapsed.value));
    } catch {
      // ignore
    }
  }
}

// ── Session / init ───────────────────────────────────────────────────────────

const { sessionId: appSessionId, restoreLastViewedTour } = useSession();

const tourMetaItems = computed(() =>
  buildTourMetaItems(tourMetrics.value, tourMarkdown.value || ""),
);

async function initializeSession() {
  await restoreLastViewedTour(async (tour) => {
    setSelectedTourId(tour.id);
    await loadTour(tour);
  });
  sessionId.value = appSessionId.value;
}

const { isOnline } = useAppLifecycle({
  onToggleMap: () => {
    isMapVisible.value = !isMapVisible.value;
  },
  onInitializeSession: async () => {
    updateDarkClass();
    await initializeSession();
  },
  onEscape: () => {
    if (isMobileSidebarOpen.value) {
      closeSidebar();
    }
    if (isCommandPaletteOpen.value) {
      closeCommandPalette();
    }
  },
});

// ── Event handlers ───────────────────────────────────────────────────────────

async function handleSend(message: string) {
  setActivityFeedExpanded(true);
  closeSidebar();
  await sendMessage(message, language.value);
  chatInputRef.value?.clear();
}

async function handleSelectTour(tour: Tour) {
  setSelectedTourId(tour.id);
  closeSidebar();
  await loadTour(tour);
}

async function handleSelectSession(targetSessionId: string) {
  setSelectedTourId(null);
  await loadSession(targetSessionId);
}

async function handleSaveTour() {
  try {
    const saved = await saveCurrentTour();
    if (saved) {
      setSelectedTourId(saved.id);
      refreshLibrary();
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Failed to save tour";
  }
}

function clearCurrentTourView() {
  tourMarkdown.value = "";
  gpxContent.value = "";
  mapData.value = { waypoints: [], routes: [], pois: [], elevation: [] };
}

function resetSessionState() {
  sessionId.value = crypto.randomUUID();
  clearCurrentTourView();
  activityEvents.value = [];
  setSelectedTourId(null);
  errorMessage.value = "";
}

function handleSplitKeyboard(event: KeyboardEvent) {
  if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
    event.preventDefault();
    splitRatio.value = Math.max(20, splitRatio.value - 5);
  }

  if (event.key === "ArrowRight" || event.key === "ArrowUp") {
    event.preventDefault();
    splitRatio.value = Math.min(80, splitRatio.value + 5);
  }

  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    resetSplitRatio();
  }
}

function handleTourDeleted() {
  setSelectedTourId(null);
  clearCurrentTourView();
}

function handleSessionsCleared() {
  resetSessionState();
}
</script>

<template>
  <div
    class="flex h-screen bg-monokai-light-bg dark:bg-monokai-bg text-monokai-light-fg dark:text-monokai-fg"
  >
    <!-- Mobile sidebar backdrop -->
    <Transition name="fade">
      <div
        v-if="isMobileSidebarOpen"
        class="fixed inset-0 z-30 bg-black/50 sm:hidden"
        aria-hidden="true"
        @click="closeSidebar()"
      />
    </Transition>

    <!-- Tour Library Sidebar -->
    <div
      :class="[
        'fixed inset-y-0 left-0 z-40 sm:relative sm:z-20 sm:translate-x-0 transition-transform duration-200',
        isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full sm:translate-x-0',
      ]"
    >
      <TourLibrary
        v-model:is-collapsed="isLibraryCollapsed"
        :language="language"
        :selected-tour-id="selectedTourId"
        :refresh-key="libraryRefreshKey"
        @select="handleSelectTour"
        @deleted="handleTourDeleted"
        @close="closeSidebar()"
      />
    </div>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col min-h-0 min-w-0">
      <!-- Offline banner -->
      <div
        v-if="!isOnline"
        role="status"
        aria-live="polite"
        class="shrink-0 flex items-center justify-center gap-2 px-4 py-2 bg-amber-500 text-white text-xs font-semibold"
      >
        <WifiOff :size="14" aria-hidden="true" />
        <span>{{ language === "de" ? "Keine Internetverbindung" : "No internet connection" }}</span>
      </div>
      <div
        v-else-if="isOnline"
        style="display: none"
        role="status"
        aria-live="polite"
        aria-label="Verbindung wiederhergestellt"
      />

      <!-- App Header -->
      <AppHeader
        :language="language"
        :is-dark="isDark"
        :is-loading="isLoading"
        :active-session-id="sessionId"
        :is-library-open="!isLibraryCollapsed"
        @reset-session="resetSessionState"
        @open-search="openCommandPalette()"
        @update:language="setLanguage"
        @toggle-theme="toggleTheme"
        @select-session="handleSelectSession"
        @sessions-cleared="handleSessionsCleared"
        @toggle-library="handleToggleLibrary"
      />

      <!-- Prompt Input & Activity Feed Area -->
      <div
        class="shrink-0 bg-monokai-light-card/90 dark:bg-monokai-panel/90 backdrop-blur-md border-b border-monokai-light-border dark:border-monokai-border z-10 shadow-xs"
      >
        <div class="max-w-7xl mx-auto px-4 py-3">
          <ChatInput
            ref="chatInputRef"
            :is-loading="isLoading"
            :language="language"
            @send="handleSend"
            @cancel="cancelRequest"
          />

          <!-- Activity Feed -->
          <ActivityFeed
            :events="activityEvents"
            :is-loading="isLoading"
            :language="language"
            :is-expanded="activityFeedExpanded"
            @toggle-expanded="setActivityFeedExpanded(!activityFeedExpanded)"
          />

          <!-- Error Display -->
          <div
            v-if="errorMessage"
            role="alert"
            class="mt-3 px-4 py-3 bg-red-50 dark:bg-monokai-card border border-red-200 dark:border-monokai-pink rounded-xl flex items-start gap-3 shadow-xs"
          >
            <AlertTriangle
              :size="20"
              class="shrink-0 text-red-500 dark:text-monokai-pink mt-0.5"
              aria-hidden="true"
            />
            <div class="flex-1">
              <p class="text-sm font-medium text-red-900 dark:text-monokai-fg">
                {{ errorMessage }}
              </p>
            </div>
            <button
              @click="clearError"
              :aria-label="t('close', language)"
              :title="t('close', language)"
              class="text-red-400 hover:text-red-600 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 rounded cursor-pointer"
            >
              <X :size="18" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      <!-- Tour Content Workspace or Welcome Hero Card -->
      <div class="flex-1 min-h-0 flex flex-col bg-slate-50/60 dark:bg-monokai-bg overflow-hidden">
        <div class="max-w-7xl w-full mx-auto px-4 py-3 flex-1 min-h-0 flex flex-col">
          <Transition name="fade" mode="out-in">
            <!-- Tour Result + Map Layout -->
            <div v-if="tourMarkdown || hasMapData" class="flex-1 min-h-0 flex flex-col">
              <!-- Action & Metrics Bar -->
              <TourActionBar
                :meta-items="tourMetaItems"
                :has-map-data="hasMapData"
                :is-map-visible="isMapVisible"
                :has-generated-tour="!!generatedTourType"
                :is-tour-saved="isTourSaved"
                :is-loading="isLoading"
                :language="language"
                @toggle-map="isMapVisible = !isMapVisible"
                @save-tour="handleSaveTour"
              />

              <!-- Content + Map Resizable Split Layout -->
              <div
                ref="splitContainerRef"
                class="flex-1 min-h-0 flex flex-col lg:flex-row gap-4 items-stretch select-none"
              >
                <!-- Markdown Content Panel -->
                <div
                  v-if="tourMarkdown"
                  class="flex-1 min-w-0 h-full min-h-0 flex flex-col"
                  :style="
                    isMapVisible && hasMapData ? { flex: `0 0 ${splitRatio}%` } : { width: '100%' }
                  "
                >
                  <TourContent
                    :markdown="tourMarkdown"
                    :gpx="gpxContent"
                    :metrics="tourMetrics"
                    @focus-poi="handleFocusPoi"
                  />
                </div>

                <!-- Draggable Splitter Divider Bar (Desktop) -->
                <div
                  v-if="isMapVisible && hasMapData && tourMarkdown"
                  role="separator"
                  aria-orientation="vertical"
                  tabindex="0"
                  class="hidden lg:flex w-2 shrink-0 cursor-col-resize items-center justify-center rounded-full bg-monokai-light-border/60 dark:bg-monokai-border/60 hover:bg-blue-500 dark:hover:bg-monokai-yellow transition-colors group select-none py-12 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                  :title="
                    language === 'de'
                      ? 'Gedrückt halten zum Verschieben, Doppelklick für 50:50, Pfeile zum Anpassen'
                      : 'Hold to drag, double click for 50:50, use arrow keys to adjust'
                  "
                  @mousedown="startDragging"
                  @touchstart.passive="startDragging"
                  @dblclick="resetSplitRatio"
                  @keydown="handleSplitKeyboard"
                >
                  <div
                    class="w-1 h-8 rounded-full bg-slate-400 dark:bg-monokai-muted group-hover:bg-white transition-colors"
                  />
                </div>

                <!-- Map Panel -->
                <div
                  v-if="hasMapData && isMapVisible"
                  class="flex-1 min-w-0 rounded-2xl overflow-hidden shadow-md border border-slate-200/80 dark:border-monokai-border h-full min-h-0"
                >
                  <TourMap
                    ref="tourMapRef"
                    :waypoints="mapData.waypoints"
                    :routes="mapData.routes"
                    :pois="mapData.pois"
                    :elevation="mapData.elevation"
                    :is-dark="isDark"
                  />
                </div>
              </div>
            </div>

            <!-- Welcome Empty State -->
            <div v-else class="flex-1 overflow-y-auto">
              <Welcome :language="language" :is-loading="isLoading" @select-prompt="handleSend" />
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <!-- Toast Notifications -->
    <ToastContainer :toasts="toasts" :language="language" @dismiss="removeToast" />

    <!-- Command Palette Dialog -->
    <CommandPalette
      :is-open="isCommandPaletteOpen"
      :language="language"
      :is-dark="isDark"
      :active-session-id="sessionId"
      @close="closeCommandPalette()"
      @select-tour="handleSelectTour"
      @select-session="handleSelectSession"
    />
  </div>
</template>
