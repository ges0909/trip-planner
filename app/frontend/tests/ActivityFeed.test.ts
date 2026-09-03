import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ActivityFeed from "../src/components/ActivityFeed.vue";

describe("ActivityFeed Component", () => {
  it("does not render when events array is empty", () => {
    const wrapper = mount(ActivityFeed, {
      props: {
        events: [],
        isLoading: false,
        language: "de",
        isExpanded: true,
      },
    });

    expect(wrapper.find("div").exists()).toBe(false);
  });

  it("renders activity events and tool calls", () => {
    const wrapper = mount(ActivityFeed, {
      props: {
        events: [
          { type: "model", iteration: 1, modelId: "llama-3" },
          { type: "tool", name: "calculate_route" },
          { type: "status", message: "Route optimiert" },
        ],
        isLoading: false,
        language: "de",
        isExpanded: true,
      },
    });

    expect(wrapper.text()).toContain("Aktivitätsverlauf (3)");
    expect(wrapper.text()).toContain("calculate_route");
    expect(wrapper.text()).toContain("Route optimiert");
  });

  it("emits toggleExpanded when clicked", async () => {
    const wrapper = mount(ActivityFeed, {
      props: {
        events: [{ type: "status", message: "Laden..." }],
        isLoading: true,
        language: "de",
        isExpanded: false,
      },
    });

    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("toggleExpanded")).toBeTruthy();
  });
});
