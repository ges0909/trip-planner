import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import CommandPalette from "../src/components/CommandPalette.vue";

vi.mock("../src/api", () => ({
  fetchTours: vi.fn().mockResolvedValue([
    {
      id: "tour-1",
      title: "Wannsee Radtour",
      tour_type: "bike",
      slug: "wannsee-radtour",
      created_at: "2026-08-30",
    },
  ]),
  fetchSessions: vi.fn().mockResolvedValue([
    {
      id: "sess-1",
      title: "Berliner Radtour",
      created_at: "2026-08-30",
      message_count: 3,
    },
  ]),
}));

describe("CommandPalette", () => {
  it("does not render modal content when isOpen is false", () => {
    const wrapper = mount(CommandPalette, {
      props: {
        isOpen: false,
        language: "de",
        isDark: true,
      },
    });

    expect(wrapper.find("input").exists()).toBe(false);
  });

  it("renders search input and responds to user filtering when isOpen is true", async () => {
    const wrapper = mount(CommandPalette, {
      props: {
        isOpen: true,
        language: "de",
        isDark: true,
      },
      global: {
        stubs: {
          Teleport: true,
        },
      },
    });

    await wrapper.vm.$nextTick();
    await new Promise((r) => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    const input = wrapper.find("input");
    expect(input.exists()).toBe(true);

    await input.setValue("Wannsee");
    await new Promise((r) => setTimeout(r, 50));
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("Wannsee");
  });
});
