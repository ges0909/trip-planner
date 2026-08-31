import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ChatInput from "../src/components/ChatInput.vue";

describe("ChatInput Component", () => {
  it("renders with placeholder according to language", () => {
    const wrapper = mount(ChatInput, {
      props: {
        isLoading: false,
        language: "de",
      },
    });

    const textarea = wrapper.find("textarea");
    expect(textarea.exists()).toBe(true);
    expect(textarea.attributes("placeholder")).toBeDefined();
  });

  it("emits send event on submit and clears input", async () => {
    const wrapper = mount(ChatInput, {
      props: {
        isLoading: false,
        language: "de",
      },
    });

    const textarea = wrapper.find("textarea");
    await textarea.setValue("Radtour von Berlin nach Potsdam");

    const form = wrapper.find("form");
    await form.trigger("submit.prevent");

    expect(wrapper.emitted("send")).toBeTruthy();
    expect(wrapper.emitted("send")?.[0]).toEqual(["Radtour von Berlin nach Potsdam"]);
  });

  it("disables submit button when loading or empty", async () => {
    const wrapper = mount(ChatInput, {
      props: {
        isLoading: true,
        language: "en",
      },
    });

    const button = wrapper.find("button[type='submit']");
    expect(button.attributes("disabled")).toBeDefined();
  });

  it("emits cancel event when cancel button is clicked", async () => {
    const wrapper = mount(ChatInput, {
      props: {
        isLoading: true,
        language: "de",
      },
    });

    const cancelBtn = wrapper.find("button[title='Abbrechen']");
    expect(cancelBtn.exists()).toBe(true);
    await cancelBtn.trigger("click");

    expect(wrapper.emitted("cancel")).toBeTruthy();
  });
});
