/**
 * Composable for managing chat state and SSE streaming.
 */
import { computed, ref, type Ref } from "vue";
import { fetchTourDetail, fetchTourGpx, type Tour } from "../api";
import { t, type Lang } from "../i18n";

export interface MapData {
  waypoints: [number, number][];
  routes: [number, number][][];
  pois: { lat: number; lon: number; name: string; category?: string }[];
  elevation: [number, number][];
}

export interface ChatState {
  tourMarkdown: Ref<string>;
  gpxContent: Ref<string>;
  isLoading: Ref<boolean>;
  errorMessage: Ref<string>;
  statusMessages: Ref<string[]>;
  mapData: Ref<MapData>;
  sessionId: Ref<string | null>;
  hasMapData: Ref<boolean>;
  sendMessage: (message: string, language: Lang) => Promise<void>;
  loadTour: (tour: Tour) => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

function createEmptyMapData(): MapData {
  return {
    waypoints: [],
    routes: [],
    pois: [],
    elevation: [],
  };
}

export function useChat(): ChatState {
  const tourMarkdown = ref("");
  const gpxContent = ref("");
  const isLoading = ref(false);
  const errorMessage = ref("");
  const statusMessages = ref<string[]>([]);
  const sessionId = ref<string | null>(null);
  const mapData = ref<MapData>(createEmptyMapData());

  const hasMapData = computed(
    () =>
      mapData.value.waypoints.length > 0 ||
      mapData.value.routes.length > 0 ||
      mapData.value.pois.length > 0,
  );

  function reset() {
    tourMarkdown.value = "";
    gpxContent.value = "";
    errorMessage.value = "";
    statusMessages.value = [];
    mapData.value = createEmptyMapData();
  }

  function clearError() {
    errorMessage.value = "";
  }

  async function sendMessage(message: string, language: Lang): Promise<void> {
    isLoading.value = true;
    reset();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          language,
          session_id: sessionId.value,
        }),
      });

      if (!response.ok) {
        errorMessage.value = t("errorServer", language, {
          status: response.status,
        });
        return;
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) return;

      let buffer = "";
      let receivedData = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            const data = line.slice(5).trim();
            if (!data) continue;

            try {
              const parsed = JSON.parse(data);
              receivedData = true;

              // Handle session ID (sent first by backend)
              if (currentEvent === "session" && parsed.session_id) {
                sessionId.value = parsed.session_id;
              }
              // Handle error
              else if (currentEvent === "error" || parsed.error) {
                errorMessage.value = parsed.error;
              }
              // Handle tour markdown
              else if (currentEvent === "tour" || parsed.markdown) {
                tourMarkdown.value = parsed.markdown;
              }
              // Handle map data
              else if (currentEvent === "map") {
                if (parsed.waypoints) {
                  mapData.value.waypoints.push(...parsed.waypoints);
                }
                if (parsed.route) {
                  mapData.value.routes.push(parsed.route);
                }
                if (parsed.pois) {
                  mapData.value.pois.push(...parsed.pois);
                }
              }
              // Handle elevation profile
              else if (currentEvent === "elevation" && parsed.profile) {
                mapData.value.elevation = parsed.profile;
              }
              // Handle GPX content
              else if (currentEvent === "gpx" && parsed.gpx) {
                gpxContent.value = parsed.gpx;
              }
              // Handle status messages
              else if (currentEvent === "status" && parsed.message) {
                if (!statusMessages.value.includes(parsed.message)) {
                  statusMessages.value.push(parsed.message);
                }
              }
            } catch {
              // Ignore parse errors
            }
            currentEvent = "";
          }
        }
      }

      if (!receivedData && !errorMessage.value) {
        errorMessage.value = t("errorNoResponse", language);
      }
    } catch {
      errorMessage.value = t("errorConnection", language);
    } finally {
      isLoading.value = false;
    }
  }

  async function loadTour(tour: Tour): Promise<void> {
    isLoading.value = true;
    reset();

    try {
      const detail = await fetchTourDetail(tour.tour_type, tour.slug);
      if (detail.markdown) {
        tourMarkdown.value = detail.markdown;
      }

      // Load GPX if available and parse for map display
      if (detail.has_gpx) {
        try {
          const gpx = await fetchTourGpx(tour.tour_type, tour.slug);
          gpxContent.value = gpx;

          // Parse GPX to extract route coordinates for map
          const routes = parseGpxRoute(gpx);
          if (routes.length > 0) {
            // Set first point of first route and last point of last route as waypoints
            const firstRoute = routes[0];
            const lastRoute = routes[routes.length - 1];
            const waypoints: [number, number][] = [
              firstRoute[0],
              lastRoute[lastRoute.length - 1],
            ];
            // Assign new mapData object to trigger reactivity
            mapData.value = {
              waypoints,
              routes,
              pois: [],
              elevation: [],
            };
          }
        } catch {
          // GPX is optional
        }
      }

      // Update last viewed tour if session exists
      if (sessionId.value) {
        try {
          await fetch(`/api/sessions/${sessionId.value}/last-viewed`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tour_id: tour.id }),
          });
        } catch {
          // Silently fail if unable to save last viewed tour
        }
      }
    } catch (error) {
      errorMessage.value =
        error instanceof Error ? error.message : "Failed to load tour";
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Parse GPX XML to extract track coordinates as [lat, lon] pairs.
   * Handles multiple tracks (multi-day trips).
   */
  function parseGpxRoute(gpx: string): [number, number][][] {
    const routes: [number, number][][] = [];
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(gpx, "application/xml");

      // Get all tracks (getElementsByTagName works with namespaced XML)
      const tracks = doc.getElementsByTagName("trk");
      for (let i = 0; i < tracks.length; i++) {
        const trk = tracks[i];
        const route: [number, number][] = [];
        const trkpts = trk.getElementsByTagName("trkpt");
        for (let j = 0; j < trkpts.length; j++) {
          const pt = trkpts[j];
          const lat = parseFloat(pt.getAttribute("lat") || "");
          const lon = parseFloat(pt.getAttribute("lon") || "");
          if (!isNaN(lat) && !isNaN(lon)) {
            route.push([lat, lon]);
          }
        }
        if (route.length > 0) {
          routes.push(route);
        }
      }

      // If no tracks found, try route points
      if (routes.length === 0) {
        const route: [number, number][] = [];
        const rtepts = doc.getElementsByTagName("rtept");
        for (let i = 0; i < rtepts.length; i++) {
          const pt = rtepts[i];
          const lat = parseFloat(pt.getAttribute("lat") || "");
          const lon = parseFloat(pt.getAttribute("lon") || "");
          if (!isNaN(lat) && !isNaN(lon)) {
            route.push([lat, lon]);
          }
        }
        if (route.length > 0) {
          routes.push(route);
        }
      }
    } catch {
      // Ignore parse errors
    }
    return routes;
  }

  return {
    tourMarkdown,
    gpxContent,
    isLoading,
    errorMessage,
    statusMessages,
    mapData,
    sessionId,
    hasMapData,
    sendMessage,
    loadTour,
    clearError,
    reset,
  };
}
