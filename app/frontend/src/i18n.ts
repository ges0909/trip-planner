export type Lang = "de" | "en";

const messages = {
  subtitle: {
    de: "Roadtrips in Europa · Radtouren in Berlin/Brandenburg · Wanderungen (bald)",
    en: "Road trips across Europe · Cycling tours in Berlin/Brandenburg · Hiking (coming soon)",
  },
  placeholder: {
    de: "Erstelle für jeden der 7 Tage einen ausführlichen Tagesplan. Beende die Antwort erst nach Tag 7.",
    en: "Create a detailed daily plan for each of the 7 days. Do not finish the response until day 7.",
  },
  btnSend: { de: "Los", en: "Go" },
  cancel: { de: "Abbrechen", en: "Cancel" },
  btnMarkdown: { de: "Markdown", en: "Markdown" },
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
  close: { de: "Schließen", en: "Close" },
  toolCall: { de: "Tool: {name}", en: "Tool: {name}" },
  modelCall: {
    de: "Modell-Aufruf {iteration}: {modelId}",
    en: "Model request {iteration}: {modelId}",
  },
  activityFeedTitle: { de: "Aktivitätsverlauf ({count})", en: "Activity feed ({count})" },
  collapseActivityFeed: { de: "Aktivitätsverlauf einklappen", en: "Collapse activity feed" },
  expandActivityFeed: { de: "Aktivitätsverlauf ausklappen", en: "Expand activity feed" },
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
  tourSaved: { de: "Tour gespeichert", en: "Tour saved" },
  sessionHistory: { de: "Chat-Verlauf", en: "Chat history" },
  noSessions: { de: "Noch keine Chats gespeichert.", en: "No saved chats yet." },
  loadSession: { de: "Chat öffnen", en: "Open chat" },
  delete: { de: "Löschen", en: "Delete" },
  deleteSession: { de: "Chat löschen", en: "Delete chat" },
  deleteSessionConfirmTitle: { de: "Chat löschen?", en: "Delete chat?" },
  deleteSessionConfirm: {
    de: "Möchtest du diesen Chat-Verlauf wirklich löschen?",
    en: "Do you really want to delete this chat?",
  },
  clearAllSessions: { de: "Verlauf leeren", en: "Clear history" },
  clearAllSessionsConfirmTitle: {
    de: "Gesamten Verlauf leeren?",
    en: "Clear all history?",
  },
  clearAllSessionsConfirm: {
    de: "Möchtest du alle gespeicherten Chats wirklich unwiderruflich löschen?",
    en: "Do you really want to permanently delete all saved chats?",
  },
  trash: { de: "Papierkorb", en: "Trash" },
  trashEmpty: { de: "Papierkorb ist leer", en: "Trash is empty" },
  deletedOn: { de: "Gelöscht: {date}", en: "Deleted: {date}" },
  restore: { de: "Wiederherstellen", en: "Restore" },
  deletePermanently: { de: "Endgültig löschen", en: "Delete permanently" },
  deleteTourConfirmTitle: { de: "Tour löschen?", en: "Delete tour?" },
  deleteTourConfirm: {
    de: "„{title}“ wird in den Papierkorb verschoben.",
    en: "“{title}” will be moved to trash.",
  },
  deletePermanentlyConfirmTitle: { de: "Endgültig löschen?", en: "Delete permanently?" },
  deletePermanentlyConfirm: {
    de: "„{title}“ wird unwiderruflich gelöscht.",
    en: "“{title}” will be permanently deleted.",
  },
  downloadGpx: { de: "GPX herunterladen", en: "Download GPX" },
  showMap: { de: "Gesamtkarte anzeigen", en: "Show full map" },
  hideMap: { de: "Gesamtkarte ausblenden", en: "Hide full map" },
  rename: { de: "Umbenennen", en: "Rename" },
  save: { de: "Speichern", en: "Save" },
  renameTourTitle: { de: "Tour umbenennen", en: "Rename tour" },
} as const;

type MessageKey = keyof typeof messages;

export function t(key: MessageKey, lang: Lang, params?: Record<string, string | number>): string {
  let text = messages[key][lang];
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replace(`{${k}}`, String(v)) as typeof text;
    }
  }
  return text;
}
