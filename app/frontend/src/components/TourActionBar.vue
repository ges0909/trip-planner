<script setup lang="ts">
import { Check, Map, Save } from "@lucide/vue";
import type { Lang } from "../i18n";
import type { TourMetaItem } from "../utils/tourMeta";

defineProps<{
  metaItems: TourMetaItem[];
  hasMapData: boolean;
  isMapVisible: boolean;
  hasGeneratedTour: boolean;
  isTourSaved: boolean;
  isLoading: boolean;
  language: Lang;
}>();

const emit = defineEmits<{
  (e: "toggleMap"): void;
  (e: "saveTour"): void;
}>();
</script>

<template>
  <div
    v-if="metaItems.length > 0 || hasMapData || hasGeneratedTour"
    class="shrink-0 mb-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/90 bg-white/80 p-2.5 dark:border-monokai-border dark:bg-monokai-card/80 shadow-xs backdrop-blur-sm"
  >
    <!-- Left: Tour Metric Badges -->
    <div class="flex flex-wrap items-center gap-2">
      <div
        v-for="item in metaItems"
        :key="item.label"
        class="inline-flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-semibold"
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
        <span>{{ item.label }}</span>
      </div>
    </div>

    <!-- Right: Map Toggle & Save Actions -->
    <div class="flex items-center gap-2">
      <button
        v-if="hasMapData"
        type="button"
        class="inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition shadow-xs cursor-pointer border bg-monokai-light-card dark:bg-monokai-card text-monokai-light-fg dark:text-monokai-fg border-monokai-light-border dark:border-monokai-border hover:bg-monokai-light-panel dark:hover:bg-monokai-panel"
        :title="
          isMapVisible
            ? language === 'de'
              ? 'Karte ausblenden'
              : 'Hide map'
            : language === 'de'
              ? 'Karte anzeigen'
              : 'Show map'
        "
        @click="emit('toggleMap')"
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
        v-if="hasGeneratedTour"
        type="button"
        :disabled="isTourSaved || isLoading"
        class="inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition shadow-xs cursor-pointer"
        :class="
          isTourSaved
            ? 'bg-emerald-50 dark:bg-monokai-card text-emerald-700 dark:text-monokai-green border border-emerald-200 dark:border-monokai-green/40'
            : 'bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50'
        "
        @click="emit('saveTour')"
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
</template>
