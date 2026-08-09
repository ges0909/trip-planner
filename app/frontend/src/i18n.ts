export type Lang = "de" | "en";

const messages = {
  subtitle: {
    de: "Roadtrips in Europa · Radtouren in Berlin/Brandenburg · Wanderungen (bald)",
    en: "Road trips across Europe · Cycling tours in Berlin/Brandenburg · Hiking (coming soon)",
  },
  placeholder: {
    de: "z.B. Plane einen 2-Wochen Roadtrip an der spanischen Nordküste...",
    en: "e.g. Plan a 2-week road trip along the Spanish north coast...",
  },
  btnSend: { de: "Los", en: "Go" },
  btnMarkdown: { de: "Markdown", en: "Markdown" },
  historyTitle: { de: "Letzte Anfragen", en: "Recent queries" },
  historyClear: { de: "Verlauf löschen", en: "Clear history" },
  errorNoResponse: {
    de: "Keine Antwort vom Server erhalten. Bitte prüfe das Backend-Log.",
    en: "No response from server. Please check the backend log.",
  },
  errorConnection: {
    de: "Verbindung zum Server fehlgeschlagen. Ist das Backend gestartet?",
    en: "Connection to server failed. Is the backend running?",
  },
  errorServer: {
    de: "Server-Fehler ({status}). Bitte prüfe das Backend-Log.",
    en: "Server error ({status}). Please check the backend log.",
  },
  // Tour Library
  tourLibrary: { de: "Tour-Bibliothek", en: "Tour Library" },
  all: { de: "Alle", en: "All" },
  bikeTours: { de: "Radtouren", en: "Bike Tours" },
  roadTrips: { de: "Roadtrips", en: "Road Trips" },
  noTours: {
    de: "Noch keine Touren gespeichert.",
    en: "No tours saved yet.",
  },
  refresh: { de: "Aktualisieren", en: "Refresh" },
  saveTour: { de: "Tour speichern", en: "Save Tour" },
  downloadGpx: { de: "GPX herunterladen", en: "Download GPX" },
  showMap: { de: "Gesamtkarte anzeigen", en: "Show full map" },
  hideMap: { de: "Gesamtkarte ausblenden", en: "Hide full map" },
} as const;

type MessageKey = keyof typeof messages;

export function t(
  key: MessageKey,
  lang: Lang,
  params?: Record<string, string | number>,
): string {
  let text = messages[key][lang];
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replace(`{${k}}`, String(v)) as typeof text;
    }
  }
  return text;
}
