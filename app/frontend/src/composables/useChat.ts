/**
 * Composable for managing chat state and SSE streaming.
 */
import { computed, ref, type Ref } from "vue";
import {
  clientHeaders,
  fetchSessionDetail,
  fetchTourDetail,
  fetchTourGpx,
  saveLastViewedTour,
  saveTour,
  type Tour,
  type TourMetrics,
} from "../api";
import { t, type Lang } from "../i18n";
import { parseGpxElevation, parseGpxRoute } from "../utils/gpx";

const EVENT_NAMES = {
  session: "session",
  title: "title",
  error: "error",
  tour: "tour",
  map: "map",
  elevation: "elevation",
  gpx: "gpx",
  status: "status",
  tool: "tool",
  model: "model",
} as const;

export interface MapData {
  waypoints: [number, number][];
  routes: [number, number][][];
  pois: { lat: number; lon: number; name: string; category?: string }[];
  elevation: [number, number][];
}

export type ActivityEvent =
  | { type: "status"; message: string }
  | { type: "tool"; name: string }
  | { type: "model"; iteration: number; modelId: string };

export interface ChatState {
  sessionTitle: Ref<string>;
  tourMarkdown: Ref<string>;
  gpxContent: Ref<string>;
  tourMetrics: Ref<TourMetrics | undefined>;
  generatedTourType: Ref<"bike" | "road" | null>;
  isTourSaved: Ref<boolean>;
  isLoading: Ref<boolean>;
  errorMessage: Ref<string>;
  activityEvents: Ref<ActivityEvent[]>;
  mapData: Ref<MapData>;
  sessionId: Ref<string | null>;
  hasMapData: Ref<boolean>;
  sendMessage: (message: string, language: Lang) => Promise<void>;
  cancelRequest: () => void;
  loadTour: (tour: Tour) => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  saveCurrentTour: () => Promise<Tour | null>;
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
    sessionTitle: Ref<string>;
    errorMessage: Ref<string>;
    tourMarkdown: Ref<string>;
    generatedTourType: Ref<"bike" | "road" | null>;
    gpxContent: Ref<string>;
    mapData: Ref<MapData>;
    activityEvents: Ref<ActivityEvent[]>;
  },
) {
  if (eventName === EVENT_NAMES.session && payload.session_id) {
    state.sessionId.value = payload.session_id;
    return;
  }

  if (eventName === EVENT_NAMES.title && payload.title) {
    state.sessionTitle.value = payload.title;
    return;
  }

  if (eventName === EVENT_NAMES.error || payload.error) {
    state.errorMessage.value = payload.error;
    return;
  }

  if (eventName === EVENT_NAMES.tour || payload.markdown) {
    state.tourMarkdown.value = payload.markdown;
    state.generatedTourType.value =
      payload.tour_type === "bike" || payload.tour_type === "road" ? payload.tour_type : null;
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

  if (eventName === EVENT_NAMES.tool && payload.name) {
    state.activityEvents.value.push({ type: "tool", name: payload.name });
    return;
  }

  if (eventName === EVENT_NAMES.model && payload.model_id && payload.iteration) {
    state.activityEvents.value.push({
      type: "model",
      iteration: payload.iteration,
      modelId: payload.model_id,
    });
    return;
  }

  if (eventName === EVENT_NAMES.status && payload.message) {
    state.activityEvents.value.push({ type: "status", message: payload.message });
  }
}

function processSseBuffer(
  buffer: string,
  state: {
    sessionId: Ref<string | null>;
    sessionTitle: Ref<string>;
    errorMessage: Ref<string>;
    tourMarkdown: Ref<string>;
    generatedTourType: Ref<"bike" | "road" | null>;
    gpxContent: Ref<string>;
    mapData: Ref<MapData>;
    activityEvents: Ref<ActivityEvent[]>;
  },
): { nextBuffer: string; receivedData: boolean } {
  const blocks = buffer.replace(/\r\n/g, "\n").split("\n\n");
  const completeBlocks = blocks.slice(0, -1);
  const nextBuffer = blocks[blocks.length - 1] || "";
  let receivedData = false;

  for (const block of completeBlocks) {
    let currentEvent = "";
    const dataLines: string[] = [];

    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    const data = dataLines.join("\n");
    if (!data) continue;

    try {
      const parsed = JSON.parse(data);
      receivedData = true;
      applyStreamEvent(currentEvent, parsed, state);
    } catch {
      // Ignore malformed event payloads.
    }
  }

  return { nextBuffer, receivedData };
}

export function useChat(): ChatState {
  const sessionTitle = ref("");
  const tourMarkdown = ref("");
  const gpxContent = ref("");
  const tourMetrics = ref<TourMetrics | undefined>(undefined);
  const generatedTourType = ref<"bike" | "road" | null>(null);
  const isTourSaved = ref(false);
  const isLoading = ref(false);
  const errorMessage = ref("");
  const activityEvents = ref<ActivityEvent[]>([]);
  const sessionId = ref<string | null>(null);
  const mapData = ref<MapData>(createEmptyMapData());
  let activeRequest: AbortController | null = null;

  const hasMapData = computed(
    () =>
      mapData.value.waypoints.length > 0 ||
      mapData.value.routes.length > 0 ||
      mapData.value.pois.length > 0,
  );

  function reset() {
    tourMarkdown.value = "";
    gpxContent.value = "";
    tourMetrics.value = undefined;
    generatedTourType.value = null;
    isTourSaved.value = false;
    errorMessage.value = "";
    activityEvents.value = [];
    mapData.value = createEmptyMapData();
  }

  function clearError() {
    errorMessage.value = "";
  }

  async function sendMessage(message: string, language: Lang): Promise<void> {
    isLoading.value = true;
    reset();
    activeRequest = new AbortController();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...clientHeaders() },
        body: JSON.stringify({
          message,
          language,
          session_id: sessionId.value,
        }),
        signal: activeRequest.signal,
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
          sessionTitle,
          errorMessage,
          tourMarkdown,
          generatedTourType,
          gpxContent,
          mapData,
          activityEvents,
        });
        buffer = parsedStream.nextBuffer;
        receivedData = receivedData || parsedStream.receivedData;
      }

      if (!receivedData && !errorMessage.value) {
        errorMessage.value = t("errorNoResponse", language);
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        errorMessage.value = t("errorConnection", language);
      }
    } finally {
      activeRequest = null;
      isLoading.value = false;
    }
  }

  function cancelRequest() {
    activeRequest?.abort();
  }

  async function loadTour(tour: Tour): Promise<void> {
    isLoading.value = true;
    reset();

    try {
      const detail = await fetchTourDetail(tour.tour_type, tour.slug);
      if (detail.markdown) {
        tourMarkdown.value = detail.markdown;
      }
      generatedTourType.value = tour.tour_type;
      isTourSaved.value = true;
      if (detail.metrics) {
        tourMetrics.value = detail.metrics;
      }

      // Load GPX if available and parse for map display
      if (detail.has_gpx) {
        try {
          const gpx = await fetchTourGpx(tour.tour_type, tour.slug);
          gpxContent.value = gpx;

          // Parse GPX to extract route coordinates and elevation profile for map
          const routes = parseGpxRoute(gpx);
          const elevation = parseGpxElevation(gpx);
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
              elevation,
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

  async function loadSession(targetSessionId: string): Promise<void> {
    isLoading.value = true;
    reset();

    try {
      const detail = await fetchSessionDetail(targetSessionId);
      sessionId.value = detail.id;
      const latestResponse = [...detail.messages]
        .reverse()
        .find((message) => message.role === "assistant");
      if (latestResponse) {
        tourMarkdown.value = latestResponse.content;
      }
      if (detail.artifacts) {
        gpxContent.value = detail.artifacts.gpx || "";
        mapData.value = {
          ...createEmptyMapData(),
          ...detail.artifacts.map,
          elevation: detail.artifacts.elevation,
        };
      }
      generatedTourType.value =
        detail.tour_type === "bike" || detail.tour_type === "road" ? detail.tour_type : null;
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : "Failed to load session";
    } finally {
      isLoading.value = false;
    }
  }

  async function saveCurrentTour(): Promise<Tour | null> {
    if (!tourMarkdown.value || !generatedTourType.value || isTourSaved.value) return null;

    const saved = await saveTour({
      markdown: tourMarkdown.value,
      tour_type: generatedTourType.value,
      gpx: gpxContent.value || undefined,
      session_id: sessionId.value || undefined,
    });
    isTourSaved.value = true;
    return saved;
  }

  return {
    sessionTitle,
    tourMarkdown,
    gpxContent,
    tourMetrics,
    generatedTourType,
    isTourSaved,
    isLoading,
    errorMessage,
    activityEvents,
    mapData,
    sessionId,
    hasMapData,
    sendMessage,
    cancelRequest,
    loadTour,
    loadSession,
    saveCurrentTour,
    clearError,
    reset,
  };
}
