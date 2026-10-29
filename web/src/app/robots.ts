import type { MetadataRoute } from "next";

// ВРЕМЕННО: демо-версия закрыта от поисковиков (фото взяты из открытых источников, docs/demo-photos.md)
export default function robots(): MetadataRoute.Robots {
  return { rules: { userAgent: "*", disallow: "/" } };
}
