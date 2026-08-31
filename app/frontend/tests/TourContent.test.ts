import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import TourContent from "../src/components/TourContent.vue";

describe("TourContent Component", () => {
  it("renders sanitized markdown content and headings", () => {
    const markdown = "# Berlin nach Potsdam\n\nEine schöne Route durch den Grunewald.";
    const wrapper = mount(TourContent, {
      props: {
        markdown,
        gpx: "",
      },
    });

    expect(wrapper.html()).toContain("Berlin nach Potsdam");
    expect(wrapper.html()).toContain("Grunewald");
  });

  it("provides download links for markdown and GPX", async () => {
    const markdown = "# Spreewald Tour";
    const gpx = "<gpx></gpx>";
    const wrapper = mount(TourContent, {
      props: {
        markdown,
        gpx,
      },
    });

    const exportBtn = wrapper.find("button");
    expect(exportBtn.exists()).toBe(true);
    await exportBtn.trigger("click");

    const links = wrapper.findAll("a");
    expect(links.length).toBe(2);

    const gpxLink = links[0];
    expect(gpxLink.attributes("download")).toBe("spreewald-tour.gpx");

    const mdLink = links[1];
    expect(mdLink.attributes("download")).toBe("spreewald-tour.md");
  });

  it("renders structured metric badges when metrics are provided", () => {
    const wrapper = mount(TourContent, {
      props: {
        markdown: "# Tour",
        gpx: "",
        metrics: {
          distance_km: 42.5,
          elevation_gain_m: 350,
          duration_hours: 2.5,
          difficulty: "moderate",
          route_type: "Rundtour",
        },
      },
    });

    expect(wrapper.text()).toContain("42.5 km");
    expect(wrapper.text()).toContain("350 hm");
    expect(wrapper.text()).toContain("2.5 Std.");
    expect(wrapper.text()).toContain("Rundtour");
    expect(wrapper.text()).toContain("moderate");
  });

  it("filters out unrendered relative image references and broken bullets", () => {
    const markdown = `# Ostsee Roadtrip
### Tag 1 · Berlin → Świnoujście
* Karte:

![Tag 01](maps/tag-01-berlin-swinoujscie.png)

[📍 Google Maps](https://www.google.com/maps/dir/52.52,13.40/53.91,14.24)
`;
    const wrapper = mount(TourContent, {
      props: {
        markdown,
        gpx: "",
      },
    });

    const prose = wrapper.find(".prose");
    expect(prose.html()).not.toContain("tag-01-berlin-swinoujscie.png");
    expect(prose.html()).not.toContain("<img");
    expect(prose.html()).not.toContain("Karte:");
    expect(prose.html()).toContain("Google Maps");
    expect(prose.html()).toContain("Berlin → Świnoujście");
  });

  it("renders HTTP/HTTPS POI images with figure and figcaption", () => {
    const markdown =
      "# Bodensee Tour\n\n![Brandenburger Tor](https://images.unsplash.com/photo-12345)";
    const wrapper = mount(TourContent, {
      props: {
        markdown,
        gpx: "",
      },
    });

    const html = wrapper.html();
    expect(html).toContain("<figure");
    expect(html).toContain("<figcaption");
    expect(html).toContain("Brandenburger Tor");
    expect(html).toContain("https://images.unsplash.com/photo-12345");
  });

  it("renders standalone YouTube links as responsive video embeds", () => {
    const markdown = "# Schwarzwald Video Highlight\n\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ";
    const wrapper = mount(TourContent, {
      props: {
        markdown,
        gpx: "",
      },
    });

    const html = wrapper.html();
    expect(html).toContain("<iframe");
    expect(html).toContain("youtube-nocookie.com/embed/dQw4w9WgXcQ");
    expect(html).toContain("aspect-video");
  });
});
