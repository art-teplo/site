import type { NextConfig } from "next";
import { IMAGES_VERSION } from "./src/lib/asset";

// Фото из админки отдаёт бэк (/media/, позже — S3): оптимизатору Next нужен его адрес
const API_URL = process.env.NEXT_PUBLIC_API_URL;
const mediaPatterns = API_URL ? [new URL("/media/**", API_URL)] : [];
// Бэк на этой машине или в локальной сети (разработка, показ с телефона): оптимизатору
// нужно разрешить локальные адреса. Ходит он только по mediaPatterns, на прод не влияет
const localApi = /^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(
  API_URL ? new URL(API_URL).hostname : "",
);

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
    remotePatterns: mediaPatterns,
    dangerouslyAllowLocalIP: localApi,
  },
};

export default nextConfig;
