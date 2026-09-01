import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { type Ref, onUnmounted, ref } from "vue";

export type TileMode = "standard" | "topo" | "dark";

export interface MapDataProps {
  waypoints: [number, number][];
  routes: [number, number][][];
  pois: { lat: number; lon: number; name: string; category?: string }[];
  elevation: [number, number][];
  isDark?: boolean;
}

export function useLeafletMap(mapContainer: Ref<HTMLElement | null>, props: MapDataProps) {
  let map: L.Map | null = null;
  let tileLayer: L.TileLayer | null = null;
  let routeLayers: L.Polyline[] = [];
  let markerLayer: L.LayerGroup | null = null;
  let poiLayer: L.LayerGroup | null = null;
  let hoverMarker: L.CircleMarker | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let currentBounds: L.LatLngBounds | null = null;

  const tileMode = ref<TileMode>(props.isDark ? "dark" : "standard");

  function getTileUrl(mode: TileMode): string {
    if (mode === "dark") return "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
    if (mode === "topo") return "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png";
    return "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
  }

  function getAttribution(mode: TileMode): string {
    if (mode === "dark") {
      return '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';
    }
    if (mode === "topo") {
      return '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://opentopomap.org">OpenTopoMap</a>';
    }
    return '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
  }

  function setTileMode(mode: TileMode) {
    tileMode.value = mode;
    if (!tileLayer) return;
    tileLayer.setUrl(getTileUrl(mode));
  }

  function fitRouteBounds() {
    if (map && currentBounds) {
      map.fitBounds(currentBounds, { padding: [30, 30] });
    }
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

  function initMap() {
    if (!mapContainer.value || map) return;
    map = L.map(mapContainer.value).setView([52.5, 13.4], 7);

    tileLayer = L.tileLayer(getTileUrl(tileMode.value), {
      attribution: getAttribution(tileMode.value),
      maxZoom: 18,
    }).addTo(map);

    markerLayer = L.layerGroup().addTo(map);
    poiLayer = L.layerGroup().addTo(map);

    resizeObserver = new ResizeObserver(() => {
      map?.invalidateSize();
    });
    resizeObserver.observe(mapContainer.value);
  }

  function updateTileLayer() {
    if (!map || !tileLayer) return;
    tileLayer.setUrl(getTileUrl(tileMode.value));
  }

  function highlightElevationPoint(dist: number) {
    if (!map || props.elevation.length === 0 || props.routes.length === 0) return;
    const flatPoints: [number, number][] = props.routes.flat();
    if (flatPoints.length < 2) return;

    const totalDist = props.elevation[props.elevation.length - 1][0];
    const ratio = totalDist > 0 ? Math.min(1, Math.max(0, dist / totalDist)) : 0;
    const idx = Math.min(flatPoints.length - 1, Math.floor(ratio * (flatPoints.length - 1)));
    const pt = flatPoints[idx];

    if (hoverMarker) {
      map.removeLayer(hoverMarker);
    }

    hoverMarker = L.circleMarker(pt, {
      radius: 7,
      color: "#3b82f6",
      fillColor: "#60a5fa",
      fillOpacity: 0.9,
      weight: 3,
    }).addTo(map);
  }

  function removeElevationHighlight() {
    if (map && hoverMarker) {
      map.removeLayer(hoverMarker);
      hoverMarker = null;
    }
  }

  function cleanupMap() {
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    if (map) {
      map.remove();
      map = null;
    }
  }

  onUnmounted(() => {
    cleanupMap();
  });

  return {
    map: () => map,
    tileMode,
    setTileMode,
    fitRouteBounds,
    focusCoordinate,
    initMap,
    updateTileLayer,
    highlightElevationPoint,
    removeElevationHighlight,
    cleanupMap,
    get currentBounds() {
      return currentBounds;
    },
    set currentBounds(val: L.LatLngBounds | null) {
      currentBounds = val;
    },
    get routeLayers() {
      return routeLayers;
    },
    set routeLayers(val: L.Polyline[]) {
      routeLayers = val;
    },
    get markerLayer() {
      return markerLayer;
    },
    get poiLayer() {
      return poiLayer;
    },
  };
}
