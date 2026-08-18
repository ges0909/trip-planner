/**
 * Composable for managing chat state and SSE streaming.
 */
import { computed, ref, type Ref } from "vue";
import { fetchTourDetail, fetchTourGpx, saveLastViewedTour, type Tour } from "../api";
import { t, type Lang } from "../i18n";
import { parseGpxRoute } from "../utils/gpx";

const EVENT_NAMES = {
  session: "session",
  error: "error",
  tour: "tour",
  map: "map",
  elevation: "elevation",
  gpx: "gpx",
  status: "status",
} as const;

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

function applyStreamEvent(
  eventName: string,
  payload: any,
  state: {
    sessionId: Ref<string | null>;
    errorMessage: Ref<string>;
    tourMarkdown: Ref<string>;
    gpxContent: Ref<string>;
    mapData: Ref<MapData>;
    statusMessages: Ref<string[]>;
  },
) {
  if (eventName === EVENT_NAMES.session && payload.session_id) {
    state.sessionId.value = payload.session_id;
    return;
  }

  if (eventName === EVENT_NAMES.error || payload.error) {
    state.errorMessage.value = payload.error;
    return;
  }

  if (eventName === EVENT_NAMES.tour || payload.markdown) {
    state.tourMarkdown.value = payload.markdown;
    return;
  }

  if (eventName === EVENT_NAMES.map) {
    if (payload.waypoints) {
      state.mapData.value.waypoints.push(...payload.waypoints);
    }
    if (payload.route) {
      state.mapData.value.routes.push(payload.route);
    }
    if (payload.pois) {
      state.mapData.value.pois.push(...payload.pois);
    }
    return;
  }

  if (eventName === EVENT_NAMES.elevation && payload.profile) {
    state.mapData.value.elevation = payload.profile;
    return;
  }

  if (eventName === EVENT_NAMES.gpx && payload.gpx) {
    state.gpxContent.value = payload.gpx;
    return;
  }

  if (eventName === EVENT_NAMES.status && payload.message) {
    if (!state.statusMessages.value.includes(payload.message)) {
      state.statusMessages.value.push(payload.message);
    }
  }
}

function processSseBuffer(
  buffer: string,
  state: {
    sessionId: Ref<string | null>;
    errorMessage: Ref<string>;
    tourMarkdown: Ref<string>;
    gpxContent: Ref<string>;
    mapData: Ref<MapData>;
    statusMessages: Ref<string[]>;
  },
): { nextBuffer: string; receivedData: boolean } {
  const lines = buffer.split("\n");
  let nextBuffer = "";
  let receivedData = false;
  let currentEvent = "";

  for (const line of lines) {
    if (line.startsWith("event:")) {
      currentEvent = line.slice(6).trim();
      continue;
    }

    if (!line.startsWith("data:")) {
      continue;
    }

    const data = line.slice(5).trim();
    if (!data) {
      continue;
    }

    try {
      const parsed = JSON.parse(data);
      receivedData = true;
      applyStreamEvent(currentEvent, parsed, state);
    } catch {
      // Ignore parse errors.
    }

    currentEvent = "";
  }

  if (lines.length > 0) {
    nextBuffer = lines[lines.length - 1] || "";
  }

  return { nextBuffer, receivedData };
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
        const parsedStream = processSseBuffer(buffer, {
          sessionId,
          errorMessage,
          tourMarkdown,
          gpxContent,
          mapData,
          statusMessages,
        });
        buffer = parsedStream.nextBuffer;
        receivedData = receivedData || parsedStream.receivedData;
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
            const waypoints: [number, number][] = [firstRoute[0], lastRoute[lastRoute.length - 1]];
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
          await saveLastViewedTour(sessionId.value, tour.id);
        } catch {
          // Ignore persistence failures; the tour can still be viewed without it.
        }
      }
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : "Failed to load tour";
    } finally {
      isLoading.value = false;
    }
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
