import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../src/api";
import SessionHistory from "../src/components/SessionHistory.vue";

vi.mock("../src/api", () => ({
  fetchSessions: vi.fn(),
  deleteSession: vi.fn(),
  deleteAllSessions: vi.fn(),
}));

describe("SessionHistory Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("toggles open and fetches sessions", async () => {
    const mockSessions = [
      {
        id: "sess-1",
        title: "Ostsee Roadtrip",
        language: "de",
        tour_type: "road",
        created_at: "2026-08-30T10:00:00Z",
        updated_at: "2026-08-30T10:00:00Z",
      },
    ];
    vi.mocked(api.fetchSessions).mockResolvedValue(mockSessions);

    const wrapper = mount(SessionHistory, {
      props: {
        language: "de",
        isLoading: false,
      },
    });

    const toggleBtn = wrapper.find("button");
    await toggleBtn.trigger("click");

    expect(api.fetchSessions).toHaveBeenCalled();
    expect(wrapper.text()).toContain("Ostsee Roadtrip");
  });

  it("opens confirmation dialog and deletes single session on confirm", async () => {
    const mockSessions = [
      {
        id: "sess-1",
        title: "Ostsee Roadtrip",
        language: "de",
        tour_type: "road",
        created_at: "2026-08-30T10:00:00Z",
        updated_at: "2026-08-30T10:00:00Z",
      },
    ];
    vi.mocked(api.fetchSessions).mockResolvedValue(mockSessions);
    vi.mocked(api.deleteSession).mockResolvedValue();

    const wrapper = mount(SessionHistory, {
      props: {
        language: "de",
        isLoading: false,
      },
      attachTo: document.body,
    });

    await wrapper.find("button").trigger("click");

    const deleteBtn = wrapper.find("button[title='Chat löschen']");
    expect(deleteBtn.exists()).toBe(true);
    await deleteBtn.trigger("click");

    // Modal is now open in body
    const modal = document.body.querySelector("[role='dialog']");
    expect(modal).not.toBeNull();
    expect(modal?.textContent).toContain("Chat löschen?");
    expect(modal?.textContent).toContain("Ostsee Roadtrip");

    // Click confirm "Löschen" button inside modal
    const confirmBtn = Array.from(modal?.querySelectorAll("button") || []).find((b) =>
      b.textContent?.includes("Löschen"),
    );
    expect(confirmBtn).toBeDefined();
    confirmBtn?.click();
    await wrapper.vm.$nextTick();

    expect(api.deleteSession).toHaveBeenCalledWith("sess-1");
    expect(wrapper.emitted("deleted")).toBeTruthy();
    expect(wrapper.emitted("deleted")?.[0]).toEqual(["sess-1"]);

    wrapper.unmount();
  });

  it("opens confirmation dialog and clears all sessions on confirm", async () => {
    const mockSessions = [
      {
        id: "sess-1",
        title: "Ostsee Roadtrip",
        language: "de",
        tour_type: "road",
        created_at: "2026-08-30T10:00:00Z",
        updated_at: "2026-08-30T10:00:00Z",
      },
    ];
    vi.mocked(api.fetchSessions).mockResolvedValue(mockSessions);
    vi.mocked(api.deleteAllSessions).mockResolvedValue(1);

    const wrapper = mount(SessionHistory, {
      props: {
        language: "de",
        isLoading: false,
      },
      attachTo: document.body,
    });

    await wrapper.find("button").trigger("click");

    const clearAllBtn = wrapper.findAll("button").find((b) => b.text().includes("Verlauf leeren"));
    expect(clearAllBtn).toBeDefined();
    await clearAllBtn?.trigger("click");

    // Modal is now open
    const modal = document.body.querySelector("[role='dialog']");
    expect(modal).not.toBeNull();
    expect(modal?.textContent).toContain("Gesamten Verlauf leeren?");

    // Click confirm "Löschen" button inside modal
    const confirmBtn = Array.from(modal?.querySelectorAll("button") || []).find((b) =>
      b.textContent?.includes("Löschen"),
    );
    expect(confirmBtn).toBeDefined();
    confirmBtn?.click();
    await wrapper.vm.$nextTick();

    expect(api.deleteAllSessions).toHaveBeenCalled();
    expect(wrapper.emitted("cleared")).toBeTruthy();

    wrapper.unmount();
  });
});
