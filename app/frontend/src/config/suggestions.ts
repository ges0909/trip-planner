export interface PromptSuggestion {
  emoji: string;
  badgeClass: string;
  tag: string;
  title: string;
  prompt: string;
}

export function getPromptSuggestions(lang: "de" | "en"): PromptSuggestion[] {
  if (lang === "de") {
    return [
      {
        emoji: "🚴",
        tag: "Radtour",
        title: "Spreewald Gurkenradweg",
        prompt:
          "Erstelle eine 2-Tages-Radtour durch den Spreewald mit Start in Lübbenau. Max. 45 km pro Tag, ebene Strecke, schöne Einkehrmöglichkeiten.",
        badgeClass: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300",
      },
      {
        emoji: "🚗",
        tag: "Roadtrip",
        title: "Schwarzwald Hochstraße",
        prompt:
          "Plane einen 3-Tage-Roadtrip über die Schwarzwald-Hochstraße von Baden-Baden nach Freudenstadt mit Panorama-Aussichtspunkten.",
        badgeClass: "bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300",
      },
      {
        emoji: "🏰",
        tag: "Kultur",
        title: "Schlösser-Tour Potsdam",
        prompt:
          "Tagestour per Fahrrad zu den schönsten Schlössern in Potsdam und Umgebung. Inklusive Park Sanssouci und Cecilienhof.",
        badgeClass: "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300",
      },
    ];
  }

  return [
    {
      emoji: "🚴",
      tag: "Bike Tour",
      title: "Spreewald Loop",
      prompt:
        "Create a 2-day bike tour through the Spreewald starting in Lübbenau. Max 45 km per day, flat route, nice restaurants.",
      badgeClass: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300",
    },
    {
      emoji: "🚗",
      tag: "Roadtrip",
      title: "Black Forest Highway",
      prompt:
        "Plan a 3-day roadtrip along the Black Forest High Road from Baden-Baden to Freudenstadt with scenic viewpoints.",
      badgeClass: "bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300",
    },
    {
      emoji: "🏰",
      tag: "Culture",
      title: "Potsdam Palaces Tour",
      prompt:
        "One-day bike tour connecting Potsdam's finest palaces and parks including Sanssouci and Cecilienhof.",
      badgeClass: "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300",
    },
  ];
}
