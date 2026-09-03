<script setup lang="ts">
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  Map,
  Save,
  Sparkles,
  WifiOff,
  X,
} from "@lucide/vue";
import { computed, ref } from "vue";
import { type Tour } from "./api";
import AppHeader from "./components/AppHeader.vue";
import ChatInput from "./components/ChatInput.vue";
import CommandPalette from "./components/CommandPalette.vue";
import TourContent from "./components/TourContent.vue";
import TourLibrary from "./components/TourLibrary.vue";
import TourMap from "./components/TourMap.vue";
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
  closeSidebar,
  openCommandPalette,
  closeCommandPalette,
} = useTourSession();

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

function handleSessionDeleted(deletedId: string) {
  if (sessionId.value === deletedId) {
    resetSessionState();
  }
}

function handleSessionsCleared() {
  resetSessionState();
}
</script>

<template>
  <div
    class="flex h-screen bg-monokai-light-bg dark:bg-monokai-bg text-monokai-light-fg dark:text-monokai-fg"
  >
    <!-- #7 Mobile sidebar backdrop -->
    <Transition name="fade">
      <div
        v-if="isMobileSidebarOpen"
        class="fixed inset-0 z-30 bg-black/50 sm:hidden"
        aria-hidden="true"
        @click="closeSidebar()"
      />
    </Transition>

    <!-- Tour Library Sidebar (hidden on mobile unless open) -->
    <div
      :class="[
        'fixed inset-y-0 left-0 z-40 sm:relative sm:z-20 sm:translate-x-0 transition-transform duration-200',
        isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full sm:translate-x-0',
      ]"
    >
      <TourLibrary
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
      <!-- #10 Offline banner -->
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

      <AppHeader
        :language="language"
        :is-dark="isDark"
        :is-loading="isLoading"
        :active-session-id="sessionId"
        @reset-session="resetSessionState"
        @open-search="openCommandPalette()"
        @update:language="setLanguage"
        @toggle-theme="toggleTheme"
        @select-session="handleSelectSession"
        @sessions-cleared="handleSessionsCleared"
      />

      <div
        class="shrink-0 bg-monokai-light-card/90 dark:bg-monokai-panel/90 backdrop-blur-md border-b border-monokai-light-border dark:border-monokai-border z-10 shadow-xs"
      >
        <div class="max-w-7xl mx-auto px-4 py-3">
          <!-- Chat Input -->
          <ChatInput
            ref="chatInputRef"
            :is-loading="isLoading"
            :language="language"
            @send="handleSend"
            @cancel="cancelRequest"
          />

          <!-- Activity Feed with Expand/Collapse Toggle -->
          <div
            v-if="activityEvents.length > 0"
            class="mt-3 bg-blue-50/80 dark:bg-monokai-card/90 border border-blue-100 dark:border-monokai-border rounded-xl overflow-hidden transition-all shadow-xs"
          >
            <button
              type="button"
              class="w-full px-3.5 py-2.5 flex items-center justify-between gap-3 text-left hover:bg-blue-100/50 dark:hover:bg-monokai-panel/50 transition cursor-pointer"
              @click="setActivityFeedExpanded(!activityFeedExpanded)"
            >
              <div class="flex items-center gap-2">
                <span class="flex h-2 w-2 relative">
                  <span
                    v-if="isLoading"
                    class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"
                  ></span>
                  <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                </span>
                <span class="text-xs font-semibold text-blue-900 dark:text-monokai-fg">
                  {{
                    isLoading
                      ? language === "de"
                        ? "KI erstellt deine Route..."
                        : "AI is crafting your tour..."
                      : language === "de"
                        ? `Aktivitätsverlauf (${activityEvents.length})`
                        : `Activity History (${activityEvents.length})`
                  }}
                </span>
              </div>

              <div class="flex items-center gap-2">
                <span
                  v-if="isLoading"
                  class="text-[11px] text-blue-600 dark:text-monokai-yellow animate-pulse font-medium"
                >
                  {{ language === "de" ? "Wird verarbeitet..." : "Processing..." }}
                </span>
                <component
                  :is="activityFeedExpanded ? ChevronDown : ChevronRight"
                  :size="15"
                  class="text-blue-500 dark:text-monokai-muted"
                />
              </div>
            </button>

            <!-- Expanded Event Stream List -->
            <div
              v-show="activityFeedExpanded"
              class="px-3.5 pb-3 pt-1 border-t border-blue-100/60 dark:border-monokai-border space-y-1.5 max-h-64 overflow-y-auto scrollbar-thin"
            >
              <p
                v-for="(event, index) in activityEvents"
                :key="index"
                class="text-xs text-blue-800 dark:text-monokai-cyan font-mono flex items-start gap-2"
              >
                <span
                  class="inline-block w-1.5 h-1.5 rounded-full bg-monokai-yellow shrink-0 mt-1.5"
                ></span>
                <span class="break-words">
                  <template v-if="event.type === 'model'">
                    {{
                      t("modelCall", language, {
                        iteration: event.iteration,
                        modelId: event.modelId,
                      })
                    }}
                  </template>
                  <template v-else-if="event.type === 'tool'">
                    {{ t("toolCall", language, { name: event.name }) }}
                  </template>
                  <template v-else>{{ event.message }}</template>
                </span>
              </p>
            </div>
          </div>

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
              class="text-red-400 hover:text-red-600 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 rounded"
            >
              <X :size="18" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      <!-- Scrollable Tour Content or Welcome Hero Card -->
      <div class="flex-1 overflow-auto bg-slate-50/60 dark:bg-monokai-bg">
        <div class="max-w-7xl mx-auto px-4 py-6">
          <Transition name="fade" mode="out-in">
            <!-- Tour Result + Map -->
            <div v-if="tourMarkdown || hasMapData">
              <div
                class="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/90 bg-white/80 p-2 dark:border-monokai-border dark:bg-monokai-card/80 shadow-sm backdrop-blur-sm"
              >
                <div class="flex flex-wrap items-center gap-2.5">
                  <div
                    v-for="item in tourMetaItems"
                    :key="item.label"
                    class="inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-semibold"
                    :class="{
                      'bg-blue-50/90 dark:bg-monokai-panel/90 border-blue-100 dark:border-monokai-border text-blue-800 dark:text-monokai-cyan':
                        item.type === 'default',
                      'bg-emerald-50/90 dark:bg-monokai-panel/90 border-emerald-100 dark:border-monokai-border text-emerald-800 dark:text-monokai-green':
                        item.type === 'success',
                      'bg-amber-50/90 dark:bg-monokai-panel/90 border-amber-100 dark:border-monokai-border text-amber-800 dark:text-monokai-yellow':
                        item.type === 'warning',
                      'bg-rose-50/90 dark:bg-monokai-panel/90 border-rose-100 dark:border-monokai-border text-rose-800 dark:text-monokai-pink':
                        item.type === 'danger',
                      'bg-purple-50/90 dark:bg-monokai-panel/90 border-purple-100 dark:border-monokai-border text-purple-800 dark:text-monokai-purple':
                        item.type === 'purple',
                      'bg-sky-50/90 dark:bg-monokai-panel/90 border-sky-100 dark:border-monokai-border text-sky-800 dark:text-monokai-yellow':
                        item.type === 'sky',
                    }"
                  >
                    <span
                      class="inline-flex h-5 w-5 items-center justify-center rounded-full border border-current/25 bg-white/85 text-[10px] shadow-inner dark:bg-monokai-card/80"
                    >
                      <span
                        v-if="item.type === 'default'"
                        class="text-blue-600 dark:text-monokai-cyan"
                        >↗</span
                      >
                      <span
                        v-else-if="item.type === 'success'"
                        class="text-emerald-600 dark:text-monokai-green"
                        >↗</span
                      >
                      <span
                        v-else-if="item.type === 'warning'"
                        class="text-amber-600 dark:text-monokai-yellow"
                        >◔</span
                      >
                      <span
                        v-else-if="item.type === 'danger'"
                        class="text-rose-600 dark:text-monokai-pink"
                        >!</span
                      >
                      <span
                        v-else-if="item.type === 'purple'"
                        class="text-purple-600 dark:text-monokai-purple"
                        >◎</span
                      >
                      <span v-else class="text-sky-600 dark:text-monokai-yellow">☀</span>
                    </span>
                    <span>{{ item.label }}</span>
                  </div>
                </div>

                <div class="flex items-center gap-2">
                  <button
                    v-if="hasMapData"
                    type="button"
                    class="inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition shadow-sm cursor-pointer border bg-monokai-light-card dark:bg-monokai-card text-monokai-light-fg dark:text-monokai-fg border-monokai-light-border dark:border-monokai-border hover:bg-monokai-light-panel dark:hover:bg-monokai-panel"
                    :title="
                      isMapVisible
                        ? language === 'de'
                          ? 'Karte ausblenden'
                          : 'Hide map'
                        : language === 'de'
                          ? 'Karte anzeigen'
                          : 'Show map'
                    "
                    @click="isMapVisible = !isMapVisible"
                  >
                    <Map :size="15" aria-hidden="true" />
                    <span>{{
                      isMapVisible
                        ? language === "de"
                          ? "Karte ausblenden"
                          : "Hide Map"
                        : language === "de"
                          ? "Karte anzeigen"
                          : "Show Map"
                    }}</span>
                  </button>

                  <button
                    v-if="generatedTourType"
                    type="button"
                    :disabled="isTourSaved || isLoading"
                    class="inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition shadow-xs cursor-pointer"
                    :class="
                      isTourSaved
                        ? 'bg-emerald-50 dark:bg-monokai-card text-emerald-700 dark:text-monokai-green border border-emerald-200 dark:border-monokai-green/40'
                        : 'bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50'
                    "
                    @click="handleSaveTour"
                  >
                    <Check v-if="isTourSaved" :size="16" aria-hidden="true" />
                    <Save v-else :size="16" aria-hidden="true" />
                    <span>{{
                      isTourSaved
                        ? language === "de"
                          ? "Gespeichert"
                          : "Saved"
                        : language === "de"
                          ? "Tour speichern"
                          : "Save Tour"
                    }}</span>
                  </button>
                </div>
              </div>

              <!-- Content + Map Resizable Layout -->
              <div
                ref="splitContainerRef"
                class="flex flex-col lg:flex-row gap-4 items-stretch select-none"
              >
                <!-- Markdown Content Panel -->
                <div
                  v-if="tourMarkdown"
                  class="flex-1 min-w-0 h-[600px] lg:h-[calc(100vh-260px)]"
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
                  class="flex-1 min-w-0 rounded-2xl overflow-hidden shadow-md border border-slate-200/80 dark:border-monokai-border h-[500px] lg:h-[calc(100vh-260px)] lg:sticky lg:top-4"
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
            <Welcome
              v-else
              :language="language"
              :is-loading="isLoading"
              @select-prompt="handleSend"
            />
          </Transition>
        </div>
      </div>
    </div>

    <!-- Toast Notification Overlay (Bottom Right) — click to dismiss -->
    <div
      v-if="toasts.length > 0"
      class="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 pointer-events-none"
      role="status"
      aria-live="polite"
      aria-atomic="false"
    >
      <button
        v-for="toast in toasts"
        :key="toast.id"
        type="button"
        class="pointer-events-auto flex items-center gap-3 px-4 py-3 bg-monokai-light-card/95 dark:bg-monokai-panel/95 border border-monokai-light-border dark:border-monokai-border shadow-xl backdrop-blur-md rounded-2xl text-xs font-semibold text-monokai-light-fg dark:text-monokai-fg transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] cursor-pointer text-left"
        :aria-label="
          toast.title +
          (toast.message ? ': ' + toast.message : '') +
          ' — ' +
          (language === 'de' ? 'Klicken zum Schließen' : 'Click to dismiss')
        "
        @click="removeToast(toast.id)"
      >
        <span
          class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
          :class="{
            'bg-emerald-100 dark:bg-monokai-card text-emerald-600 dark:text-monokai-green':
              toast.type === 'success',
            'bg-blue-100 dark:bg-monokai-card text-blue-600 dark:text-monokai-cyan':
              toast.type === 'info',
            'bg-rose-100 dark:bg-monokai-card text-rose-600 dark:text-monokai-pink':
              toast.type === 'error',
          }"
        >
          <Check v-if="toast.type === 'success'" :size="14" aria-hidden="true" />
          <Sparkles v-else-if="toast.type === 'info'" :size="14" aria-hidden="true" />
          <AlertTriangle v-else :size="14" aria-hidden="true" />
        </span>
        <div class="flex-1 min-w-0">
          <p class="font-bold text-monokai-light-fg dark:text-monokai-fg">{{ toast.title }}</p>
          <p
            v-if="toast.message"
            class="text-[11px] font-normal text-monokai-light-muted dark:text-monokai-muted"
          >
            {{ toast.message }}
          </p>
        </div>
        <X
          :size="13"
          class="shrink-0 text-monokai-light-muted dark:text-monokai-muted"
          aria-hidden="true"
        />
      </button>
    </div>

    <!-- Command Palette Modal -->
    <CommandPalette
      :is-open="isCommandPaletteOpen"
      :language="language"
      :is-dark="isDark"
      @close="closeCommandPalette()"
      @select-tour="handleSelectTour"
      @select-session="handleSelectSession"
      @toggle-theme="toggleTheme"
    />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
