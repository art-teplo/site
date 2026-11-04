"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { Site } from "@/data/types";

const SiteContext = createContext<Site | null>(null);

// Контакты из админки для клиентских компонентов (шапка, форма заявки); серверные берут getSite()
export function SiteProvider({ site, children }: { site: Site; children: ReactNode }) {
  return <SiteContext value={site}>{children}</SiteContext>;
}

export function useSite(): Site {
  const site = useContext(SiteContext);
  if (!site) throw new Error("useSite вне SiteProvider");
  return site;
}
