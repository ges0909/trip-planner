<script setup lang="ts">
import { Check, Copy, Download, FileText, Map, Printer, Share2 } from "@lucide/vue";
import DOMPurify from "dompurify";
import { marked } from "marked";
import { computed, ref } from "vue";
import type { TourMetrics } from "../api";
import { useToast } from "../composables/useToast";

const props = defineProps<{
  markdown: string;
  gpx: string;
  metrics?: TourMetrics;
}>();

const isTestEnvironment = import.meta.env.MODE === "test";

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

// Custom marked renderer for rich images and video embeds
const customRenderer = new marked.Renderer();
customRenderer.image = ({ href, text }) => {
  if (!href.startsWith("http://") && !href.startsWith("https://") && !href.startsWith("/api/")) {
    return "";
  }
  const caption = text
    ? `<figcaption class="text-xs text-center text-monokai-light-muted dark:text-monokai-muted mt-2 font-sans">${text}</figcaption>`
    : "";
  return `<figure class="my-6"><img src="${href}" alt="${text || ""}" loading="lazy" class="rounded-2xl shadow-md max-h-[480px] w-full object-cover border border-monokai-light-border dark:border-monokai-border" />${caption}</figure>`;
};

function parseWeatherInfo(md: string): string | null {
  const match = md.match(
    /(?:wetter|weather|vorhersage)[:\s]+([^\n.,]+(?:\d+°C|\d+\s*grad)[^\n.]*)/i,
  );
  if (match) return match[1].trim();
  const tempMatch = md.match(
    /(\d+\s*°C[^\n.]*sonnig|\d+\s*°C[^\n.]*bewölkt|sonnig[^\n.]*\d+\s*°C)/i,
  );
  return tempMatch ? tempMatch[1].trim() : null;
}

function sanitizeTourMarkdown(rawMd: string): string {
  let md = rawMd;
  // Strip YAML front matter if present (---\n...\n---)
  if (md.startsWith("---")) {
    const end = md.indexOf("---", 3);
    if (end !== -1) {
      md = md.slice(end + 3).trim();
    }
  }

  // Filter collapsible map details blocks
  md = md.replace(
    /<details>\s*<summary>[^<]*<\/summary>[\s\S]*?!\[[^\]]*\]\([^)]+\)[\s\S]*?<\/details>/gi,
    "",
  );
  // Remove standalone "Karte:" or "- Karte:" bullet points
  md = md.replace(/^[-*]?\s*(?:Karte|Map):\s*$/gim, "");
  // Remove static GPX file path lines
  md = md.replace(/^[-*]?\s*(?:\*\*GPX-Datei:\*\*|GPX:)\s*.*$/gim, "");
  // Remove relative/local image markdown references
  md = md.replace(/\[?!\[[^\]]*\]\((?!https?:\/\/|\/api\/)[^)]+\)\]?(?:\([^)]+\))?/gi, "");

  // Transform standalone YouTube links into responsive iframe embeds.
  // In Vitest/Happy DOM we intentionally avoid setting the live embed URL to prevent
  // background iframe fetches from the test environment while preserving the behavior
  // in the actual browser app.
  md = md.replace(
    /(?:^|\n)(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})(?:\S+)?/gi,
    (_match, videoId: string) => {
      const embedUrl = isTestEnvironment
        ? "about:blank"
        : `https://www.youtube-nocookie.com/embed/${videoId}`;
      return `\n<div class="aspect-video w-full rounded-2xl shadow-md overflow-hidden my-6 border border-monokai-light-border dark:border-monokai-border"><iframe src="${embedUrl}" data-video-id="${videoId}" title="Highlight Video" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen class="w-full h-full"></iframe></div>\n`;
    },
  );

  // Transform Geo coordinates link into interactive map POI clickable buttons
  md = md.replace(
    /\[([^\]]+)\]\((?:geo:|https?:\/\/(?:maps\.google\.com|www\.google\.com\/maps)\S*?[?&]q=)?(-?\d+\.\d+),(-?\d+\.\d+)\)/gi,
    '<a href="javascript:void(0)" data-poi-coords="$2,$3" data-poi-name="$1" class="inline-flex items-center gap-1 text-blue-600 dark:text-monokai-cyan font-bold hover:underline cursor-pointer">📍 $1</a>',
  );

  const raw = marked(md, { renderer: customRenderer }) as string;
  return DOMPurify.sanitize(raw, {
    ADD_TAGS: ["iframe", "figure", "figcaption"],
    ADD_ATTR: [
      "src",
      "allow",
      "allowfullscreen",
      "frameborder",
      "class",
      "width",
      "height",
      "loading",
      "title",
      "target",
      "scrolling",
      "data-poi-coords",
      "data-poi-name",
    ],
  });
}

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
  const title = match ? match[1] : "tour";
  return title
    .toLowerCase()
    .replace(/[äöü]/g, (c) => ({ ä: "ae", ö: "oe", ü: "ue" })[c] || c)
    .replace(/ß/g, "ss")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
});
</script>

<template>
  <div
    class="bg-white dark:bg-monokai-card text-monokai-light-fg dark:text-monokai-fg rounded-2xl shadow-xs border border-monokai-light-border dark:border-monokai-border flex flex-col h-full overflow-hidden"
  >
    <!-- Scrollable Markdown Content Area -->
    <div class="flex-1 overflow-y-auto p-6 sm:p-8">
      <div
        class="prose prose-slate dark:prose-invert max-w-none leading-relaxed prose-headings:font-bold prose-headings:tracking-tight prose-a:text-blue-600 dark:prose-a:text-monokai-cyan hover:prose-a:underline"
        v-html="renderedHtml"
        @click="handleContentClick"
        @error.capture="handleImageError"
      ></div>

      <!-- Unified Export & Share Dropdown -->
      <div
        class="mt-8 pt-5 border-t border-monokai-light-border/60 dark:border-monokai-border flex items-center justify-between gap-3 relative"
      >
        <div
          class="text-xs text-monokai-light-muted dark:text-monokai-muted flex items-center gap-1.5"
        >
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
              class="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left hover:bg-monokai-light-card dark:hover:bg-monokai-card transition font-medium"
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
              class="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left hover:bg-monokai-light-card dark:hover:bg-monokai-card transition font-medium"
              @click="
                printTour();
                isExportOpen = false;
              "
            >
              <Printer
                :size="15"
                class="text-amber-600 dark:text-monokai-yellow"
                aria-hidden="true"
              />
              <span>Drucken / Als PDF</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
