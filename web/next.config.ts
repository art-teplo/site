import type { NextConfig } from "next";
import { IMAGES_VERSION } from "./src/lib/asset";

const nextConfig: NextConfig = {
  // Для Docker-образа (web/Dockerfile); Vercel эту настройку не мешает
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  images: {
    formats: ["image/avif", "image/webp"],
    qualities: [70, 75],
    // Оптимизируем только свои картинки и только с текущей версией (см. lib/asset.ts)
    localPatterns: [{ pathname: "/images/**", search: `?v=${IMAGES_VERSION}` }],
  },
};

export default nextConfig;
