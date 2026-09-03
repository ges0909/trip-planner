<script setup lang="ts">
import { Bike, Car, ChevronsLeft, Pencil, RefreshCw, Trash2 } from "@lucide/vue";
import { computed, onMounted, ref, watch } from "vue";
import type { Tour, TrashItem } from "../api";
import { useTourLibrary } from "../composables/useTourLibrary";
import { t, type Lang } from "../i18n";
import ConfirmDialog from "./ConfirmDialog.vue";

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

const {
  tours,
  trashItems,
  isLoading,
  error,
  filterType,
  filteredTours,
  bikeTours,
  roadTours,
  loadTours,
  loadTrash,
  removeTour,
  renameTourItem,
  restoreItem,
  deleteTrashPermanently,
} = useTourLibrary();

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

const confirmDialog = ref<{
  open: boolean;
  type: "deleteTour" | "deletePermanently";
  tour?: Tour;
  trashItem?: TrashItem;
}>({ open: false, type: "deleteTour" });

const renameDialog = ref<{
  open: boolean;
  tour?: Tour;
}>({ open: false });
const renameInput = ref("");

const confirmDialogTitle = computed(() => {
  return confirmDialog.value.type === "deleteTour"
    ? t("deleteTourConfirmTitle", props.language)
    : t("deletePermanentlyConfirmTitle", props.language);
});

const confirmDialogMessage = computed(() => {
  if (confirmDialog.value.type === "deleteTour" && confirmDialog.value.tour) {
    return t("deleteTourConfirm", props.language, { title: confirmDialog.value.tour.title });
  }
  if (confirmDialog.value.type === "deletePermanently" && confirmDialog.value.trashItem) {
    return t("deletePermanentlyConfirm", props.language, {
      title: confirmDialog.value.trashItem.title,
    });
  }
  return "";
});

function handleRename(tour: Tour, event: Event) {
  event.stopPropagation();
  renameInput.value = tour.title;
  renameDialog.value = { open: true, tour };
}

async function handleConfirmRename() {
  const tour = renameDialog.value.tour;
  const newTitle = renameInput.value.trim();
  renameDialog.value = { open: false };

  if (tour && newTitle && newTitle !== tour.title) {
    const updated = await renameTourItem(tour.tour_type, tour.slug, newTitle);
    if (updated && props.selectedTourId === tour.id) {
      emit("select", updated);
    }
  }
}

async function handleDelete(tour: Tour, event: Event) {
  event.stopPropagation();
  confirmDialog.value = { open: true, type: "deleteTour", tour };
}

async function handleRestore(item: TrashItem) {
  const restored = await restoreItem(item.tour_type, item.trash_name);
  if (restored) {
    emit("select", restored);
  }
}

async function handlePermanentDelete(item: TrashItem) {
  confirmDialog.value = { open: true, type: "deletePermanently", trashItem: item };
}

async function handleConfirmDialog() {
  const dialog = confirmDialog.value;
  confirmDialog.value = { ...confirmDialog.value, open: false };

  if (dialog.type === "deleteTour" && dialog.tour) {
    const success = await removeTour(dialog.tour.tour_type, dialog.tour.slug);
    if (success) {
      emit("deleted");
    }
  } else if (dialog.type === "deletePermanently" && dialog.trashItem) {
    await deleteTrashPermanently(dialog.trashItem.tour_type, dialog.trashItem.trash_name);
  }
}

// Touch + Mouse resize
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

onMounted(async () => {
  const latest = await loadTours(true);
  if (latest) {
    emit("select", latest);
  }
});
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
        <ChevronsLeft :size="16" :class="{ 'rotate-180': isCollapsed }" aria-hidden="true" />
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
        class="p-2 border-b border-monokai-lightBorder dark:border-monokai-border bg-monokai-lightPanel/50 dark:bg-monokai-panel/50"
      >
        <div
          class="flex rounded-lg bg-monokai-lightBorder/40 dark:bg-monokai-card p-0.5 text-xs font-medium"
        >
          <button
            @click="filterType = 'all'"
            :class="[
              'flex-1 py-1 rounded-md transition text-center',
              filterType === 'all'
                ? 'bg-white dark:bg-monokai-panel text-monokai-lightFg dark:text-monokai-fg shadow-xs font-semibold'
                : 'text-monokai-lightMuted dark:text-monokai-muted hover:text-monokai-lightFg dark:hover:text-monokai-fg',
            ]"
          >
            {{ t("all", language) }} ({{ tours.length }})
          </button>
          <button
            @click="filterType = 'bike'"
            :class="[
              'flex-1 py-1 rounded-md transition text-center flex items-center justify-center gap-1',
              filterType === 'bike'
                ? 'bg-white dark:bg-monokai-panel text-monokai-lightFg dark:text-monokai-fg shadow-xs font-semibold'
                : 'text-monokai-lightMuted dark:text-monokai-muted hover:text-monokai-lightFg dark:hover:text-monokai-fg',
            ]"
          >
            <Bike :size="13" aria-hidden="true" />
            <span>{{ bikeTours.length }}</span>
          </button>
          <button
            @click="filterType = 'road'"
            :class="[
              'flex-1 py-1 rounded-md transition text-center flex items-center justify-center gap-1',
              filterType === 'road'
                ? 'bg-white dark:bg-monokai-panel text-monokai-lightFg dark:text-monokai-fg shadow-xs font-semibold'
                : 'text-monokai-lightMuted dark:text-monokai-muted hover:text-monokai-lightFg dark:hover:text-monokai-fg',
            ]"
          >
            <Car :size="13" aria-hidden="true" />
            <span>{{ roadTours.length }}</span>
          </button>
          <button
            @click="filterType = 'trash'"
            :class="[
              'p-1.5 rounded-md transition flex items-center justify-center',
              filterType === 'trash'
                ? 'bg-white dark:bg-monokai-panel text-rose-500 shadow-xs'
                : 'text-monokai-lightMuted dark:text-monokai-muted hover:text-rose-400',
            ]"
            :title="t('trash', language)"
            :aria-label="t('trash', language)"
          >
            <Trash2 :size="13" aria-hidden="true" />
          </button>
        </div>
      </div>

      <!-- Error message -->
      <div
        v-if="error"
        role="alert"
        class="p-3 bg-rose-500/10 border-b border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex justify-between items-center"
      >
        <span>{{ error }}</span>
        <button
          @click="error = ''"
          class="text-rose-400 hover:text-rose-600 font-bold focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-red-500"
          :aria-label="t('close', language)"
        >
          ✕
        </button>
      </div>

      <!-- Tour list -->
      <div class="flex-1 overflow-y-auto p-2 space-y-1.5 scrollbar-thin">
        <!-- Trash view -->
        <template v-if="filterType === 'trash'">
          <div
            v-if="trashItems.length === 0"
            class="text-center py-8 text-monokai-lightMuted dark:text-monokai-muted text-xs"
          >
            {{ t("trashEmpty", language) }}
          </div>
          <div
            v-for="item in trashItems"
            :key="item.trash_name"
            class="p-2.5 rounded-xl border border-monokai-lightBorder/60 dark:border-monokai-border bg-monokai-lightPanel dark:bg-monokai-card/40 space-y-2 group text-xs"
          >
            <div class="flex items-start justify-between gap-1">
              <span class="font-medium text-monokai-lightFg dark:text-monokai-fg line-clamp-1">
                {{ item.title }}
              </span>
              <span
                class="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold shrink-0"
                :class="
                  item.tour_type === 'bike'
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400'
                    : 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400'
                "
              >
                {{ item.tour_type }}
              </span>
            </div>
            <div class="flex items-center justify-between text-[11px]">
              <button
                @click="handleRestore(item)"
                class="text-monokai-lightCyan dark:text-monokai-cyan hover:underline font-medium focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500"
              >
                {{ t("restore", language) }}
              </button>
              <button
                @click="handlePermanentDelete(item)"
                class="text-rose-500 hover:text-rose-700 font-medium focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-red-500"
              >
                {{ t("deletePermanently", language) }}
              </button>
            </div>
          </div>
        </template>

        <!-- Active tours view -->
        <template v-else>
          <div
            v-if="filteredTours.length === 0 && !isLoading"
            class="text-center py-8 text-monokai-lightMuted dark:text-monokai-muted text-xs"
          >
            {{ t("noTours", language) }}
          </div>

          <div
            v-for="tour in filteredTours"
            :key="tour.id"
            class="group relative rounded-xl border transition flex items-stretch"
            :class="[
              selectedTourId === tour.id
                ? 'bg-blue-50/80 dark:bg-monokai-card border-blue-200 dark:border-monokai-cyan/40 shadow-xs'
                : 'bg-white dark:bg-monokai-card/50 border-monokai-lightBorder/40 dark:border-monokai-border hover:border-blue-200 dark:hover:border-monokai-cyan/30 hover:bg-slate-50/80 dark:hover:bg-monokai-card',
            ]"
          >
            <button
              type="button"
              class="w-full text-left p-3 pr-14 cursor-pointer rounded-xl focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500"
              @click="emit('select', tour)"
            >
              <div class="flex items-start gap-2.5">
                <div
                  class="p-1.5 rounded-lg shrink-0 mt-0.5"
                  :class="
                    tour.tour_type === 'bike'
                      ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400'
                      : 'bg-blue-50 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400'
                  "
                >
                  <Bike v-if="tour.tour_type === 'bike'" :size="15" aria-hidden="true" />
                  <Car v-else :size="15" aria-hidden="true" />
                </div>
                <div class="min-w-0 flex-1">
                  <h3
                    class="text-xs font-semibold text-monokai-lightFg dark:text-monokai-fg line-clamp-1 leading-snug"
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
            <div
              class="absolute top-2 right-2 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition"
            >
              <button
                type="button"
                :aria-label="
                  (language === 'de' ? 'Tour umbenennen: ' : 'Rename tour: ') + tour.title
                "
                :title="t('rename', language)"
                class="p-1.5 hover:bg-monokai-lightBorder/60 dark:hover:bg-monokai-bg rounded-md text-monokai-lightMuted hover:text-blue-500 dark:hover:text-monokai-cyan transition focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-500"
                @click.stop="handleRename(tour, $event)"
              >
                <Pencil :size="13" aria-hidden="true" />
              </button>
              <button
                type="button"
                :aria-label="(language === 'de' ? 'Tour löschen: ' : 'Delete tour: ') + tour.title"
                :title="t('deleteTourConfirmTitle', language)"
                class="p-1.5 hover:bg-rose-50 dark:hover:bg-monokai-bg rounded-md text-monokai-lightMuted hover:text-rose-500 dark:hover:text-monokai-pink transition focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-red-500"
                @click.stop="handleDelete(tour, $event)"
              >
                <Trash2 :size="13" aria-hidden="true" />
              </button>
            </div>
          </div>
        </template>
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

    <!-- Resize handle — Mouse + Touch -->
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

  <!-- Reusable Confirmation Dialog -->
  <ConfirmDialog
    v-model:open="confirmDialog.open"
    :title="confirmDialogTitle"
    :message="confirmDialogMessage"
    :confirm-text="t('delete', language)"
    :cancel-text="t('cancel', language)"
    @confirm="handleConfirmDialog"
  />

  <!-- Rename Dialog -->
  <ConfirmDialog
    v-model:open="renameDialog.open"
    :title="t('renameTourTitle', language)"
    :confirm-text="t('save', language)"
    :cancel-text="t('cancel', language)"
    confirm-button-class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
    @confirm="handleConfirmRename"
  >
    <div class="mt-3">
      <input
        v-model="renameInput"
        type="text"
        class="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-monokai-border bg-white dark:bg-monokai-card text-gray-900 dark:text-monokai-fg focus:outline-none focus:ring-2 focus:ring-blue-500"
        @keydown.enter="handleConfirmRename"
      />
    </div>
  </ConfirmDialog>
</template>
