<script setup lang="ts">
import { Compass, Moon, Search, Sun, X } from "@lucide/vue";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { fetchSessions, fetchTours, type Session, type Tour } from "../api";
import { t, type Lang } from "../i18n";

const props = defineProps<{
  isOpen: boolean;
  language: Lang;
  isDark: boolean;
}>();

const emit = defineEmits<{
  close: [];
  selectTour: [tour: Tour];
  selectSession: [sessionId: string];
  toggleTheme: [];
}>();

const searchQuery = ref("");
const searchInputRef = ref<HTMLInputElement | null>(null);
const tours = ref<Tour[]>([]);
const sessions = ref<Session[]>([]);
const selectedIndex = ref(0);

async function loadData() {
  try {
    const [fetchedTours, fetchedSessions] = await Promise.all([fetchTours(), fetchSessions()]);
    tours.value = fetchedTours;
    sessions.value = fetchedSessions;
  } catch {
    // Ignore load failures in palette
  }
}

watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      openPalette();
    }
  },
  { immediate: true },
);

const filteredItems = computed(() => {
  const query = searchQuery.value.toLowerCase().trim();

  const tourItems = tours.value
    .filter(
      (t) =>
        !query ||
        t.title.toLowerCase().includes(query) ||
        t.tour_type.toLowerCase().includes(query),
    )
    .slice(0, 5)
    .map((t) => ({
      id: `tour-${t.id}`,
      type: "tour" as const,
      title: t.title,
      subtitle: t.tour_type === "bike" ? "🚴 Radtour" : "🚗 Roadtrip",
      data: t,
    }));

  const sessionItems = sessions.value
    .filter(
      (s: Session) =>
        !query || s.title?.toLowerCase().includes(query) || s.id.toLowerCase().includes(query),
    )
    .slice(0, 5)
    .map((s: Session) => ({
      id: `session-${s.id}`,
      type: "session" as const,
      title: s.title || `Session ${s.id.slice(0, 8)}`,
      subtitle: s.tour_type ? `💬 ${s.tour_type}` : "💬 Chat Session",
      data: s.id,
    }));

  const actionItems = [
    {
      id: "action-theme",
      type: "action" as const,
      title: props.isDark ? "Light Mode aktivieren" : "Dark Mode aktivieren",
      subtitle: "🎨 Design anpassen",
      action: () => emit("toggleTheme"),
    },
  ];

  return [...tourItems, ...sessionItems, ...actionItems];
});

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    if (props.isOpen) {
      emit("close");
    } else {
      openPalette();
    }
    return;
  }

  if (!props.isOpen) return;

  if (e.key === "Escape") {
    emit("close");
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    if (filteredItems.value.length > 0) {
      selectedIndex.value = (selectedIndex.value + 1) % filteredItems.value.length;
    }
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    if (filteredItems.value.length > 0) {
      selectedIndex.value =
        (selectedIndex.value - 1 + filteredItems.value.length) % filteredItems.value.length;
    }
  } else if (e.key === "Enter") {
    e.preventDefault();
    executeSelectedItem();
  }
}

function executeSelectedItem() {
  const item = filteredItems.value[selectedIndex.value];
  if (!item) return;

  if (item.type === "tour") {
    emit("selectTour", item.data);
  } else if (item.type === "session") {
    emit("selectSession", item.data);
  } else if (item.type === "action") {
    item.action();
  }
  emit("close");
}

function openPalette() {
  searchQuery.value = "";
  selectedIndex.value = 0;
  loadData();
  nextTick(() => {
    searchInputRef.value?.focus();
  });
}

onMounted(() => {
  window.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-900/60 dark:bg-black/70 backdrop-blur-xs animate-in fade-in duration-150"
      @click.self="emit('close')"
    >
      <div
        class="w-full max-w-xl bg-monokai-light-card dark:bg-monokai-panel border border-monokai-light-border dark:border-monokai-border rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150"
      >
        <!-- Search Input Header -->
        <div
          class="flex items-center px-4 py-3.5 border-b border-monokai-light-border dark:border-monokai-border gap-3"
        >
          <Search :size="18" class="text-monokai-light-muted dark:text-monokai-muted shrink-0" />
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            class="w-full bg-transparent border-0 text-sm font-medium text-monokai-light-fg dark:text-monokai-fg placeholder-monokai-light-muted dark:placeholder-monokai-muted focus:outline-none"
            :placeholder="
              language === 'de'
                ? 'Touren, Sessions oder Aktionen suchen...'
                : 'Search tours, sessions or actions...'
            "
          />
          <kbd
            class="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono font-semibold text-monokai-light-muted dark:text-monokai-muted bg-monokai-light-panel dark:bg-monokai-card rounded-md border border-monokai-light-border dark:border-monokai-border"
          >
            ESC
          </kbd>
          <button
            type="button"
            class="p-1 rounded-lg text-monokai-light-muted dark:text-monokai-muted hover:text-monokai-light-fg dark:hover:text-monokai-fg"
            @click="emit('close')"
          >
            <X :size="18" />
          </button>
        </div>

        <!-- Results List -->
        <div class="max-h-80 overflow-y-auto p-2 space-y-1">
          <div
            v-if="filteredItems.length === 0"
            class="px-4 py-8 text-center text-xs text-monokai-light-muted dark:text-monokai-muted"
          >
            Keine Ergebnisse gefunden.
          </div>
          <button
            v-for="(item, index) in filteredItems"
            :key="item.id"
            type="button"
            class="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-left transition text-xs font-medium cursor-pointer"
            :class="
              index === selectedIndex
                ? 'bg-blue-600/10 dark:bg-monokai-cyan/20 text-blue-700 dark:text-monokai-cyan font-semibold'
                : 'text-monokai-light-fg dark:text-monokai-fg hover:bg-monokai-light-panel dark:hover:bg-monokai-card'
            "
            @click="
              selectedIndex = index;
              executeSelectedItem();
            "
          >
            <div class="flex items-center gap-3">
              <span
                class="flex h-7 w-7 items-center justify-center rounded-lg bg-monokai-light-panel dark:bg-monokai-card shrink-0"
              >
                <Compass
                  v-if="item.type === 'tour'"
                  :size="14"
                  class="text-blue-600 dark:text-monokai-cyan"
                />
                <Search
                  v-else-if="item.type === 'session'"
                  :size="14"
                  class="text-emerald-600 dark:text-monokai-green"
                />
                <Sun v-else-if="props.isDark" :size="14" class="text-amber-500" />
                <Moon v-else :size="14" class="text-purple-600" />
              </span>
              <div>
                <p class="font-bold text-monokai-light-fg dark:text-monokai-fg leading-tight">
                  {{ item.title }}
                </p>
                <p class="text-[11px] text-monokai-light-muted dark:text-monokai-muted mt-0.5">
                  {{ item.subtitle }}
                </p>
              </div>
            </div>
            <kbd
              v-if="index === selectedIndex"
              class="px-2 py-0.5 text-[10px] font-mono text-blue-600 dark:text-monokai-cyan"
            >
              ↵ Enter
            </kbd>
          </button>
        </div>

        <!-- Footer -->
        <div
          class="px-4 py-2 border-t border-monokai-light-border dark:border-monokai-border bg-monokai-light-panel/50 dark:bg-monokai-bg/40 flex items-center justify-between text-[11px] text-monokai-light-muted dark:text-monokai-muted"
        >
          <span><kbd class="font-bold">↑↓</kbd> Navigieren</span>
          <span><kbd class="font-bold">↵</kbd> Auswählen</span>
          <span><kbd class="font-bold">ESC</kbd> Schließen</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>
