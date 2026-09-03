import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import TourMap from "../src/components/TourMap.vue";

describe("TourMap Component", () => {
  it("renders map container and toolbar buttons", () => {
    const wrapper = mount(TourMap, {
      props: {
        waypoints: [],
        routes: [],
        pois: [],
        elevation: [],
        isDark: false,
      },
    });

    expect(wrapper.find("[title='Standard Karte']").exists()).toBe(true);
    expect(wrapper.find("[title='Topografische Karte']").exists()).toBe(true);
    expect(wrapper.find("[title='Dunkle Karte']").exists()).toBe(true);
  });

  it("renders POI category filter chips when POIs are present", () => {
    const wrapper = mount(TourMap, {
      props: {
        waypoints: [],
        routes: [],
        pois: [
          { lat: 52.5, lon: 13.4, name: "Schloss Charlottenburg", category: "castle" },
          { lat: 52.51, lon: 13.41, name: "Café Einstein", category: "cafe" },
          { lat: 52.52, lon: 13.42, name: "Strandbad Wannsee", category: "swimming" },
        ],
        elevation: [],
        isDark: false,
      },
    });

    expect(wrapper.text()).toContain("Alle (3)");
    expect(wrapper.text()).toContain("Sehenswürdigkeiten");
    expect(wrapper.text()).toContain("Einkehr");
    expect(wrapper.text()).toContain("Baden");
  });

  it("renders elevation profile stats and weather timeline", () => {
    const wrapper = mount(TourMap, {
      props: {
        waypoints: [],
        routes: [],
        pois: [],
        elevation: [
          [0, 50],
          [10, 150],
          [20, 80],
        ],
        isDark: false,
      },
    });

    expect(wrapper.text()).toContain("Höhenprofil");
    expect(wrapper.text()).toContain("20.0 km");
    expect(wrapper.text()).toContain("Wetterverlauf:");
  });
});
