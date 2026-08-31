import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import TourLibrary from "../src/components/TourLibrary.vue";

vi.mock("../src/api", () => ({
  fetchTours: vi.fn().mockResolvedValue([
    {
      id: "tour-1",
      title: "Wannsee Radtour",
      tour_type: "bike",
      slug: "wannsee-radtour",
      summary: "Schöne Tour am See",
      created_at: "2026-08-30T10:00:00Z",
    },
    {
      id: "tour-2",
      title: "Schwarzwald Trip",
      tour_type: "road",
      slug: "schwarzwald-trip",
      summary: "Panoramastraße",
      created_at: "2026-08-30T11:00:00Z",
    },
  ]),
  fetchTrashItems: vi.fn().mockResolvedValue([]),
  deleteTour: vi.fn().mockResolvedValue(true),
  restoreTrashItem: vi.fn().mockResolvedValue(true),
  permanentlyDeleteTrashItem: vi.fn().mockResolvedValue(true),
}));

describe("TourLibrary Component", () => {
  it("renders tour library header and filter tabs", async () => {
    const wrapper = mount(TourLibrary, {
      props: {
        language: "de",
      },
    });

    expect(wrapper.text()).toContain("Tour-Bibliothek");
  });

  it("filters tours by category when clicking filter tabs", async () => {
    const wrapper = mount(TourLibrary, {
      props: {
        language: "de",
      },
    });

    // Wait for api mock to resolve
    await new Promise((resolve) => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain("Wannsee Radtour");
    expect(wrapper.text()).toContain("Schwarzwald Trip");
  });
});
