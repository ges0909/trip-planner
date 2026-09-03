<script setup lang="ts">
import { AlertTriangle, Bike, Car, ChevronLeft, RefreshCw, Trash2 } from "@lucide/vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  deleteFromTrash,
  deleteTour,
  fetchTours,
  fetchTrash,
  restoreFromTrash,
  type Tour,
  type TrashItem,
} from "../api";
import { t, type Lang } from "../i18n";

const props = defineProps<{
  language: Lang;
  selectedTourId?: string | null;
  refreshKey?: number;
  isCollapsed?: boolean;
}>();

const emit = defineEmits<{
  (e: "select", tour: Tour): void;
  (e: "deleted"): void;
  (e: "close"): void;
  (e: "update:isCollapsed", val: boolean): void;
}>();

const tours = ref<Tour[]>([]);
const trashItems = ref<TrashItem[]>([]);
const isLoading = ref(false);
const error = ref("");
const filterType = ref<"all" | "bike" | "road" | "trash">("all");
function getStoredLibraryCollapsed(): boolean {
  try {
    return localStorage.getItem("tourpilot_library_collapsed") === "true";
  } catch {
    return false;
  }
}

const isCollapsedInternal = ref(getStoredLibraryCollapsed());
const isCollapsed = computed({
  get: () => (props.isCollapsed !== undefined ? props.isCollapsed : isCollapsedInternal.value),
  set: (val: boolean) => {
    isCollapsedInternal.value = val;
    emit("update:isCollapsed", val);
    try {
      localStorage.setItem("tourpilot_library_collapsed", String(val));
    } catch {
      // ignore
    }
  },
});
const sidebarWidth = ref(288);
const isResizing = ref(false);

// #3 Focus-trap refs
const dialogRef = ref<HTMLElement | null>(null);
const cancelBtnRef = ref<HTMLButtonElement | null>(null);

const confirmDialog = ref<{
  open: boolean;
  type: "deleteTour" | "deletePermanently";
  tour?: Tour;
  trashItem?: TrashItem;
}>({ open: false, type: "deleteTour" });

const filteredTours = computed(() => {
  if (filterType.value === "all") return tours.value;
  if (filterType.value === "trash") return [];
  return tours.value.filter((t) => t.tour_type === filterType.value);
});

const bikeTours = computed(() => tours.value.filter((t) => t.tour_type === "bike"));
const roadTours = computed(() => tours.value.filter((t) => t.tour_type === "road"));

async function loadTours(autoSelectLatest = false) {
  isLoading.value = true;
  error.value = "";
  try {
    tours.value = await fetchTours();
    if (autoSelectLatest && tours.value.length > 0) {
      const sorted = [...tours.value].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      );
      emit("select", sorted[0]);
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load tours";
  } finally {
    isLoading.value = false;
  }
}

async function loadTrash() {
  isLoading.value = true;
  error.value = "";
  try {
    trashItems.value = await fetchTrash();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load trash";
  } finally {
    isLoading.value = false;
  }
}

async function handleDelete(tour: Tour, event: Event) {
  event.stopPropagation();
  confirmDialog.value = { open: true, type: "deleteTour", tour };
  await nextTick();
  cancelBtnRef.value?.focus();
}

async function handleRestore(item: TrashItem) {
  try {
    const restored = await restoreFromTrash(item.tour_type, item.trash_name);
    await loadTours(false);
    await loadTrash();
    emit("select", restored as Tour);
    filterType.value = "all";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to restore";
  }
}

async function handlePermanentDelete(item: TrashItem) {
  confirmDialog.value = { open: true, type: "deletePermanently", trashItem: item };
  await nextTick();
  cancelBtnRef.value?.focus();
}

async function handleConfirmDialog() {
  const dialog = confirmDialog.value;
  confirmDialog.value = { ...confirmDialog.value, open: false };
  if (dialog.type === "deleteTour" && dialog.tour) {
    try {
      await deleteTour(dialog.tour.tour_type, dialog.tour.slug);
      await loadTours(false);
      emit("deleted");
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to delete";
    }
  } else if (dialog.type === "deletePermanently" && dialog.trashItem) {
    try {
      await deleteFromTrash(dialog.trashItem.tour_type, dialog.trashItem.trash_name);
      await loadTrash();
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to delete";
    }
  }
}

// #3 Focus-trap: keep Tab/Shift+Tab inside the dialog, Escape closes it
function handleDialogKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    confirmDialog.value.open = false;
    return;
  }
  if (e.key !== "Tab") return;
  const dialog = dialogRef.value;
  if (!dialog) return;
  const focusable = Array.from(
    dialog.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((el) => !el.hasAttribute("disabled"));
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (e.shiftKey) {
    if (document.activeElement === first) {
      e.preventDefault();
      last.focus();
    }
  } else {
    if (document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

// #5 Touch + Mouse resize
function startResize(clientX: number) {
  isResizing.value = true;
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";

  function onMouseMove(ev: MouseEvent) {
    sidebarWidth.value = Math.max(200, Math.min(500, ev.clientX));
  }
  function onTouchMove(ev: TouchEvent) {
    sidebarWidth.value = Math.max(200, Math.min(500, ev.touches[0].clientX));
  }
  function cleanup() {
    isResizing.value = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", cleanup);
    document.removeEventListener("touchmove", onTouchMove);
    document.removeEventListener("touchend", cleanup);
  }

  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", cleanup);
  document.addEventListener("touchmove", onTouchMove, { passive: true });
  document.addEventListener("touchend", cleanup);
}

function onResizeMouseDown(e: MouseEvent) {
  e.preventDefault();
  startResize(e.clientX);
}

function onResizeTouchStart(e: TouchEvent) {
  startResize(e.touches[0].clientX);
}

function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString(props.language === "de" ? "de-DE" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

watch(filterType, (newVal) => {
  if (newVal === "trash") loadTrash();
});

watch(
  () => props.refreshKey,
  () => loadTours(false),
);

onMounted(() => loadTours(true));
</script>

<template>
  <aside
    :class="[
      'h-full bg-monokai-light-panel dark:bg-monokai-panel border-r border-monokai-light-border dark:border-monokai-border flex flex-col transition-all relative',
      isCollapsed ? 'w-12' : '',
      isResizing ? '' : 'duration-200',
    ]"
    :style="isCollapsed ? {} : { width: `${sidebarWidth}px` }"
  >
    <!-- Header -->
    <div
      class="p-3 border-b border-monokai-light-border dark:border-monokai-border flex items-center justify-between"
    >
      <h2
        v-if="!isCollapsed"
        class="font-semibold text-monokai-light-fg dark:text-monokai-fg text-sm"
      >
        {{ t("tourLibrary", language) }}
      </h2>
      <button
        @click="isCollapsed = !isCollapsed"
        class="p-1 hover:bg-monokai-lightBorder/50 dark:hover:bg-monokai-card rounded-lg text-monokai-lightMuted dark:text-monokai-muted transition focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500"
        :title="
          isCollapsed
            ? language === 'de'
              ? 'Erweitern'
              : 'Expand'
            : language === 'de'
              ? 'Einklappen'
              : 'Collapse'
        "
        :aria-label="
          isCollapsed
            ? language === 'de'
              ? 'Bibliothek erweitern'
              : 'Expand library'
            : language === 'de'
              ? 'Bibliothek einklappen'
              : 'Collapse library'
        "
        :aria-expanded="!isCollapsed"
      >
        <ChevronLeft :size="16" :class="{ 'rotate-180': isCollapsed }" aria-hidden="true" />
      </button>
    </div>

    <!-- Collapsed state -->
    <div v-if="isCollapsed" class="flex-1 flex flex-col items-center py-4 gap-4">
      <button
        @click="
          filterType = 'bike';
          isCollapsed = false;
        "
        class="relative p-2 hover:bg-monokai-lightBorder/50 dark:hover:bg-monokai-card rounded-lg text-monokai-lightFg dark:text-monokai-fg transition"
        :title="language === 'de' ? 'Radtouren' : 'Bike Tours'"
        :aria-label="language === 'de' ? 'Radtouren anzeigen' : 'Show bike tours'"
      >
        <Bike :size="20" aria-hidden="true" />
        <span
          class="absolute -top-1 -right-1 bg-monokai-lightCyan dark:bg-monokai-cyan text-white dark:text-monokai-bg text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold"
          aria-hidden="true"
        >
          {{ bikeTours.length }}
        </span>
        <span class="sr-only">{{ bikeTours.length }}</span>
      </button>
      <button
        @click="
          filterType = 'road';
          isCollapsed = false;
        "
        class="relative p-2 hover:bg-monokai-lightBorder/50 dark:hover:bg-monokai-card rounded-lg text-monokai-lightFg dark:text-monokai-fg transition"
        :title="language === 'de' ? 'Roadtrips' : 'Road Trips'"
        :aria-label="language === 'de' ? 'Roadtrips anzeigen' : 'Show road trips'"
      >
        <Car :size="20" aria-hidden="true" />
        <span
          class="absolute -top-1 -right-1 bg-monokai-lightCyan dark:bg-monokai-cyan text-white dark:text-monokai-bg text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold"
          aria-hidden="true"
        >
          {{ roadTours.length }}
        </span>
        <span class="sr-only">{{ roadTours.length }}</span>
      </button>
      <button
        @click="
          filterType = 'trash';
          isCollapsed = false;
        "
        class="relative p-2 hover:bg-monokai-lightBorder/50 dark:hover:bg-monokai-card rounded-lg text-monokai-lightFg dark:text-monokai-fg transition"
        :title="language === 'de' ? 'Papierkorb' : 'Trash'"
        :aria-label="language === 'de' ? 'Papierkorb anzeigen' : 'Show trash'"
      >
        <Trash2 :size="20" aria-hidden="true" />
      </button>
    </div>

    <!-- Expanded state -->
    <template v-else>
      <!-- Filter tabs (Segmented Control) -->
      <div
        class="mx-2 my-2 p-1 bg-monokai-lightBorder/60 dark:bg-monokai-card rounded-xl flex gap-1 text-xs font-medium"
        role="tablist"
      >
        <button
          v-for="filter in ['all', 'bike', 'road', 'trash'] as const"
          :key="filter"
          role="tab"
          :aria-selected="filterType === filter"
          :class="[
            'flex-1 py-1.5 px-2 text-center rounded-lg transition-all flex items-center justify-center gap-1',
            filterType === filter
              ? 'bg-white dark:bg-monokai-bg text-monokai-lightCyan dark:text-monokai-yellow shadow-xs font-semibold'
              : 'text-monokai-lightMuted dark:text-monokai-muted hover:text-monokai-lightFg dark:hover:text-monokai-fg hover:bg-white/50 dark:hover:bg-monokai-border/40',
          ]"
          @click="filterType = filter"
        >
          <template v-if="filter === 'all'">{{ t("all", language) }}</template>
          <template v-else-if="filter === 'bike'">
            <Bike :size="13" aria-hidden="true" />
            <span>{{ language === "de" ? "Rad" : "Bike" }}</span>
          </template>
          <template v-else-if="filter === 'road'">
            <Car :size="13" aria-hidden="true" />
            <span>{{ language === "de" ? "Auto" : "Road" }}</span>
          </template>
          <template v-else>
            <Trash2 :size="13" aria-hidden="true" />
            <span>{{ language === "de" ? "Papierkorb" : "Trash" }}</span>
          </template>
        </button>
      </div>

      <!-- Loading state -->
      <div v-if="isLoading" class="flex-1 flex items-center justify-center">
        <div
          class="animate-spin w-6 h-6 border-2 border-monokai-lightCyan dark:border-monokai-cyan border-t-transparent rounded-full"
          role="status"
          :aria-label="language === 'de' ? 'Wird geladen…' : 'Loading…'"
        ></div>
      </div>

      <!-- Error state -->
      <div
        v-else-if="error"
        role="alert"
        class="p-4 text-monokai-lightPink dark:text-monokai-pink text-sm"
      >
        {{ error }}
        <button @click="() => loadTours(false)" class="ml-2 underline">
          {{ language === "de" ? "Erneut versuchen" : "Retry" }}
        </button>
      </div>

      <!-- Trash view -->
      <template v-else-if="filterType === 'trash'">
        <div
          v-if="trashItems.length === 0"
          class="flex-1 flex items-center justify-center p-4 text-monokai-lightMuted text-sm text-center font-medium"
        >
          {{ t("trashEmpty", language) }}
        </div>
        <div v-else class="flex-1 overflow-y-auto px-2 space-y-1.5 py-1">
          <div
            v-for="item in trashItems"
            :key="item.trash_name"
            class="p-2.5 bg-white dark:bg-monokai-card border border-monokai-lightBorder dark:border-monokai-border rounded-xl hover:border-monokai-lightCyan dark:hover:border-monokai-border transition"
          >
            <div class="flex items-start gap-2">
              <div
                class="p-1.5 rounded-lg shrink-0"
                :class="
                  item.tour_type === 'bike'
                    ? 'bg-emerald-50 dark:bg-monokai-bg text-emerald-600 dark:text-monokai-green'
                    : 'bg-indigo-50 dark:bg-monokai-bg text-indigo-600 dark:text-monokai-purple'
                "
              >
                <Bike v-if="item.tour_type === 'bike'" :size="15" aria-hidden="true" />
                <Car v-else :size="15" aria-hidden="true" />
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="font-medium text-monokai-lightFg dark:text-monokai-fg text-sm truncate">
                  {{ item.title }}
                </h3>
                <p
                  v-if="item.deleted_at"
                  class="text-xs text-monokai-lightMuted dark:text-monokai-muted mt-0.5"
                >
                  {{ t("deletedOn", language, { date: formatDate(item.deleted_at) }) }}
                </p>
                <div class="flex gap-3 mt-2 font-medium text-xs">
                  <button
                    @click="handleRestore(item)"
                    class="text-monokai-lightCyan dark:text-monokai-cyan hover:underline transition focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500 rounded"
                  >
                    {{ t("restore", language) }}
                  </button>
                  <button
                    @click="handlePermanentDelete(item)"
                    class="text-monokai-lightPink dark:text-monokai-pink hover:underline transition focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-red-500 rounded"
                  >
                    {{ t("deletePermanently", language) }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Empty state (tours) -->
      <div
        v-else-if="filteredTours.length === 0"
        class="flex-1 flex items-center justify-center p-4 text-monokai-lightMuted text-sm text-center font-medium"
      >
        {{ t("noTours", language) }}
      </div>

      <!-- #4 Tour list — <button> elements for keyboard accessibility -->
      <div v-else class="flex-1 overflow-y-auto px-2 space-y-1.5 py-1">
        <div v-for="tour in filteredTours" :key="tour.id" class="relative group">
          <button
            type="button"
            :aria-pressed="tour.id === selectedTourId"
            :aria-label="
              tour.title +
              ' — ' +
              (tour.tour_type === 'bike'
                ? language === 'de'
                  ? 'Radtour'
                  : 'Bike tour'
                : language === 'de'
                  ? 'Roadtrip'
                  : 'Road trip')
            "
            :class="[
              'w-full text-left p-3 rounded-xl border transition-all cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500',
              tour.id === selectedTourId
                ? 'bg-amber-50/60 dark:bg-monokai-card border-monokai-lightYellow/50 dark:border-monokai-yellow shadow-xs'
                : 'bg-white dark:bg-monokai-card/90 border-monokai-lightBorder dark:border-monokai-border hover:border-monokai-lightCyan dark:hover:border-monokai-yellow hover:shadow-xs hover:-translate-y-0.5',
            ]"
            @click="emit('select', tour)"
          >
            <div class="flex items-start gap-2.5">
              <div
                class="p-1.5 rounded-lg shrink-0 mt-0.5"
                :class="
                  tour.tour_type === 'bike'
                    ? 'bg-emerald-50 dark:bg-monokai-bg text-emerald-700 dark:text-monokai-green'
                    : 'bg-indigo-50 dark:bg-monokai-bg text-indigo-700 dark:text-monokai-purple'
                "
              >
                <Bike v-if="tour.tour_type === 'bike'" :size="16" aria-hidden="true" />
                <Car v-else :size="16" aria-hidden="true" />
              </div>
              <div class="flex-1 min-w-0 pr-8">
                <h3
                  class="font-semibold text-monokai-lightFg dark:text-monokai-fg text-sm truncate group-hover:text-monokai-lightCyan dark:group-hover:text-monokai-cyan transition"
                >
                  {{ tour.title }}
                </h3>
                <p
                  v-if="tour.summary"
                  class="text-xs text-monokai-lightMuted dark:text-monokai-muted mt-0.5 line-clamp-2 leading-relaxed"
                >
                  {{ tour.summary }}
                </p>
                <p
                  class="text-[11px] font-medium text-monokai-lightMuted/80 dark:text-monokai-muted/80 mt-1.5"
                >
                  {{ formatDate(tour.created_at) }}
                </p>
              </div>
            </div>
          </button>
          <!-- Delete button overlaid absolutely so it doesn't nest inside the tour button -->
          <button
            type="button"
            :aria-label="(language === 'de' ? 'Tour löschen: ' : 'Delete tour: ') + tour.title"
            :title="t('deleteTourConfirmTitle', language)"
            class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 opacity-0 group-hover:opacity-100 focus:opacity-100 focus-visible:opacity-100 hover:bg-rose-50 dark:hover:bg-monokai-bg rounded-lg text-monokai-lightMuted hover:text-monokai-lightPink dark:hover:text-monokai-pink transition focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-red-500"
            @click.stop="handleDelete(tour, $event)"
          >
            <Trash2 :size="15" aria-hidden="true" />
          </button>
        </div>
      </div>

      <!-- Refresh button -->
      <div
        class="p-2 border-t border-monokai-lightBorder dark:border-monokai-border bg-monokai-lightPanel/70 dark:bg-monokai-panel"
      >
        <button
          @click="() => (filterType === 'trash' ? loadTrash() : loadTours(false))"
          :disabled="isLoading"
          class="w-full py-1.5 text-xs text-monokai-lightFg dark:text-monokai-fg hover:bg-white dark:hover:bg-monokai-card hover:shadow-xs rounded-lg transition flex items-center justify-center gap-1.5 font-medium disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500"
        >
          <RefreshCw :size="13" aria-hidden="true" />
          {{ t("refresh", language) }}
        </button>
      </div>
    </template>

    <!-- #5 Resize handle — Mouse + Touch -->
    <div
      v-if="!isCollapsed"
      class="absolute top-0 right-0 w-2 h-full cursor-col-resize group flex items-center justify-center touch-none"
      role="separator"
      aria-orientation="vertical"
      :aria-label="language === 'de' ? 'Breite anpassen' : 'Resize sidebar'"
      tabindex="0"
      @mousedown="onResizeMouseDown"
      @touchstart.passive="onResizeTouchStart"
    >
      <div
        :class="[
          'w-1 h-8 rounded-full transition-colors',
          isResizing ? 'bg-blue-500' : 'bg-gray-300 group-hover:bg-blue-400',
        ]"
      ></div>
    </div>
  </aside>

  <!-- #3 Confirmation Dialog with focus-trap -->
  <Teleport to="body">
    <div
      v-if="confirmDialog.open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs"
      @click.self="confirmDialog.open = false"
    >
      <div
        ref="dialogRef"
        class="relative w-full max-w-sm overflow-hidden rounded-2xl bg-white p-6 shadow-2xl border border-gray-100 animate-in fade-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="'dialog-title-library'"
        @keydown="handleDialogKeydown"
      >
        <div class="flex items-start gap-4">
          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600"
          >
            <AlertTriangle :size="20" aria-hidden="true" />
          </div>
          <div class="flex-1 min-w-0">
            <h3 id="dialog-title-library" class="text-base font-semibold text-gray-900">
              {{
                confirmDialog.type === "deleteTour"
                  ? t("deleteTourConfirmTitle", language)
                  : t("deletePermanentlyConfirmTitle", language)
              }}
            </h3>
            <p class="mt-1.5 text-sm text-gray-600 leading-relaxed break-words">
              <template v-if="confirmDialog.type === 'deleteTour' && confirmDialog.tour">
                {{ t("deleteTourConfirm", language, { title: confirmDialog.tour.title }) }}
              </template>
              <template
                v-else-if="confirmDialog.type === 'deletePermanently' && confirmDialog.trashItem"
              >
                {{
                  t("deletePermanentlyConfirm", language, { title: confirmDialog.trashItem.title })
                }}
              </template>
            </p>
          </div>
        </div>
        <div class="mt-6 flex justify-end gap-2.5">
          <button
            ref="cancelBtnRef"
            type="button"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-400"
            @click="confirmDialog.open = false"
          >
            {{ t("cancel", language) }}
          </button>
          <button
            type="button"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500"
            @click="handleConfirmDialog"
          >
            {{ t("delete", language) }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
