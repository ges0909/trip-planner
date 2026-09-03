import { beforeEach, describe, expect, it } from "vitest";
import { useAppPreferences } from "../src/composables/useAppPreferences";

describe("useAppPreferences", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
    Object.defineProperty(window.navigator, "language", {
      value: "en-US",
      configurable: true,
    });
  });

  it("uses the stored language when available", () => {
    localStorage.setItem("tourpilot_lang", "de");

    const { language } = useAppPreferences();

    expect(language.value).toBe("de");
  });

  it("falls back to the browser language when no stored preference exists", () => {
    const { language } = useAppPreferences();

    expect(language.value).toBe("en");
  });

  it("applies the stored dark mode preference and updates the html class", () => {
    localStorage.setItem("tourpilot_theme", "dark");

    const { isDark } = useAppPreferences();

    expect(isDark.value).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });
});
