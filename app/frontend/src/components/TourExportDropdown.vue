<script setup lang="ts">
import { Check, Copy, Download, FileText, Map, Printer, Share2 } from "@lucide/vue";
import { ref } from "vue";
import { useToast } from "../composables/useToast";

const props = defineProps<{
  markdown: string;
  gpx: string;
  filename: string;
}>();

const { addToast } = useToast();
const isCopied = ref(false);
const isExportOpen = ref(false);

function printTour() {
  window.print();
}

async function copyMarkdown() {
  try {
    await navigator.clipboard.writeText(props.markdown);
    isCopied.value = true;
    addToast("Markdown kopiert", "Der Tourenplan wurde in die Zwischenablage kopiert.", "success");
    setTimeout(() => {
      isCopied.value = false;
    }, 2500);
  } catch {
    addToast("Kopieren fehlgeschlagen", "Bitte Inhalt manuell markieren.", "error");
  }
}

function handleMdDownload() {
  addToast("Markdown Export", "Datei wird heruntergeladen...", "info");
}

function handleGpxDownload() {
  addToast("GPX Download", "Track-Datei wird heruntergeladen...", "info");
}
</script>

<template>
  <div
    class="mt-8 pt-5 border-t border-monokai-light-border/60 dark:border-monokai-border flex items-center justify-between gap-3 relative"
  >
    <div class="text-xs text-monokai-light-muted dark:text-monokai-muted flex items-center gap-1.5">
      <Share2 :size="14" aria-hidden="true" />
      <span>Exportieren & Teilen</span>
    </div>

    <div class="relative">
      <button
        type="button"
        class="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-monokai-light-fg dark:text-monokai-fg bg-blue-50/80 dark:bg-monokai-panel hover:bg-blue-100 dark:hover:bg-monokai-border border border-blue-200 dark:border-monokai-border rounded-xl transition shadow-xs cursor-pointer"
        @click="isExportOpen = !isExportOpen"
      >
        <Download :size="15" class="text-blue-600 dark:text-monokai-cyan" aria-hidden="true" />
        <span>Export ▾</span>
      </button>

      <div
        v-if="isExportOpen"
        class="absolute right-0 bottom-full mb-2 z-30 w-56 overflow-hidden rounded-xl border border-monokai-light-border dark:border-monokai-border bg-monokai-light-panel dark:bg-monokai-panel shadow-xl py-1 text-monokai-light-fg dark:text-monokai-fg text-xs"
      >
        <a
          v-if="gpx"
          :href="'data:application/gpx+xml;charset=utf-8,' + encodeURIComponent(gpx)"
          :download="filename + '.gpx'"
          class="flex items-center gap-2.5 px-3.5 py-2.5 hover:bg-monokai-light-card dark:hover:bg-monokai-card transition font-medium text-blue-600 dark:text-monokai-cyan"
          @click="
            handleGpxDownload();
            isExportOpen = false;
          "
        >
          <Map :size="15" aria-hidden="true" />
          <span>GPX Track herunterladen</span>
        </a>

        <button
          type="button"
          class="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left hover:bg-monokai-light-card dark:hover:bg-monokai-card transition font-medium cursor-pointer"
          @click="
            copyMarkdown();
            isExportOpen = false;
          "
        >
          <Check
            v-if="isCopied"
            :size="15"
            class="text-emerald-600 dark:text-monokai-green"
            aria-hidden="true"
          />
          <Copy
            v-else
            :size="15"
            class="text-purple-600 dark:text-monokai-purple"
            aria-hidden="true"
          />
          <span>{{ isCopied ? "Markdown Kopiert!" : "Markdown Kopieren" }}</span>
        </button>

        <a
          :href="'data:text/markdown;charset=utf-8,' + encodeURIComponent(markdown)"
          :download="filename + '.md'"
          class="flex items-center gap-2.5 px-3.5 py-2.5 hover:bg-monokai-light-card dark:hover:bg-monokai-card transition font-medium"
          @click="
            handleMdDownload();
            isExportOpen = false;
          "
        >
          <FileText
            :size="15"
            class="text-emerald-600 dark:text-monokai-green"
            aria-hidden="true"
          />
          <span>Markdown Datei (.md)</span>
        </a>

        <button
          type="button"
          class="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left hover:bg-monokai-light-card dark:hover:bg-monokai-card transition font-medium cursor-pointer"
          @click="
            printTour();
            isExportOpen = false;
          "
        >
          <Printer :size="15" class="text-amber-600 dark:text-monokai-yellow" aria-hidden="true" />
          <span>Drucken / Als PDF</span>
        </button>
      </div>
    </div>
  </div>
</template>
