/**
 * GPX parsing utilities.
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
