import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import TourExportDropdown from "../src/components/TourExportDropdown.vue";

describe("TourExportDropdown Component", () => {
  it("renders export button", () => {
    const wrapper = mount(TourExportDropdown, {
      props: {
        markdown: "# Test Tour",
        gpx: "<gpx></gpx>",
        filename: "test-tour",
      },
    });

    expect(wrapper.text()).toContain("Exportieren & Teilen");
    expect(wrapper.text()).toContain("Export ▾");
  });

  it("opens dropdown on button click and renders export options", async () => {
    const wrapper = mount(TourExportDropdown, {
      props: {
        markdown: "# Test Tour",
        gpx: "<gpx></gpx>",
        filename: "test-tour",
      },
    });

    const exportBtn = wrapper.find("button");
    await exportBtn.trigger("click");

    expect(wrapper.text()).toContain("GPX Track herunterladen");
    expect(wrapper.text()).toContain("Markdown Kopieren");
    expect(wrapper.text()).toContain("Markdown Datei (.md)");
    expect(wrapper.text()).toContain("Drucken / Als PDF");
  });
});
