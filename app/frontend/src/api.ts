/**
 * API client for the Trip Planner backend.
 */

export interface Tour {
  id: string;
  title: string;
  tour_type: "bike" | "road";
  slug: string;
  summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface TourDetail extends Tour {
  markdown: string | null;
  has_gpx: boolean;
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
export async function fetchTourDetail(
  tourType: string,
  slug: string,
): Promise<TourDetail> {
  const response = await fetch(`/api/tours/${tourType}/${slug}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch tour: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch GPX content for a tour.
 */
export async function fetchTourGpx(
  tourType: string,
  slug: string,
): Promise<string> {
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
  const response = await fetch(`/api/sessions?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch session details including messages.
 */
export async function fetchSessionDetail(
  sessionId: string,
): Promise<SessionDetail> {
  const response = await fetch(`/api/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.status}`);
  }
  return response.json();
}
