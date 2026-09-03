import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ConfirmDialog from "../src/components/ConfirmDialog.vue";

describe("ConfirmDialog Component", () => {
  it("renders when open is true with title and message", () => {
    const wrapper = mount(ConfirmDialog, {
      props: {
        open: true,
        title: "Tour löschen?",
        message: "Möchtest du diese Tour wirklich löschen?",
        confirmText: "Löschen",
        cancelText: "Abbrechen",
      },
      attachTo: document.body,
    });

    expect(document.body.textContent).toContain("Tour löschen?");
    expect(document.body.textContent).toContain("Möchtest du diese Tour wirklich löschen?");
    wrapper.unmount();
  });

  it("emits confirm and cancel events", async () => {
    const wrapper = mount(ConfirmDialog, {
      props: {
        open: true,
        title: "Test Dialog",
        message: "Test Message",
      },
      attachTo: document.body,
    });

    const buttons = document.body.querySelectorAll("button");
    expect(buttons.length).toBeGreaterThanOrEqual(2);

    // Cancel button
    buttons[0].click();
    expect(wrapper.emitted("cancel")).toBeTruthy();

    // Confirm button
    buttons[1].click();
    expect(wrapper.emitted("confirm")).toBeTruthy();

    wrapper.unmount();
  });
});
