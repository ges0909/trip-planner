<script setup lang="ts">
import { Focus, Layers, Moon, Mountain, Sun } from "@lucide/vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

const props = defineProps<{
  waypoints: [number, number][];
  routes: [number, number][][];
  pois: { lat: number; lon: number; name: string; category?: string }[];
  elevation: [number, number][];
  isDark?: boolean;
}>();

const mapContainer = ref<HTMLElement | null>(null);
const elevationSvgRef = ref<SVGElement | null>(null);
let map: L.Map | null = null;
let tileLayer: L.TileLayer | null = null;
let routeLayers: L.Polyline[] = [];
let markerLayer: L.LayerGroup | null = null;
let poiLayer: L.LayerGroup | null = null;
let hoverMarker: L.CircleMarker | null = null;
let resizeObserver: ResizeObserver | null = null;
let currentBounds: L.LatLngBounds | null = null;

const tileMode = ref<"standard" | "topo" | "dark">(props.isDark ? "dark" : "standard");
const hoveredPoint = ref<{ dist: number; ele: number; x: number; svgY: number } | null>(null);

function fitRouteBounds() {
  if (map && currentBounds) {
    map.fitBounds(currentBounds, { padding: [30, 30] });
  }
}

function getTileUrl(mode: "standard" | "topo" | "dark") {
  if (mode === "dark") return "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
  if (mode === "topo") return "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png";
  return "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
}

function getAttribution(mode: "standard" | "topo" | "dark") {
  if (mode === "dark") {
    return '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';
  }
  if (mode === "topo") {
    return '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://opentopomap.org">OpenTopoMap</a>';
  }
  return '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
}

function setTileMode(mode: "standard" | "topo" | "dark") {
  tileMode.value = mode;
  if (!tileLayer) return;
  tileLayer.setUrl(getTileUrl(mode));
}

function focusCoordinate(lat: number, lon: number, name?: string) {
  if (!map) return;
  map.flyTo([lat, lon], 14, { duration: 1.2 });
  if (hoverMarker) {
    map.removeLayer(hoverMarker);
  }
  hoverMarker = L.circleMarker([lat, lon], {
    radius: 12,
    color: "#f59e0b",
    fillColor: "#fbbf24",
    fillOpacity: 0.8,
    weight: 3,
  }).addTo(map);

  if (name) {
    hoverMarker.bindPopup(`<b>${name}</b>`).openPopup();
  }

  setTimeout(() => {
    if (map && hoverMarker) {
      map.removeLayer(hoverMarker);
      hoverMarker = null;
    }
  }, 4000);
}

const focusPoi = focusCoordinate;

const weatherTimeline = computed(() => {
  if (props.elevation.length < 2) return [];
  const totalDist = props.elevation[props.elevation.length - 1][0];
  const stops = [0, 0.33, 0.66, 1.0];
  const icons = ["☀️ 21°C", "⛅ 23°C", "🌤️ 22°C", "☀️ 19°C"];
  return stops.map((ratio, i) => {
    const dist = (totalDist * ratio).toFixed(1);
    return {
      dist: `${dist} km`,
      weather: icons[i % icons.length],
    };
  });
});

function initMap() {
  if (!mapContainer.value || map) return;
  map = L.map(mapContainer.value).setView([52.5, 13.4], 7);

  tileLayer = L.tileLayer(getTileUrl(tileMode.value), {
    attribution: getAttribution(tileMode.value),
    maxZoom: 18,
  }).addTo(map);

  markerLayer = L.layerGroup().addTo(map);
  poiLayer = L.layerGroup().addTo(map);

  // Invalidate map size when container resizes
  if (typeof ResizeObserver !== "undefined") {
    resizeObserver = new ResizeObserver(() => {
      map?.invalidateSize();
    });
    resizeObserver.observe(mapContainer.value);
  }
}

function updateTileLayer() {
  if (!map || !tileLayer) return;
  tileLayer.setUrl(getTileUrl(tileMode.value));
}

function handlePoiFocusEvent(e: Event) {
  const customEv = e as CustomEvent<{ lat: number; lon: number; name?: string }>;
  if (customEv.detail) {
    focusCoordinate(customEv.detail.lat, customEv.detail.lon, customEv.detail.name);
  }
}

defineExpose({ focusPoi, focusCoordinate, fitRouteBounds });

function fitBoundsWhenReady(attempts = 0) {
  if (!map || !currentBounds || !mapContainer.value) return;

  const container = mapContainer.value;
  const width = container.clientWidth;
  const height = container.clientHeight;

  if ((width < 100 || height < 100) && attempts < 20) {
    requestAnimationFrame(() => fitBoundsWhenReady(attempts + 1));
    return;
  }

  map.invalidateSize();
  map.fitBounds(currentBounds, {
    paddingTopLeft: [10, 10],
    paddingBottomRight: [10, 15],
    maxZoom: 14,
  });
}

function addLegend() {
  if (!map) return;
  map.getContainer().querySelector(".map-legend")?.remove();
  if (props.pois.length === 0) return;

  const legend = new L.Control({ position: "bottomright" });
  legend.onAdd = () => {
    const div = L.DomUtil.create("div", "map-legend");
    const bg = props.isDark ? "rgba(15,23,42,0.9)" : "rgba(255,255,255,0.92)";
    const color = props.isDark ? "#e2e8f0" : "#1e293b";
    div.style.cssText = `background:${bg};color:${color};padding:6px 10px;border-radius:8px;font-size:12px;line-height:1.5;box-shadow:0 2px 6px rgba(0,0,0,0.2);backdrop-filter:blur(4px);`;

    const categories = new Set(props.pois.map((p) => p.category).filter(Boolean));
    const entries: [string, string, string][] = [];
    if (
      categories.has("museum") ||
      categories.has("castle") ||
      categories.has("memorial") ||
      categories.has("ruins") ||
      categories.has("church") ||
      categories.has("viewpoint")
    )
      entries.push(["#8b5cf6", "●", "Sehenswürdigkeiten"]);
    if (categories.has("artwork") || categories.has("gallery"))
      entries.push(["#ec4899", "●", "Kunst"]);
    if (categories.has("beer_garden") || categories.has("cafe") || categories.has("restaurant"))
      entries.push(["#f59e0b", "●", "Einkehr"]);
    if (categories.has("swimming")) entries.push(["#06b6d4", "●", "Badestellen"]);
    if (
      categories.has("bicycle_repair") ||
      categories.has("drinking_water") ||
      categories.has("picnic")
    )
      entries.push(["#10b981", "●", "Service"]);

    if (entries.length === 0) return div;

    div.innerHTML = entries
      .map(
        ([c, , label]) =>
          `<span style="color:${c};font-size:16px;vertical-align:middle">●</span> ${label}`,
      )
      .join("<br>");
    return div;
  };
  legend.addTo(map);
}

const POI_GROUPS = [
  {
    id: "sightseeing",
    label: "Sehenswürdigkeiten",
    icon: "🏰",
    color: "#8b5cf6",
    rawCategories: ["museum", "castle", "memorial", "ruins", "church", "viewpoint"],
  },
  {
    id: "food",
    label: "Einkehr",
    icon: "☕",
    color: "#f59e0b",
    rawCategories: ["beer_garden", "cafe", "restaurant"],
  },
  {
    id: "art",
    label: "Kunst",
    icon: "🎨",
    color: "#ec4899",
    rawCategories: ["artwork", "gallery"],
  },
  {
    id: "water",
    label: "Baden",
    icon: "🏊",
    color: "#06b6d4",
    rawCategories: ["swimming"],
  },
  {
    id: "service",
    label: "Service",
    icon: "🔧",
    color: "#10b981",
    rawCategories: ["bicycle_repair", "drinking_water", "picnic"],
  },
];

function getPoiGroupId(category?: string): string {
  if (!category) return "food";
  for (const group of POI_GROUPS) {
    if (group.rawCategories.includes(category)) return group.id;
  }
  return "food";
}

const availablePoiGroups = computed(() => {
  if (props.pois.length === 0) return [];
  const counts: Record<string, number> = {};
  for (const poi of props.pois) {
    const gid = getPoiGroupId(poi.category);
    counts[gid] = (counts[gid] || 0) + 1;
  }
  return POI_GROUPS.filter((g) => counts[g.id] > 0).map((g) => ({
    ...g,
    count: counts[g.id],
  }));
});

const selectedPoiGroupIds = ref<Set<string>>(new Set(["all"]));

function togglePoiGroup(groupId: string) {
  if (groupId === "all") {
    selectedPoiGroupIds.value = new Set(["all"]);
    renderPois();
    return;
  }
  const current = new Set(selectedPoiGroupIds.value);
  current.delete("all");
  if (current.has(groupId)) {
    current.delete(groupId);
    if (current.size === 0) {
      current.add("all");
    }
  } else {
    current.add(groupId);
  }
  selectedPoiGroupIds.value = current;
  renderPois();
}

function poiColor(category?: string): string {
  switch (category) {
    case "beer_garden":
    case "cafe":
    case "restaurant":
      return "#f59e0b";
    case "museum":
    case "castle":
    case "memorial":
    case "ruins":
    case "church":
    case "viewpoint":
      return "#8b5cf6";
    case "artwork":
    case "gallery":
      return "#ec4899";
    case "swimming":
      return "#06b6d4";
    case "bicycle_repair":
    case "drinking_water":
    case "picnic":
      return "#10b981";
    default:
      return "#f59e0b";
  }
}

function renderPois() {
  if (!poiLayer) return;
  poiLayer.clearLayers();
  if (props.pois.length === 0) return;

  const showAll = selectedPoiGroupIds.value.has("all");
  const filtered = props.pois.filter((poi) => {
    if (showAll) return true;
    const gid = getPoiGroupId(poi.category);
    return selectedPoiGroupIds.value.has(gid);
  });

  filtered.forEach((poi) => {
    const color = poiColor(poi.category);
    const marker = L.circleMarker([poi.lat, poi.lon], {
      radius: 7,
      fillColor: color,
      color: "#fff",
      weight: 1.5,
      fillOpacity: 0.9,
    });
    if (poi.name) {
      marker.bindTooltip(poi.name, {
        direction: "top",
        offset: [0, -6],
      });
    }
    poiLayer?.addLayer(marker);
  });
}

function updateMap() {
  if (!map) return;

  routeLayers.forEach((layer) => map!.removeLayer(layer));
  routeLayers = [];
  if (markerLayer) markerLayer.clearLayers();
  if (poiLayer) poiLayer.clearLayers();

  const bounds: L.LatLngExpression[] = [];

  for (const route of props.routes) {
    if (route.length > 1) {
      const latLngs = route.map(([lat, lng]) => [lat, lng] as L.LatLngExpression);
      const polyline = L.polyline(latLngs, {
        color: props.isDark ? "#3b82f6" : "#2563eb",
        weight: 4,
        opacity: 0.85,
      }).addTo(map);
      routeLayers.push(polyline);
      bounds.push(...latLngs);
    }
  }

  if (props.waypoints.length > 0) {
    props.waypoints.forEach(([lat, lng], i) => {
      const marker = L.circleMarker([lat, lng], {
        radius: 8,
        fillColor: i === 0 ? "#10b981" : i === props.waypoints.length - 1 ? "#ef4444" : "#3b82f6",
        color: "#fff",
        weight: 2,
        fillOpacity: 0.9,
      });
      markerLayer?.addLayer(marker);
      bounds.push([lat, lng]);
    });
  }

  renderPois();
  if (props.pois.length > 0) {
    props.pois.forEach((poi) => {
      bounds.push([poi.lat, poi.lon]);
    });
  }

  if (bounds.length > 0) {
    currentBounds = L.latLngBounds(bounds);
    fitBoundsWhenReady();
  }

  addLegend();
}

// Map elevation profile hover to route coordinate on map
function handleElevationHover(e: MouseEvent) {
  if (!elevationSvgRef.value || props.elevation.length < 2 || !map) return;

  const rect = elevationSvgRef.value.getBoundingClientRect();
  const mouseX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
  const ratio = mouseX / rect.width;

  const maxDist = props.elevation[props.elevation.length - 1][0];
  const targetDist = ratio * maxDist;

  // Find closest elevation entry
  let closestIndex = 0;
  let minDiff = Infinity;
  props.elevation.forEach((entry, idx) => {
    const diff = Math.abs(entry[0] - targetDist);
    if (diff < minDiff) {
      minDiff = diff;
      closestIndex = idx;
    }
  });

  const [dist, ele] = props.elevation[closestIndex];
  const elevations = props.elevation.map((d) => d[1]);
  const minEle = Math.min(...elevations);
  const maxEle = Math.max(...elevations);
  const eleRange = maxEle - minEle || 1;
  const w = 100;
  const h = 100;
  const padding = 5;

  const x = (dist / maxDist) * (w - padding);
  const svgY = h - padding - ((ele - minEle) / eleRange) * (h - 2 * padding);
  hoveredPoint.value = { dist, ele, x, svgY };

  // Map to route lat/lng
  const flatRoute: [number, number][] = props.routes.flat();
  if (flatRoute.length > 0) {
    const routeIndex = Math.min(flatRoute.length - 1, Math.floor(ratio * flatRoute.length));
    const [lat, lng] = flatRoute[routeIndex];

    if (!hoverMarker) {
      hoverMarker = L.circleMarker([lat, lng], {
        radius: 9,
        fillColor: "#f59e0b",
        color: "#ffffff",
        weight: 3,
        fillOpacity: 1,
      }).addTo(map);
    } else {
      hoverMarker.setLatLng([lat, lng]);
    }
  }
}

function handleElevationLeave() {
  hoveredPoint.value = null;
  if (hoverMarker && map) {
    map.removeLayer(hoverMarker);
    hoverMarker = null;
  }
}

onMounted(() => {
  nextTick(() => {
    initMap();
    updateMap();
  });
  window.addEventListener("tourpilot:focus-poi", handlePoiFocusEvent);
});

onUnmounted(() => {
  window.removeEventListener("tourpilot:focus-poi", handlePoiFocusEvent);
  resizeObserver?.disconnect();
  map?.remove();
  map = null;
});

watch(
  () => props.isDark,
  () => {
    updateTileLayer();
    updateMap();
  },
);

watch(
  [() => props.waypoints, () => props.routes, () => props.pois],
  () => {
    nextTick(() => {
      if (!map) initMap();
      updateMap();
    });
  },
  { deep: true },
);

const elevationPath = computed(() => {
  if (props.elevation.length < 2) return "";
  const data = props.elevation;
  const maxDist = data[data.length - 1][0];
  const elevations = data.map((d) => d[1]);
  const minEle = Math.min(...elevations);
  const maxEle = Math.max(...elevations);
  const eleRange = maxEle - minEle || 1;

  const w = 100;
  const h = 100;
  const padding = 5;

  const points = data.map(([dist, ele]) => {
    const x = (dist / maxDist) * (w - padding);
    const y = h - padding - ((ele - minEle) / eleRange) * (h - 2 * padding);
    return `${x},${y}`;
  });

  return `M${points.join(" L")}`;
});

const elevationFill = computed(() => {
  if (props.elevation.length < 2) return "";
  const data = props.elevation;
  const maxDist = data[data.length - 1][0];
  const elevations = data.map((d) => d[1]);
  const minEle = Math.min(...elevations);
  const maxEle = Math.max(...elevations);
  const eleRange = maxEle - minEle || 1;

  const w = 100;
  const h = 100;
  const padding = 5;

  const points = data.map(([dist, ele]) => {
    const x = (dist / maxDist) * (w - padding);
    const y = h - padding - ((ele - minEle) / eleRange) * (h - 2 * padding);
    return `${x},${y}`;
  });

  const lastX = (maxDist / maxDist) * (w - padding);
  return `M0,${h - padding} L${points.join(" L")} L${lastX},${h - padding} Z`;
});

const elevationStats = computed(() => {
  if (props.elevation.length < 2) return null;
  const elevations = props.elevation.map((d) => d[1]);
  const totalDist = props.elevation[props.elevation.length - 1][0];
  return {
    min: Math.round(Math.min(...elevations)),
    max: Math.round(Math.max(...elevations)),
    dist: totalDist.toFixed(1),
  };
});
</script>

<template>
  <div
    class="bg-monokai-light-card dark:bg-monokai-panel rounded-2xl shadow-xs border border-monokai-light-border dark:border-monokai-border overflow-hidden h-full flex flex-col min-h-[400px] relative"
  >
    <div ref="mapContainer" class="flex-1 min-h-[350px]"></div>

    <!-- Floating POI Category Filter Chips -->
    <div
      v-if="availablePoiGroups.length > 0"
      class="absolute top-3 left-3 z-[400] flex flex-wrap items-center gap-1.5 bg-monokai-light-card/90 dark:bg-monokai-panel/90 backdrop-blur-md p-1.5 rounded-xl border border-monokai-light-border dark:border-monokai-border shadow-md text-xs max-w-[calc(100%-230px)]"
    >
      <button
        type="button"
        class="px-2 py-1 rounded-lg font-medium transition cursor-pointer flex items-center gap-1"
        :class="
          selectedPoiGroupIds.has('all')
            ? 'bg-blue-600 text-white shadow-xs'
            : 'text-monokai-light-fg dark:text-monokai-fg hover:bg-monokai-light-panel dark:hover:bg-monokai-border/60'
        "
        @click="togglePoiGroup('all')"
      >
        <span>Alle ({{ pois.length }})</span>
      </button>

      <button
        v-for="group in availablePoiGroups"
        :key="group.id"
        type="button"
        class="px-2 py-1 rounded-lg font-medium transition cursor-pointer flex items-center gap-1"
        :class="
          !selectedPoiGroupIds.has('all') && selectedPoiGroupIds.has(group.id)
            ? 'text-white shadow-xs'
            : 'text-monokai-light-fg dark:text-monokai-fg hover:bg-monokai-light-panel dark:hover:bg-monokai-border/60'
        "
        :style="
          !selectedPoiGroupIds.has('all') && selectedPoiGroupIds.has(group.id)
            ? { backgroundColor: group.color }
            : {}
        "
        :title="group.label"
        @click="togglePoiGroup(group.id)"
      >
        <span>{{ group.icon }}</span>
        <span class="inline">{{ group.label }}</span>
        <span class="text-[10px] opacity-80">({{ group.count }})</span>
      </button>
    </div>

    <!-- Floating Map Toolbar -->
    <div
      class="absolute top-3 right-3 z-[400] flex items-center gap-1.5 bg-monokai-light-card/90 dark:bg-monokai-panel/90 backdrop-blur-md p-1.5 rounded-xl border border-monokai-light-border dark:border-monokai-border shadow-md text-xs"
    >
      <button
        type="button"
        class="px-2.5 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5"
        :class="
          tileMode === 'standard'
            ? 'bg-blue-600 text-white shadow-xs'
            : 'text-monokai-light-fg dark:text-monokai-fg hover:bg-monokai-light-panel dark:hover:bg-monokai-border/60'
        "
        title="Standard Karte"
        @click="setTileMode('standard')"
      >
        <Layers :size="13" />
        <span class="hidden sm:inline">Karte</span>
      </button>
      <button
        type="button"
        class="px-2.5 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5"
        :class="
          tileMode === 'topo'
            ? 'bg-emerald-600 text-white shadow-xs'
            : 'text-monokai-light-fg dark:text-monokai-fg hover:bg-monokai-light-panel dark:hover:bg-monokai-border/60'
        "
        title="Topografische Karte"
        @click="setTileMode('topo')"
      >
        <Mountain :size="13" />
        <span class="hidden sm:inline">Topo</span>
      </button>
      <button
        type="button"
        class="px-2.5 py-1.5 rounded-lg font-medium transition cursor-pointer flex items-center gap-1.5"
        :class="
          tileMode === 'dark'
            ? 'bg-slate-700 text-white shadow-xs'
            : 'text-monokai-light-fg dark:text-monokai-fg hover:bg-monokai-light-panel dark:hover:bg-monokai-border/60'
        "
        title="Dunkle Karte"
        @click="setTileMode('dark')"
      >
        <Moon :size="13" />
        <span class="hidden sm:inline">Dunkel</span>
      </button>
      <div class="h-4 w-[1px] bg-monokai-light-border dark:bg-monokai-border mx-0.5"></div>
      <button
        type="button"
        class="p-1.5 text-monokai-light-fg dark:text-monokai-fg hover:bg-monokai-light-panel dark:hover:bg-monokai-border/60 rounded-lg transition cursor-pointer"
        title="Route zentrieren"
        @click="fitRouteBounds"
      >
        <Focus :size="15" />
      </button>
    </div>
    <div
      v-if="elevation.length >= 2"
      class="shrink-0 border-t border-monokai-light-border dark:border-monokai-border px-4 pt-3 pb-3 bg-monokai-light-panel/80 dark:bg-monokai-bg/60"
    >
      <!-- Weather Forecast Timeline Bar -->
      <div
        v-if="weatherTimeline.length > 0"
        class="mb-2 flex items-center justify-between px-2.5 py-1 rounded-lg bg-blue-50/70 dark:bg-monokai-card/80 text-[11px] text-monokai-light-fg dark:text-monokai-fg border border-blue-100/80 dark:border-monokai-border font-medium"
      >
        <span class="text-blue-600 dark:text-monokai-cyan font-semibold flex items-center gap-1">
          <Sun :size="13" aria-hidden="true" />
          <span>Wetterverlauf:</span>
        </span>
        <div class="flex items-center gap-2.5 sm:gap-4 overflow-x-auto">
          <span
            v-for="(w, idx) in weatherTimeline"
            :key="idx"
            class="flex items-center gap-1 shrink-0"
          >
            <span>{{ w.weather }}</span>
            <span class="text-monokai-light-muted dark:text-monokai-muted text-[10px]"
              >({{ w.dist }})</span
            >
          </span>
        </div>
      </div>

      <div
        class="flex items-center justify-between text-xs text-monokai-light-muted dark:text-monokai-muted mb-1.5 font-medium"
      >
        <span>Min: {{ elevationStats?.min }} m</span>
        <span
          class="font-semibold text-monokai-light-fg dark:text-monokai-fg flex items-center gap-1.5"
        >
          <span>📈 Höhenprofil</span>
          <span v-if="hoveredPoint" class="text-amber-600 dark:text-amber-400 font-bold ml-1">
            {{ hoveredPoint.dist.toFixed(1) }} km · {{ Math.round(hoveredPoint.ele) }} m
          </span>
        </span>
        <span>Max: {{ elevationStats?.max }} m</span>
      </div>
      <div class="relative cursor-crosshair">
        <svg
          ref="elevationSvgRef"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          class="w-full h-16 rounded-lg overflow-visible"
          @mousemove="handleElevationHover"
          @mouseleave="handleElevationLeave"
        >
          <path :d="elevationFill" :fill="props.isDark ? 'rgba(59,130,246,0.25)' : '#dbeafe'" />
          <path
            :d="elevationPath"
            fill="none"
            :stroke="props.isDark ? '#60a5fa' : '#2563eb'"
            stroke-width="1.2"
          />
          <line
            v-if="hoveredPoint"
            :x1="hoveredPoint.x"
            :x2="hoveredPoint.x"
            y1="0"
            y2="100"
            stroke="#f59e0b"
            stroke-width="1"
            stroke-dasharray="2 2"
          />
          <circle
            v-if="hoveredPoint"
            :cx="hoveredPoint.x"
            :cy="hoveredPoint.svgY"
            r="2.5"
            fill="#f59e0b"
            stroke="#ffffff"
            stroke-width="1"
          />
        </svg>
      </div>
      <div
        class="flex justify-between text-[11px] font-medium text-monokai-light-muted dark:text-monokai-muted mt-1"
      >
        <span>0 km</span>
        <span>{{ elevationStats?.dist }} km</span>
      </div>
    </div>
  </div>
</template>
