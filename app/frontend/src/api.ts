/**
 * API client for the Trip Planner backend.
 */

export interface LastViewedTourResponse {
  tour: {
    id: string;
    title: string;
    tour_type: "bike" | "road";
    slug: string;
  } | null;
}

export interface Tour {
  id: string;
  title: string;
  tour_type: "bike" | "road";
  slug: string;
  summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface TourMetrics {
  distance_km?: number | null;
  elevation_gain_m?: number | null;
  duration_hours?: number | null;
  point_count?: number;
  difficulty?: "easy" | "moderate" | "challenging" | null;
  route_type?: string | null;
  start_location?: string | null;
}

export interface TourDetail extends Tour {
  markdown: string | null;
  has_gpx: boolean;
  metrics?: TourMetrics;
}

export interface Session {
  id: string;
  title: string | null;
  language: string;
  tour_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail extends Session {
  messages: { role: string; content: string }[];
  artifacts: {
    gpx: string | null;
    map: {
      waypoints: [number, number][];
      routes: [number, number][][];
      pois: { lat: number; lon: number; name: string; category?: string }[];
    };
    elevation: [number, number][];
  } | null;
}

export function clientHeaders(): HeadersInit {
  let token = localStorage.getItem("client_token");
  if (!token) {
    token = crypto.randomUUID();
    localStorage.setItem("client_token", token);
  }
  return { "X-Client-Token": token };
}

/**
 * Fetch list of tours, optionally filtered by type.
 */
export async function fetchTours(tourType?: "bike" | "road"): Promise<Tour[]> {
  const params = tourType ? `?tour_type=${tourType}` : "";
  const response = await fetch(`/api/tours${params}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch tours: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch tour details including markdown content.
 */
export async function fetchTourDetail(tourType: string, slug: string): Promise<TourDetail> {
  const response = await fetch(`/api/tours/${tourType}/${slug}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch tour: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch GPX content for a tour.
 */
export async function fetchTourGpx(tourType: string, slug: string): Promise<string> {
  const response = await fetch(`/api/tours/${tourType}/${slug}/gpx`);
  if (!response.ok) {
    throw new Error(`Failed to fetch GPX: ${response.status}`);
  }
  return response.text();
}

/**
 * Save a new tour.
 */
export async function saveTour(params: {
  markdown: string;
  tour_type: "bike" | "road";
  gpx?: string;
  session_id?: string;
}): Promise<Tour> {
  const response = await fetch("/api/tours", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    throw new Error(`Failed to save tour: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch list of sessions.
 */
export async function fetchSessions(limit = 50): Promise<Session[]> {
  const response = await fetch(`/api/sessions?limit=${limit}`, { headers: clientHeaders() });
  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch the last-viewed tour for a session.
 */
export async function fetchLastViewedTour(sessionId: string): Promise<LastViewedTourResponse> {
  const response = await fetch(`/api/sessions/${sessionId}/last-viewed`, {
    headers: clientHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch last viewed tour: ${response.status}`);
  }
  return response.json();
}

/**
 * Save the last-viewed tour for a session.
 */
export async function saveLastViewedTour(sessionId: string, tourId: string): Promise<void> {
  const response = await fetch(`/api/sessions/${sessionId}/last-viewed`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...clientHeaders() },
    body: JSON.stringify({ tour_id: tourId }),
  });

  if (!response.ok) {
    throw new Error(`Failed to save last viewed tour: ${response.status}`);
  }
}

/**
 * Fetch session details including messages.
 */
export async function fetchSessionDetail(sessionId: string): Promise<SessionDetail> {
  const response = await fetch(`/api/sessions/${sessionId}`, { headers: clientHeaders() });
  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.status}`);
  }
  return response.json();
}

/**
 * Delete a tour (move to trash).
 */
export async function deleteTour(tourType: string, slug: string): Promise<void> {
  const response = await fetch(`/api/tours/${tourType}/${slug}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Failed to delete tour: ${response.status}`);
  }
}

/**
 * Trash item returned from the API.
 */
export interface TrashItem {
  tour_type: "bike" | "road";
  trash_name: string;
  original_slug: string;
  deleted_at: string | null;
  title: string;
}

/**
 * Rename a tour title.
 */
export async function renameTour(tourType: string, slug: string, title: string): Promise<Tour> {
  const response = await fetch(`/api/tours/${tourType}/${slug}/rename`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw new Error(`Failed to rename tour: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch list of tours in trash.
 */
export async function fetchTrash(): Promise<TrashItem[]> {
  const response = await fetch("/api/trash");
  if (!response.ok) {
    throw new Error(`Failed to fetch trash: ${response.status}`);
  }
  return response.json();
}

/**
 * Restore a tour from trash.
 */
export async function restoreFromTrash(tourType: string, trashName: string): Promise<Tour> {
  const response = await fetch(`/api/trash/${tourType}/${trashName}/restore`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Failed to restore tour: ${response.status}`);
  }
  return response.json();
}

/**
 * Permanently delete a tour from trash.
 */
export async function deleteFromTrash(tourType: string, trashName: string): Promise<void> {
  const response = await fetch(`/api/trash/${tourType}/${trashName}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Failed to delete from trash: ${response.status}`);
  }
}

/**
 * Empty the entire trash.
 */
export async function emptyTrash(): Promise<number> {
  const response = await fetch("/api/trash", {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Failed to empty trash: ${response.status}`);
  }
  const data = await response.json();
  return data.deleted_count;
}

/**
 * Delete a single session.
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`/api/sessions/${sessionId}`, {
    method: "DELETE",
    headers: clientHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to delete session: ${response.status}`);
  }
}

/**
 * Delete all sessions.
 */
export async function deleteAllSessions(): Promise<number> {
  const response = await fetch("/api/sessions", {
    method: "DELETE",
    headers: clientHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to delete all sessions: ${response.status}`);
  }
  const data = await response.json();
  return data.deleted_count;
}
