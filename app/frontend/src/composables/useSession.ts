/**
 * Session helpers for persistent browser sessions.
 */
import { ref } from "vue";
import { fetchLastViewedTour, type Tour } from "../api";

export function useSession() {
  const sessionId = ref<string | null>(null);

  function getOrCreateSessionId(): string {
    const stored = localStorage.getItem("session_id");
    if (stored) {
      return stored;
    }

    const generated = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });

    localStorage.setItem("session_id", generated);
    return generated;
  }

  async function restoreLastViewedTour(
    onRestore: (tour: Tour) => Promise<void> | void,
  ): Promise<void> {
    const sid = getOrCreateSessionId();
    sessionId.value = sid;

    try {
      const data = await fetchLastViewedTour(sid);
      if (!data.tour) {
        return;
      }

      await onRestore({
        id: data.tour.id,
        tour_type: data.tour.tour_type,
        slug: data.tour.slug,
      } as Tour);
    } catch {
      // Ignore restore errors and continue without restoring a tour.
    }
  }

  return {
    sessionId,
    getOrCreateSessionId,
    restoreLastViewedTour,
  };
}
