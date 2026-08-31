import { describe, expect, it } from "vitest";
import { t } from "../src/i18n";

describe("i18n helper", () => {
  it("translates static messages in German and English", () => {
    expect(t("btnSend", "de")).toBe("Los");
    expect(t("btnSend", "en")).toBe("Go");
    expect(t("tourLibrary", "de")).toBe("Tour-Bibliothek");
    expect(t("tourLibrary", "en")).toBe("Tour Library");
  });

  it("interpolates parameters into translated strings", () => {
    expect(t("toolCall", "de", { name: "brouter" })).toBe("Tool: brouter");
    expect(t("modelCall", "en", { iteration: 2, modelId: "llama-3" })).toBe(
      "Model request 2: llama-3",
    );
    expect(t("activityFeedTitle", "de", { count: 5 })).toBe("Aktivitätsverlauf (5)");
  });
});
