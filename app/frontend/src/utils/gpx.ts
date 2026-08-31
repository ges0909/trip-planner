/**
 * Calculate haversine distance in meters between two [lat, lon] coordinates.
 */
function haversineDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000; // Earth radius in meters
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Parse GPX string to extract cumulative distance (km) and elevation (m) pairs [[dist_km, ele_m], ...].
 */
export function parseGpxElevation(gpx: string): [number, number][] {
  const profile: [number, number][] = [];
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(gpx, "application/xml");
    const trkpts = doc.getElementsByTagName("trkpt");

    let totalDistMeters = 0;
    let prevLat: number | null = null;
    let prevLon: number | null = null;

    for (let i = 0; i < trkpts.length; i += 1) {
      const pt = trkpts[i];
      const lat = parseFloat(pt.getAttribute("lat") || "");
      const lon = parseFloat(pt.getAttribute("lon") || "");
      const eleEl = pt.getElementsByTagName("ele")[0];
      const ele = eleEl ? parseFloat(eleEl.textContent || "") : NaN;

      if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
        if (prevLat !== null && prevLon !== null) {
          totalDistMeters += haversineDistance(prevLat, prevLon, lat, lon);
        }
        prevLat = lat;
        prevLon = lon;

        if (!Number.isNaN(ele)) {
          const distKm = parseFloat((totalDistMeters / 1000).toFixed(2));
          profile.push([distKm, ele]);
        }
      }
    }
  } catch {
    return profile;
  }
  return profile;
}

/**
 * Parse GPX route coordinates [[lat, lon], ...].
 */
export function parseGpxRoute(gpx: string): [number, number][][] {
  const routes: [number, number][][] = [];

  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(gpx, "application/xml");
    const tracks = doc.getElementsByTagName("trk");

    for (let i = 0; i < tracks.length; i += 1) {
      const trk = tracks[i];
      const route: [number, number][] = [];
      const trkpts = trk.getElementsByTagName("trkpt");

      for (let j = 0; j < trkpts.length; j += 1) {
        const pt = trkpts[j];
        const lat = parseFloat(pt.getAttribute("lat") || "");
        const lon = parseFloat(pt.getAttribute("lon") || "");

        if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
          route.push([lat, lon]);
        }
      }

      if (route.length > 0) {
        routes.push(route);
      }
    }
  } catch {
    return routes;
  }

  return routes;
}
