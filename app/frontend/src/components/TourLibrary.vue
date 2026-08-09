<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { fetchTours, type Tour } from "../api";
import { t, type Lang } from "../i18n";

const props = defineProps<{
  language: Lang;
}>();

const emit = defineEmits<{
  (e: "select", tour: Tour): void;
}>();

const tours = ref<Tour[]>([]);
const isLoading = ref(false);
const error = ref("");
const filterType = ref<"all" | "bike" | "road">("all");
const isCollapsed = ref(false);

const filteredTours = computed(() => {
  if (filterType.value === "all") return tours.value;
  return tours.value.filter((t) => t.tour_type === filterType.value);
});

const bikeTours = computed(() => tours.value.filter((t) => t.tour_type === "bike"));
const roadTours = computed(() => tours.value.filter((t) => t.tour_type === "road"));

async function loadTours() {
  isLoading.value = true;
  error.value = "";
  try {
    tours.value = await fetchTours();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load tours";
  } finally {
    isLoading.value = false;
  }
}

function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return date.toLocaleDateString(props.language === "de" ? "de-DE" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

onMounted(loadTours);
</script>

<template>
  <aside
    :class="[
      'bg-white border-r border-gray-200 flex flex-col transition-all duration-200',
      isCollapsed ? 'w-12' : 'w-72',
    ]"
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
          :class="['w-4 h-4 transition-transform', isCollapsed ? 'rotate-180' : '']"
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
    <div v-if="isCollapsed" class="flex-1 flex flex-col items-center py-4 gap-3">
      <div class="text-center">
        <span class="text-lg">{{ bikeTours.length }}</span>
      </div>
      <div class="text-center">
        <span class="text-lg">{{ roadTours.length }}</span>
      </div>
    </div>

    <!-- Expanded state -->
    <template v-else>
      <!-- Filter tabs -->
      <div class="flex border-b border-gray-200 text-xs">
        <button
          v-for="filter in (['all', 'bike', 'road'] as const)"
          :key="filter"
          :class="[
            'flex-1 py-2 text-center transition',
            filterType === filter
              ? 'border-b-2 border-blue-500 text-blue-600 font-medium'
              : 'text-gray-500 hover:text-gray-700',
          ]"
          @click="filterType = filter"
        >
          {{
            filter === "all"
              ? t("all", language)
              : filter === "bike"
                ? t("bikeTours", language)
                : t("roadTrips", language)
          }}
          <span class="ml-1 text-gray-400">
            ({{
              filter === "all"
                ? tours.length
                : filter === "bike"
                  ? bikeTours.length
                  : roadTours.length
            }})
          </span>
        </button>
      </div>

      <!-- Loading state -->
      <div v-if="isLoading" class="flex-1 flex items-center justify-center">
        <div class="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="p-4 text-red-600 text-sm">
        {{ error }}
        <button @click="loadTours" class="ml-2 underline">Retry</button>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="filteredTours.length === 0"
        class="flex-1 flex items-center justify-center p-4 text-gray-500 text-sm text-center"
      >
        {{ t("noTours", language) }}
      </div>

      <!-- Tour list -->
      <div v-else class="flex-1 overflow-y-auto">
        <button
          v-for="tour in filteredTours"
          :key="tour.id"
          @click="emit('select', tour)"
          class="w-full text-left p-3 hover:bg-gray-50 border-b border-gray-100 transition"
        >
          <div class="flex items-start gap-2">
            <span class="text-lg">{{ tour.tour_type === "bike" ? "" : "" }}</span>
            <div class="flex-1 min-w-0">
              <h3 class="font-medium text-gray-800 text-sm truncate">{{ tour.title }}</h3>
              <p v-if="tour.summary" class="text-xs text-gray-500 mt-0.5 line-clamp-2">
                {{ tour.summary }}
              </p>
              <p class="text-xs text-gray-400 mt-1">{{ formatDate(tour.created_at) }}</p>
            </div>
          </div>
        </button>
      </div>

      <!-- Refresh button -->
      <div class="p-2 border-t border-gray-200">
        <button
          @click="loadTours"
          :disabled="isLoading"
          class="w-full py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded transition flex items-center justify-center gap-1"
        >
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
  </aside>
</template>
