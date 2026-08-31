import { describe, expect, it } from "vitest";
import { parseGpxElevation, parseGpxRoute } from "../src/utils/gpx";

describe("parseGpxRoute", () => {
  it("parses valid GPX trackpoints into coordinate pairs", () => {
    const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="TripPlanner">
  <trk>
    <name>Berlin Tour</name>
    <trkseg>
      <trkpt lat="52.5200" lon="13.4050"></trkpt>
      <trkpt lat="52.5300" lon="13.4150"></trkpt>
    </trkseg>
  </trk>
</gpx>`;

    const routes = parseGpxRoute(gpx);
    expect(routes).toHaveLength(1);
    expect(routes[0]).toEqual([
      [52.52, 13.405],
      [52.53, 13.415],
    ]);
  });

  it("handles multiple tracks in a single GPX", () => {
    const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="52.5" lon="13.4"></trkpt>
    </trkseg>
  </trk>
  <trk>
    <trkseg>
      <trkpt lat="52.6" lon="13.5"></trkpt>
    </trkseg>
  </trk>
</gpx>`;

    const routes = parseGpxRoute(gpx);
    expect(routes).toHaveLength(2);
    expect(routes[0]).toEqual([[52.5, 13.4]]);
    expect(routes[1]).toEqual([[52.6, 13.5]]);
  });

  it("returns empty array for invalid or empty GPX string", () => {
    expect(parseGpxRoute("")).toEqual([]);
    expect(parseGpxRoute("not xml at all")).toEqual([]);
    expect(parseGpxRoute("<gpx></gpx>")).toEqual([]);
  });

  it("ignores trackpoints with NaN coordinates", () => {
    const gpx = `<gpx><trk><trkseg>
      <trkpt lat="invalid" lon="13.4"></trkpt>
      <trkpt lat="52.5" lon="13.4"></trkpt>
    </trkseg></trk></gpx>`;

    const routes = parseGpxRoute(gpx);
    expect(routes).toHaveLength(1);
    expect(routes[0]).toEqual([[52.5, 13.4]]);
  });

  it("parses elevation profile data from GPX trackpoints", () => {
    const gpx = `<gpx><trk><trkseg>
      <trkpt lat="52.52" lon="13.40"><ele>100</ele></trkpt>
      <trkpt lat="52.53" lon="13.41"><ele>150</ele></trkpt>
    </trkseg></trk></gpx>`;

    const profile = parseGpxElevation(gpx);
    expect(profile).toHaveLength(2);
    expect(profile[0]).toEqual([0, 100]);
    expect(profile[1][0]).toBeGreaterThan(0);
    expect(profile[1][1]).toBe(150);
  });
});
