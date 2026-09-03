<script setup lang="ts">
import { computed } from "vue";
import type { TourMetrics } from "../api";
import { sanitizeTourMarkdown } from "../utils/markdown";
import TourExportDropdown from "./TourExportDropdown.vue";

const props = defineProps<{
  markdown: string;
  gpx: string;
  metrics?: TourMetrics;
}>();

const emit = defineEmits<{
  (e: "focusPoi", poi: { lat: number; lon: number; name: string }): void;
}>();

const renderedHtml = computed(() => sanitizeTourMarkdown(props.markdown));

function handleContentClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null;
  if (!target) return;
  const poiAttr = target.getAttribute("data-poi-coords");
  if (poiAttr) {
    const [latStr, lonStr] = poiAttr.split(",");
    const lat = parseFloat(latStr);
    const lon = parseFloat(lonStr);
    const name = target.getAttribute("data-poi-name") || target.innerText;
    if (!isNaN(lat) && !isNaN(lon)) {
      emit("focusPoi", { lat, lon, name });
    }
  }
}

function handleImageError(event: Event) {
  const target = event.target as HTMLElement;
  if (target && target.tagName === "IMG") {
    target.style.display = "none";
  }
}

const filename = computed(() => {
  const match = props.markdown.match(/^#\s+(.+)$/m);
  if (match) {
    return match[1]
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");
  }
  return "tour";
});
</script>

<template>
  <div
    class="h-full flex flex-col rounded-2xl bg-white dark:bg-monokai-card border border-slate-200/90 dark:border-monokai-border shadow-md overflow-hidden text-monokai-light-fg dark:text-monokai-fg"
  >
    <!-- Scrollable Markdown Content Body -->
    <div
      class="flex-1 overflow-y-auto p-6 sm:p-8 scrollbar-thin"
      @click="handleContentClick"
      @error.capture="handleImageError"
    >
      <article
        class="prose prose-slate dark:prose-invert max-w-none text-monokai-light-fg dark:text-monokai-fg prose-headings:font-bold prose-h1:text-2xl prose-h1:text-monokai-light-pink dark:prose-h1:text-monokai-pink prose-h2:text-xl prose-h2:text-monokai-light-green dark:prose-h2:text-monokai-green prose-h3:text-lg prose-h3:text-monokai-light-yellow dark:prose-h3:text-monokai-yellow prose-a:text-monokai-light-cyan dark:prose-a:text-monokai-cyan prose-p:leading-relaxed prose-li:my-1 prose-table:w-full prose-table:border prose-th:p-2 prose-td:p-2"
        v-html="renderedHtml"
      />

      <!-- Bottom Export & Share Drawer -->
      <TourExportDropdown :markdown="markdown" :gpx="gpx" :filename="filename" />
    </div>
  </div>
</template>
