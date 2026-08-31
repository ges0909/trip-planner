import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import LanguageSelector from "../src/components/LanguageSelector.vue";

describe("LanguageSelector Component", () => {
  it("renders with current language code", () => {
    const wrapper = mount(LanguageSelector, {
      props: {
        modelValue: "de",
      },
    });

    expect(wrapper.text()).toContain("DE");
    expect(wrapper.find("svg").exists()).toBe(true);
  });

  it("toggles dropdown and emits update when language is clicked", async () => {
    const wrapper = mount(LanguageSelector, {
      props: {
        modelValue: "de",
      },
    });

    // Dropdown should be closed initially
    expect(wrapper.text()).not.toContain("English");

    // Click toggle button
    const button = wrapper.find("button");
    await button.trigger("click");

    expect(wrapper.text()).toContain("Deutsch");
    expect(wrapper.text()).toContain("English");

    // Click English option
    const options = wrapper.findAll("div button");
    const englishBtn = options.find((b) => b.text().includes("English"));
    expect(englishBtn).toBeDefined();
    await englishBtn?.trigger("click");

    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["en"]);
  });
});
