<script setup lang="ts">
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  Columns,
  Compass,
  FileText,
  Map,
  Menu,
  Moon,
  Save,
  Search,
  Sparkles,
  Sun,
  WifiOff,
  X,
} from "@lucide/vue";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { type Tour } from "./api";
import ChatInput from "./components/ChatInput.vue";
import CommandPalette from "./components/CommandPalette.vue";
import LanguageSelector from "./components/LanguageSelector.vue";
import SessionHistory from "./components/SessionHistory.vue";
import TourContent from "./components/TourContent.vue";
import TourLibrary from "./components/TourLibrary.vue";
import TourMap from "./components/TourMap.vue";
import { useChat } from "./composables/useChat";
import { useSession } from "./composables/useSession";
import { useToast } from "./composables/useToast";
import { t, type Lang } from "./i18n";

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

const viewMode = ref<"split" | "content" | "map">("split");
const tourMapRef = ref<InstanceType<typeof TourMap> | null>(null);

function handleFocusPoi(poi: { lat: number; lon: number; name: string }) {
  tourMapRef.value?.focusPoi(poi.lat, poi.lon, poi.name);
}

// ── UI state ────────────────────────────────────────────────────────────────

// #11 Detect browser language on first visit (fall back to "de")
function detectLanguage(): Lang {
  const stored = localStorage.getItem("tourpilot_lang");
  if (stored === "de" || stored === "en") return stored;
  const browser = navigator.language.slice(0, 2).toLowerCase();
  return browser === "en" ? "en" : "de";
}

const language = ref<Lang>(detectLanguage());

// Persist language choice
function setLanguage(lang: Lang) {
  language.value = lang;
  localStorage.setItem("tourpilot_lang", lang);
}

const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null);
const showMap = ref(false);
const activityFeedExpanded = ref(true);
const selectedTourId = ref<string | null>(null);
const libraryRefreshKey = ref(0);
const isCommandPaletteOpen = ref(false);

// #7 Mobile sidebar drawer
const isMobileSidebarOpen = ref(false);

// ── Theme ────────────────────────────────────────────────────────────────────

// #1 prefers-color-scheme on first visit
function detectDark(): boolean {
  const stored = localStorage.getItem("tourpilot_theme");
  if (stored === "dark") return true;
  if (stored === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

const isDark = ref(detectDark());

function toggleTheme() {
  isDark.value = !isDark.value;
  localStorage.setItem("tourpilot_theme", isDark.value ? "dark" : "light");
  updateDarkClass();
}

function updateDarkClass() {
  document.documentElement.classList.toggle("dark", isDark.value);
}

// ── Offline detection ────────────────────────────────────────────────────────

// #10 Online / offline banner
const isOnline = ref(navigator.onLine);

function handleOnline() {
  isOnline.value = true;
}
function handleOffline() {
  isOnline.value = false;
}

// ── Session / init ───────────────────────────────────────────────────────────

const { sessionId: appSessionId, restoreLastViewedTour } = useSession();

const promptSuggestions = computed(() => [
  {
    emoji: "🚴",
    tag: language.value === "de" ? "Radtour" : "Bike Tour",
    badgeClass:
      "bg-emerald-50 dark:bg-monokai-panel text-emerald-700 dark:text-monokai-green border border-emerald-100 dark:border-monokai-border",
    title: language.value === "de" ? "Wannsee & Potsdam" : "Wannsee & Potsdam",
    prompt:
      language.value === "de"
        ? "1-Tages-Radtour am Wannsee und Potsdam mit schattigen Waldwegen und Ausflugslokalen"
        : "1-day bike tour around Wannsee and Potsdam with shaded forest trails and cozy cafes",
  },
  {
    emoji: "🚘",
    tag: language.value === "de" ? "Roadtrip" : "Roadtrip",
    badgeClass:
      "bg-indigo-50 dark:bg-monokai-panel text-indigo-700 dark:text-monokai-cyan border border-indigo-100 dark:border-monokai-border",
    title: language.value === "de" ? "Schwarzwald Panoramastraße" : "Black Forest Highway",
    prompt:
      language.value === "de"
        ? "3-Tage-Roadtrip durch den Schwarzwald mit Aussichtspunkten und Etappen"
        : "3-day road trip through the Black Forest with scenic viewpoints and daily stops",
  },
  {
    emoji: "⛰️",
    tag: language.value === "de" ? "Alpen" : "Alps",
    badgeClass:
      "bg-amber-50 dark:bg-monokai-panel text-amber-700 dark:text-monokai-yellow border border-amber-100 dark:border-monokai-border",
    title: language.value === "de" ? "Alpenpass-Erlebnis" : "Alpine Pass Experience",
    prompt:
      language.value === "de"
        ? "Anspruchsvolle Tages-Radtour in den Voralpen mit Panoramablick und Berg-Pass"
        : "Challenging day bike tour in the Alpine foothills with panoramic views and mountain passes",
  },
]);

async function initializeSession() {
  await restoreLastViewedTour(async (tour) => {
    selectedTourId.value = tour.id;
    await loadTour(tour);
  });
  sessionId.value = appSessionId.value;
}

onMounted(() => {
  updateDarkClass();
  initializeSession();
  window.addEventListener("online", handleOnline);
  window.addEventListener("offline", handleOffline);
});

onUnmounted(() => {
  window.removeEventListener("online", handleOnline);
  window.removeEventListener("offline", handleOffline);
});

// ── Event handlers ───────────────────────────────────────────────────────────

async function handleSend(message: string) {
  activityFeedExpanded.value = true;
  isMobileSidebarOpen.value = false;
  await sendMessage(message, language.value);
  chatInputRef.value?.clear();
}

async function handleSelectTour(tour: Tour) {
  selectedTourId.value = tour.id;
  isMobileSidebarOpen.value = false;
  await loadTour(tour);
}

async function handleSelectSession(targetSessionId: string) {
  selectedTourId.value = null;
  await loadSession(targetSessionId);
}

async function handleSaveTour() {
  try {
    const saved = await saveCurrentTour();
    if (saved) {
      selectedTourId.value = saved.id;
      libraryRefreshKey.value += 1;
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Failed to save tour";
  }
}

function resetSessionState() {
  sessionId.value = crypto.randomUUID();
  tourMarkdown.value = "";
  gpxContent.value = "";
  activityEvents.value = [];
  selectedTourId.value = null;
  errorMessage.value = "";
  mapData.value = { waypoints: [], routes: [], pois: [], elevation: [] };
}

function handleTourDeleted() {
  selectedTourId.value = null;
  tourMarkdown.value = "";
  gpxContent.value = "";
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
        @click="isMobileSidebarOpen = false"
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
        @close="isMobileSidebarOpen = false"
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

      <!-- Fixed Header + Chat Input (Glassmorphic) -->
      <div
        class="shrink-0 bg-monokai-light-card/90 dark:bg-monokai-panel/90 backdrop-blur-md border-b border-monokai-light-border dark:border-monokai-border z-10 shadow-xs"
      >
        <div class="max-w-7xl mx-auto px-4 py-3">
          <!-- Header -->
          <header class="mb-3 flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <!-- #7 Mobile sidebar toggle -->
              <button
                type="button"
                class="sm:hidden inline-flex h-9 w-9 items-center justify-center rounded-xl border border-monokai-light-border dark:border-monokai-border bg-monokai-light-card dark:bg-monokai-card text-monokai-light-fg dark:text-monokai-fg transition shadow-xs"
                :aria-label="language === 'de' ? 'Bibliothek öffnen' : 'Open library'"
                @click="isMobileSidebarOpen = !isMobileSidebarOpen"
              >
                <Menu :size="17" aria-hidden="true" />
              </button>

              <button
                type="button"
                class="flex items-center gap-3 text-left group cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 rounded-lg"
                title="Zur Startseite"
                aria-label="Zur Startseite"
                @click="resetSessionState"
              >
                <div
                  class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-xs group-hover:scale-105 transition-transform"
                >
                  <Compass :size="22" aria-hidden="true" />
                </div>
                <div>
                  <h1
                    class="text-xl font-bold text-monokai-light-fg dark:text-monokai-fg tracking-tight group-hover:text-blue-600 dark:group-hover:text-monokai-cyan transition"
                  >
                    Tour Pilot
                  </h1>
                  <p
                    class="text-xs text-monokai-light-muted dark:text-monokai-muted hidden sm:block"
                  >
                    {{ t("subtitle", language) }}
                  </p>
                </div>
              </button>
            </div>

            <div class="flex items-center gap-2">
              <button
                type="button"
                class="hidden sm:inline-flex items-center gap-2 h-9 px-3 text-xs font-medium rounded-xl border border-monokai-light-border dark:border-monokai-border bg-monokai-light-card dark:bg-monokai-card text-monokai-light-muted dark:text-monokai-muted hover:text-monokai-light-fg dark:hover:text-monokai-fg hover:bg-monokai-light-panel dark:hover:bg-monokai-border/50 transition cursor-pointer shadow-xs"
                title="Schnellsuche (Strg+K)"
                @click="isCommandPaletteOpen = true"
              >
                <Search :size="14" aria-hidden="true" />
                <span>{{ language === "de" ? "Suchen..." : "Search..." }}</span>
                <kbd
                  class="px-1.5 py-0.5 text-[10px] font-mono rounded-md bg-monokai-light-panel dark:bg-monokai-panel border border-monokai-light-border dark:border-monokai-border"
                >
                  ⌘K
                </kbd>
              </button>
              <SessionHistory
                :language="language"
                :is-loading="isLoading"
                :active-session-id="sessionId"
                @select="handleSelectSession"
                @deleted="handleSessionDeleted"
                @cleared="handleSessionsCleared"
              />
              <!-- #11 Language selector persists choice -->
              <LanguageSelector :model-value="language" @update:model-value="setLanguage" />
              <button
                type="button"
                class="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-monokai-light-border dark:border-monokai-border bg-monokai-light-card dark:bg-monokai-card text-monokai-light-fg dark:text-monokai-yellow hover:bg-monokai-light-panel dark:hover:bg-monokai-border/50 transition cursor-pointer shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                :title="isDark ? 'Light Mode' : 'Dark Mode'"
                :aria-label="isDark ? 'Light Mode' : 'Dark Mode'"
                @click="toggleTheme"
              >
                <Sun v-if="isDark" :size="17" aria-hidden="true" />
                <Moon v-else :size="17" aria-hidden="true" />
              </button>
            </div>
          </header>

          <!-- Chat Input -->
          <ChatInput
            ref="chatInputRef"
            :is-loading="isLoading"
            :language="language"
            @send="handleSend"
            @cancel="cancelRequest"
          />

          <!-- Activity Feed -->
          <div
            v-if="activityEvents.length > 0"
            class="mt-3 px-3.5 py-2 bg-blue-50/80 dark:bg-monokai-card/90 border border-blue-100 dark:border-monokai-border rounded-xl"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="flex h-2 w-2 relative">
                  <span
                    v-if="isLoading"
                    class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"
                  ></span>
                  <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                </span>
                <p class="text-xs font-semibold text-blue-900 dark:text-monokai-yellow">
                  {{ t("activityFeedTitle", language, { count: activityEvents.length }) }}
                </p>
              </div>
              <button
                :aria-expanded="activityFeedExpanded"
                :aria-label="
                  t(activityFeedExpanded ? 'collapseActivityFeed' : 'expandActivityFeed', language)
                "
                :title="
                  t(activityFeedExpanded ? 'collapseActivityFeed' : 'expandActivityFeed', language)
                "
                class="flex h-6 w-6 items-center justify-center rounded-lg border border-blue-200/60 dark:border-monokai-border bg-white dark:bg-monokai-panel text-blue-700 dark:text-monokai-cyan transition hover:bg-blue-100 dark:hover:bg-monokai-card focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                @click="activityFeedExpanded = !activityFeedExpanded"
              >
                <ChevronDown
                  aria-hidden="true"
                  :size="14"
                  :class="{ 'rotate-180': activityFeedExpanded }"
                />
              </button>
            </div>
            <!-- #2 aria-live so screen readers announce streaming progress -->
            <div
              v-if="activityFeedExpanded"
              aria-live="polite"
              aria-atomic="false"
              class="mt-1.5 space-y-1"
            >
              <p
                v-for="(event, index) in activityEvents"
                :key="index"
                class="text-xs text-blue-800 dark:text-monokai-cyan font-mono truncate flex items-center gap-1.5"
              >
                <span class="inline-block w-1 h-1 rounded-full bg-monokai-yellow"></span>
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
              </p>
            </div>
          </div>

          <!-- #2 Error Display — role="alert" for immediate screen reader announcement -->
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
              <!-- View Mode Controls (Desktop) -->
              <div v-if="hasMapData" class="mb-4 flex items-center justify-between gap-3">
                <div
                  class="flex items-center gap-1.5 p-1 bg-white dark:bg-monokai-card border border-monokai-light-border dark:border-monokai-border rounded-xl shadow-xs text-xs"
                >
                  <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5"
                    :class="
                      viewMode === 'split'
                        ? 'bg-blue-600 text-white shadow-xs'
                        : 'text-monokai-light-fg dark:text-monokai-fg hover:bg-slate-100 dark:hover:bg-monokai-border/40'
                    "
                    @click="viewMode = 'split'"
                  >
                    <Columns :size="14" />
                    <span>Split View</span>
                  </button>
                  <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5"
                    :class="
                      viewMode === 'content'
                        ? 'bg-blue-600 text-white shadow-xs'
                        : 'text-monokai-light-fg dark:text-monokai-fg hover:bg-slate-100 dark:hover:bg-monokai-border/40'
                    "
                    @click="viewMode = 'content'"
                  >
                    <FileText :size="14" />
                    <span>Nur Tour</span>
                  </button>
                  <button
                    type="button"
                    class="px-3 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5"
                    :class="
                      viewMode === 'map'
                        ? 'bg-blue-600 text-white shadow-xs'
                        : 'text-monokai-light-fg dark:text-monokai-fg hover:bg-slate-100 dark:hover:bg-monokai-border/40'
                    "
                    @click="viewMode = 'map'"
                  >
                    <Map :size="14" />
                    <span>Nur Karte</span>
                  </button>
                </div>
              </div>

              <!-- Content + Map Layout Grid -->
              <div
                :class="[
                  'gap-6',
                  viewMode === 'split' ? 'grid grid-cols-1 lg:grid-cols-2' : '',
                  viewMode === 'map' ? 'block' : '',
                  viewMode === 'content' ? 'block' : '',
                ]"
              >
                <!-- Map Panel -->
                <div
                  v-if="hasMapData && (viewMode === 'split' || viewMode === 'map')"
                  :class="[
                    'rounded-2xl overflow-hidden shadow-md border border-slate-200/80 dark:border-monokai-border mb-6 lg:mb-0',
                    viewMode === 'map'
                      ? 'h-[650px]'
                      : 'h-[500px] lg:h-[calc(100vh-280px)] lg:sticky lg:top-4',
                  ]"
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

                <!-- Markdown Content Panel -->
                <div
                  v-if="tourMarkdown && (viewMode === 'split' || viewMode === 'content')"
                  :class="
                    viewMode === 'split' ? 'lg:max-h-[calc(100vh-280px)] lg:overflow-y-auto' : ''
                  "
                >
                  <TourContent
                    :markdown="tourMarkdown"
                    :gpx="gpxContent"
                    :metrics="tourMetrics"
                    @focus-poi="handleFocusPoi"
                  >
                    <template #actions>
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
                    </template>
                  </TourContent>
                </div>
              </div>
            </div>

            <!-- Welcome Hero Cards (Empty State) -->
            <div v-else-if="!isLoading" class="py-10 px-4 max-w-4xl mx-auto text-center">
              <div
                class="inline-flex items-center justify-center p-3.5 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-monokai-card dark:to-monokai-panel text-blue-600 dark:text-monokai-yellow rounded-2xl mb-4 shadow-xs border border-blue-100 dark:border-monokai-border"
              >
                <Sparkles :size="28" aria-hidden="true" />
              </div>
              <h2
                class="text-2xl font-bold text-slate-800 dark:text-monokai-fg sm:text-3xl tracking-tight"
              >
                {{
                  language === "de"
                    ? "Wohin führt dein nächstes Abenteuer?"
                    : "Where is your next adventure?"
                }}
              </h2>
              <p class="mt-2 text-slate-500 dark:text-monokai-muted text-sm max-w-lg mx-auto">
                {{
                  language === "de"
                    ? "Erstelle maßgeschneiderte Radtouren und Roadtrips mit KI-Unterstützung, Routenkarten und GPX-Export."
                    : "Create tailored bike tours and road trips with AI assistance, route maps, and GPX export."
                }}
              </p>

              <div class="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
                <button
                  v-for="suggestion in promptSuggestions"
                  :key="suggestion.title"
                  type="button"
                  class="group p-4 bg-white dark:bg-monokai-card border border-monokai-light-border dark:border-monokai-border rounded-2xl hover:border-blue-500 dark:hover:border-monokai-yellow hover:shadow-md transition-all text-left flex flex-col justify-between focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                  @click="handleSend(suggestion.prompt)"
                >
                  <div>
                    <div class="flex items-center justify-between">
                      <span class="text-2xl">{{ suggestion.emoji }}</span>
                      <span
                        class="text-xs font-semibold px-2 py-0.5 rounded-full"
                        :class="suggestion.badgeClass"
                      >
                        {{ suggestion.tag }}
                      </span>
                    </div>
                    <h3
                      class="mt-3 font-semibold text-slate-800 dark:text-monokai-fg text-sm group-hover:text-blue-600 dark:group-hover:text-monokai-cyan transition"
                    >
                      {{ suggestion.title }}
                    </h3>
                    <p class="mt-1 text-xs text-slate-500 dark:text-monokai-muted line-clamp-2">
                      {{ suggestion.prompt }}
                    </p>
                  </div>
                  <div
                    class="mt-4 flex items-center text-xs font-semibold text-blue-600 dark:text-monokai-cyan opacity-0 group-hover:opacity-100 transition"
                  >
                    <span>{{ language === "de" ? "Tour planen" : "Plan tour" }}</span>
                    <ChevronRight :size="14" class="ml-1" />
                  </div>
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <!-- #9 Toast Notification Overlay (Bottom Right) — click to dismiss -->
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
      @close="isCommandPaletteOpen = false"
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
