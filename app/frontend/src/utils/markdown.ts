import DOMPurifyFactory from "dompurify";
import { marked } from "marked";

const isTestEnvironment = typeof import.meta !== "undefined" && import.meta.env?.MODE === "test";

function createPurifier() {
  const factory = (DOMPurifyFactory as any)?.default || DOMPurifyFactory;
  if (typeof factory === "function" && typeof window !== "undefined") {
    return factory(window);
  }
  return factory;
}

const purify = createPurifier();

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

export function sanitizeTourMarkdown(rawMd: string): string {
  let md = rawMd || "";

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
  // background iframe fetches from the test environment.
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
  return purify.sanitize(raw, {
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
