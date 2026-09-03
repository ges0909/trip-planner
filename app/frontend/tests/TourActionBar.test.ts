import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import TourActionBar from "../src/components/TourActionBar.vue";

describe("TourActionBar Component", () => {
  it("does not render when no meta items, map data, or generated tour exist", () => {
    const wrapper = mount(TourActionBar, {
      props: {
        metaItems: [],
        hasMapData: false,
        isMapVisible: false,
        hasGeneratedTour: false,
        isTourSaved: false,
        isLoading: false,
        language: "de",
      },
    });

    expect(wrapper.find("div").exists()).toBe(false);
  });

  it("renders metric badges when meta items are provided", () => {
    const wrapper = mount(TourActionBar, {
      props: {
        metaItems: [
          { label: "120 km", type: "default" },
          { label: "850 hm", type: "success" },
          { label: "3.5 Std.", type: "warning" },
        ],
        hasMapData: false,
        isMapVisible: false,
        hasGeneratedTour: false,
        isTourSaved: false,
        isLoading: false,
        language: "de",
      },
    });

    expect(wrapper.text()).toContain("120 km");
    expect(wrapper.text()).toContain("850 hm");
    expect(wrapper.text()).toContain("3.5 Std.");
  });

  it("emits toggleMap and saveTour on button clicks", async () => {
    const wrapper = mount(TourActionBar, {
      props: {
        metaItems: [],
        hasMapData: true,
        isMapVisible: true,
        hasGeneratedTour: true,
        isTourSaved: false,
        isLoading: false,
        language: "de",
      },
    });

    const buttons = wrapper.findAll("button");
    expect(buttons.length).toBe(2);

    await buttons[0].trigger("click");
    expect(wrapper.emitted("toggleMap")).toBeTruthy();

    await buttons[1].trigger("click");
    expect(wrapper.emitted("saveTour")).toBeTruthy();
  });
});
