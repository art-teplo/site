import type { NextConfig } from "next";
import { IMAGES_VERSION } from "./src/lib/asset";

// Адрес бэка для сервера Next (src/data/api.ts): в Docker http://backend:8000, локально
// http://localhost:8000. Не задан — демо без бэка, как на Vercel
const API_URL = process.env.API_URL;

const nextConfig: NextConfig = {
  // Для Docker-образа (web/Dockerfile); Vercel эту настройку не мешает
  output: "standalone",
  cacheComponents: true,
  // npm run dev: открыть сайт с телефона в той же Wi-Fi по адресу компьютера (http://192.168.x.x:3000).
  // Только частные адреса локальных сетей (172.* — офисные сети и раздача с iPhone); на сборку и прод не влияет
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*", "172.*.*.*"],
  partialPrefetching: true,
  // Вшивается в клиентский код при сборке: форма заявки без бэка только имитирует отправку
  env: { NEXT_PUBLIC_DEMO: API_URL ? "" : "1" },
  // Браузер ходит в /api/ и /media/ на том же домене. На сервере их перехватывает nginx, а сюда
  // попадают оптимизатор картинок (фото из админки) и разработка без nginx (npm run dev).
  // afterFiles: свои роуты Next (/api/revalidate) важнее. Адрес вшивается при сборке.
  // Next сначала срезает слеш в конце (/api/leads/ → /api/leads), а DRF ждёт его — возвращаем
  async rewrites() {
    if (!API_URL) return [];
    return {
      beforeFiles: [],
      afterFiles: [
        { source: "/api/:path*", destination: `${API_URL}/api/:path*/` },
        { source: "/media/:path*", destination: `${API_URL}/media/:path*` },
      ],
      fallback: [],
    };
  },
  images: {
    formats: ["image/avif", "image/webp"],
    qualities: [70, 75],
    // Свои картинки — только с текущей версией (см. lib/asset.ts); фото из админки отдаёт бэк
    localPatterns: [{ pathname: "/images/**", search: `?v=${IMAGES_VERSION}` }, { pathname: "/media/**" }],
    // С S3 (BACKEND__S3__ENABLED=1) бэк отдаёт полные адреса публичного бакета ActiveStorage
    remotePatterns: [{ protocol: "https", hostname: "io.activecloud.com", pathname: "/art-teplo-media/**" }],
  },
};

export default nextConfig;
