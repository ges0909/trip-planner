<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import {
  fetchTours,
  fetchTrash,
  deleteTour,
  restoreFromTrash,
  deleteFromTrash,
  type Tour,
  type TrashItem,
} from "../api";
import { t, type Lang } from "../i18n";

const props = defineProps<{
  language: Lang;
  selectedTourId?: string | null;
}>();

const emit = defineEmits<{
  (e: "select", tour: Tour): void;
  (e: "deleted"): void;
}>();

const tours = ref<Tour[]>([]);
const trashItems = ref<TrashItem[]>([]);
const isLoading = ref(false);
const error = ref("");
const filterType = ref<"all" | "bike" | "road" | "trash">("all");
const isCollapsed = ref(false);
const sidebarWidth = ref(288);
const isResizing = ref(false);

const filteredTours = computed(() => {
  if (filterType.value === "all") return tours.value;
  if (filterType.value === "trash") return [];
  return tours.value.filter((t) => t.tour_type === filterType.value);
});

const bikeTours = computed(() =>
  tours.value.filter((t) => t.tour_type === "bike"),
);
const roadTours = computed(() =>
  tours.value.filter((t) => t.tour_type === "road"),
);

async function loadTours(autoSelectLatest = false) {
  isLoading.value = true;
  error.value = "";
  try {
    tours.value = await fetchTours();
    if (autoSelectLatest && tours.value.length > 0) {
      const sorted = [...tours.value].sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
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
  if (!confirm(`"${tour.title}" in den Papierkorb verschieben?`)) return;

  try {
    await deleteTour(tour.tour_type, tour.slug);
    await loadTours(false);
    emit("deleted");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to delete";
  }
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
  if (!confirm(`"${item.title}" endgültig löschen?`)) return;

  try {
    await deleteFromTrash(item.tour_type, item.trash_name);
    await loadTrash();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to delete";
  }
}

function startResize(e: MouseEvent) {
  e.preventDefault();
  isResizing.value = true;
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";

  function onMove(ev: MouseEvent) {
    const newWidth = ev.clientX;
    sidebarWidth.value = Math.max(200, Math.min(500, newWidth));
  }

  function onUp() {
    isResizing.value = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
  }

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}

function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString(props.language === "de" ? "de-DE" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// Load trash when switching to trash tab
watch(filterType, (newVal) => {
  if (newVal === "trash") {
    loadTrash();
  }
});

onMounted(() => loadTours(true));
</script>

<template>
  <aside
    :class="[
      'bg-white border-r border-gray-200 flex flex-col transition-all relative',
      isCollapsed ? 'w-12' : '',
      isResizing ? '' : 'duration-200',
    ]"
    :style="isCollapsed ? {} : { width: `${sidebarWidth}px` }"
  >
    <!-- Header -->
    <div class="p-3 border-b border-gray-200 flex items-center justify-between">
      <h2 v-if="!isCollapsed" class="font-semibold text-gray-800 text-sm">
        {{ t("tourLibrary", language) }}
      </h2>
      <button
        @click="isCollapsed = !isCollapsed"
        class="p-1 hover:bg-gray-100 rounded text-gray-500"
        :title="isCollapsed ? 'Expand' : 'Collapse'"
      >
        <svg
          :class="[
            'w-4 h-4 transition-transform',
            isCollapsed ? 'rotate-180' : '',
          ]"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
          />
        </svg>
      </button>
    </div>

    <!-- Collapsed state -->
    <div
      v-if="isCollapsed"
      class="flex-1 flex flex-col items-center py-4 gap-4"
    >
      <button
        @click="
          filterType = 'bike';
          isCollapsed = false;
        "
        class="relative p-2 hover:bg-gray-100 rounded"
        title="Radtouren"
      >
        <span class="text-xl">🚴</span>
        <span
          class="absolute -top-1 -right-1 bg-blue-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center"
        >
          {{ bikeTours.length }}
        </span>
      </button>
      <button
        @click="
          filterType = 'road';
          isCollapsed = false;
        "
        class="relative p-2 hover:bg-gray-100 rounded"
        title="Roadtrips"
      >
        <span class="text-xl">🚗</span>
        <span
          class="absolute -top-1 -right-1 bg-blue-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center"
        >
          {{ roadTours.length }}
        </span>
      </button>
      <button
        @click="
          filterType = 'trash';
          isCollapsed = false;
        "
        class="relative p-2 hover:bg-gray-100 rounded"
        title="Papierkorb"
      >
        <span class="text-xl">🗑️</span>
      </button>
    </div>

    <!-- Expanded state -->
    <template v-else>
      <!-- Filter tabs -->
      <div class="flex border-b border-gray-200 text-xs">
        <button
          v-for="filter in ['all', 'bike', 'road', 'trash'] as const"
          :key="filter"
          :class="[
            'flex-1 py-2 text-center transition',
            filterType === filter
              ? 'border-b-2 border-blue-500 text-blue-600 font-medium'
              : 'text-gray-500 hover:text-gray-700',
          ]"
          @click="filterType = filter"
        >
          <template v-if="filter === 'all'">{{ t("all", language) }}</template>
          <template v-else-if="filter === 'bike'"
            ><span class="text-lg">🚴</span></template
          >
          <template v-else-if="filter === 'road'"
            ><span class="text-lg">🚗</span></template
          >
          <template v-else><span class="text-lg">🗑️</span></template>
        </button>
      </div>

      <!-- Loading state -->
      <div v-if="isLoading" class="flex-1 flex items-center justify-center">
        <div
          class="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full"
        ></div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="p-4 text-red-600 text-sm">
        {{ error }}
        <button @click="() => loadTours(false)" class="ml-2 underline">
          Retry
        </button>
      </div>

      <!-- Trash view -->
      <template v-else-if="filterType === 'trash'">
        <div
          v-if="trashItems.length === 0"
          class="flex-1 flex items-center justify-center p-4 text-gray-500 text-sm text-center"
        >
          Papierkorb ist leer
        </div>
        <div v-else class="flex-1 overflow-y-auto">
          <div
            v-for="item in trashItems"
            :key="item.trash_name"
            class="p-3 border-b border-gray-100"
          >
            <div class="flex items-start gap-2">
              <span class="text-lg opacity-50">{{
                item.tour_type === "bike" ? "🚴" : "🚗"
              }}</span>
              <div class="flex-1 min-w-0">
                <h3 class="font-medium text-gray-600 text-sm truncate">
                  {{ item.title }}
                </h3>
                <p v-if="item.deleted_at" class="text-xs text-gray-400 mt-1">
                  Gelöscht: {{ formatDate(item.deleted_at) }}
                </p>
                <div class="flex gap-2 mt-2">
                  <button
                    @click="handleRestore(item)"
                    class="text-xs text-blue-600 hover:underline"
                  >
                    Wiederherstellen
                  </button>
                  <button
                    @click="handlePermanentDelete(item)"
                    class="text-xs text-red-600 hover:underline"
                  >
                    Endgültig löschen
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
        class="flex-1 flex items-center justify-center p-4 text-gray-500 text-sm text-center"
      >
        {{ t("noTours", language) }}
      </div>

      <!-- Tour list -->
      <div v-else class="flex-1 overflow-y-auto">
        <div
          v-for="tour in filteredTours"
          :key="tour.id"
          @click="emit('select', tour)"
          :class="[
            'w-full text-left p-3 border-b border-gray-100 transition cursor-pointer group',
            tour.id === selectedTourId
              ? 'bg-blue-50 border-l-2 border-l-blue-500'
              : 'hover:bg-gray-50',
          ]"
        >
          <div class="flex items-start gap-2">
            <span class="text-lg">{{
              tour.tour_type === "bike" ? "🚴" : "🚗"
            }}</span>
            <div class="flex-1 min-w-0">
              <h3 class="font-medium text-gray-800 text-sm truncate">
                {{ tour.title }}
              </h3>
              <p
                v-if="tour.summary"
                class="text-xs text-gray-500 mt-0.5 line-clamp-2"
              >
                {{ tour.summary }}
              </p>
              <p class="text-xs text-gray-400 mt-1">
                {{ formatDate(tour.created_at) }}
              </p>
            </div>
            <button
              @click="handleDelete(tour, $event)"
              class="p-1 opacity-0 group-hover:opacity-100 hover:bg-red-100 rounded text-red-500 transition"
              title="Löschen"
            >
              <svg
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Refresh button -->
      <div class="p-2 border-t border-gray-200">
        <button
          @click="
            () => (filterType === 'trash' ? loadTrash() : loadTours(false))
          "
          :disabled="isLoading"
          class="w-full py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded transition flex items-center justify-center gap-1"
        >
          <svg
            class="w-3 h-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          {{ t("refresh", language) }}
        </button>
      </div>
    </template>

    <!-- Resize handle -->
    <div
      v-if="!isCollapsed"
      @mousedown="startResize"
      class="absolute top-0 right-0 w-2 h-full cursor-col-resize group flex items-center justify-center"
    >
      <div
        :class="[
          'w-1 h-8 rounded-full transition-colors',
          isResizing ? 'bg-blue-500' : 'bg-gray-300 group-hover:bg-blue-400',
        ]"
      ></div>
    </div>
  </aside>
</template>
