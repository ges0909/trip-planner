import type { TourMetrics } from "../api";

export type TourMetaItemType = "default" | "success" | "warning" | "danger" | "purple" | "sky";

export interface TourMetaItem {
  label: string;
  type: TourMetaItemType;
}

export function extractWeatherInfo(markdown: string): string | null {
  const md = markdown || "";
  const match = md.match(
    /(?:wetter|weather|vorhersage)[:\s]+([^\n.,]+(?:\d+°C|\d+\s*grad)[^\n.]*)/i,
  );
  if (match) return match[1].trim();

  const tempMatch = md.match(
    /(\d+\s*°C[^\n.]*sonnig|\d+\s*°C[^\n.]*bewölkt|sonnig[^\n.]*\d+\s*°C)/i,
  );
  return tempMatch ? tempMatch[1].trim() : null;
}

export function extractDistanceInfo(markdown: string): string | null {
  const md = markdown || "";
  const match = md.match(
    /(?:Gesamtdistanz|Distanz|Strecke|Gesamtlänge|Länge|Distance|Length)[:\s]+(?:ca\.\s*)?([0-9.,]+\s*(?:km|Kilometer))/i,
  );
  return match ? match[1].trim() : null;
}

export function extractDurationInfo(markdown: string): string | null {
  const md = markdown || "";
  const match = md.match(
    /(?:Gesamtdauer|Reisedauer|Dauer|Fahrzeit|Duration|Time)[:\s]+(?:ca\.\s*)?([0-9.,]+\s*(?:Std\.?|Stunden|Tage|Days|h))/i,
  );
  return match ? match[1].trim() : null;
}

export function buildTourMetaItems(
  metrics: TourMetrics | undefined,
  markdown: string,
): TourMetaItem[] {
  const items: TourMetaItem[] = [];
  const weatherInfo = extractWeatherInfo(markdown);

  if (metrics?.distance_km) {
    items.push({ label: `${metrics.distance_km} km`, type: "default" });
  } else {
    const parsedDist = extractDistanceInfo(markdown);
    if (parsedDist) items.push({ label: parsedDist, type: "default" });
  }

  if (metrics?.elevation_gain_m) {
    items.push({ label: `${metrics.elevation_gain_m} hm`, type: "success" });
  }

  if (metrics?.duration_hours) {
    items.push({ label: `${metrics.duration_hours} Std.`, type: "warning" });
  } else {
    const parsedDur = extractDurationInfo(markdown);
    if (parsedDur) items.push({ label: parsedDur, type: "warning" });
  }

  if (weatherInfo) {
    items.push({ label: weatherInfo, type: "sky" });
  }

  if (metrics?.route_type) {
    items.push({ label: metrics.route_type, type: "purple" });
  }

  if (metrics?.difficulty) {
    const difficultyLabel = metrics.difficulty;
    items.push({
      label: difficultyLabel,
      type:
        difficultyLabel === "easy"
          ? "success"
          : difficultyLabel === "moderate"
            ? "warning"
            : "danger",
    });
  }

  return items;
}
