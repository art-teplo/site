import { cacheLife, cacheTag } from "next/cache";
import { faq, posts, projects, showroomHall } from "./content";
import { demoSite } from "./site";
import type { Faq, ImageAsset, Post, PostCard, Project, Site } from "./types";

// Контент из админки (бэк: apps/content). Без NEXT_PUBLIC_API_URL — демо-данные из src/data,
// как на Vercel. Ответы кэшируются по тегам; после правки бэк зовёт /api/revalidate с тегом раздела.
const API_URL = process.env.NEXT_PUBLIC_API_URL;

// Теги — те же, что models.Tag на бэке
type Tag = "site" | "faq" | "projects" | "posts" | "showroom";

async function load<T>(path: string, tag: Tag): Promise<T | null> {
  "use cache";
  cacheTag(tag);
  cacheLife("hours"); // страховка, если бэк не достучался до /api/revalidate
  const response = await fetch(`${API_URL}/api/${path}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`API ${path}: ${response.status}`);
  return response.json();
}

type ApiSite = {
  city: string;
  address: string;
  map_url: string;
  phone: string;
  phone_href: string;
  email: string;
  hours: { days: string; time: string }[];
  viber_url: string;
  telegram_url: string;
  instagram_url: string;
  instagram_handle: string;
  reply_promise: string;
  legal_name: string;
  unp: string;
};
type ApiFaq = { question: string; answer: string; on_home: boolean };
type ApiProject = Omit<Project, "products"> & { product_slugs: string[] };
type ApiPostCard = Omit<PostCard, "date" | "readMinutes"> & { published_at: string; read_minutes: number };
type ApiPost = ApiPostCard & { body: string };

export async function getSite(): Promise<Site> {
  const data = API_URL ? await load<ApiSite>("site/", "site") : null;
  if (!data) return demoSite;
  return {
    city: data.city,
    address: data.address,
    mapUrl: data.map_url,
    phone: data.phone,
    phoneHref: data.phone_href,
    email: data.email,
    hours: data.hours,
    viber: data.viber_url,
    telegram: data.telegram_url,
    instagram: data.instagram_url,
    instagramHandle: data.instagram_handle,
    replyPromise: data.reply_promise,
    // Пока заказчик не прислал реквизиты — видимая заглушка, как в демо
    legalName: data.legal_name || "[Уточнить у заказчика: юрлицо]",
    unp: data.unp || "[УНП]",
  };
}

export async function getFaq(): Promise<Faq[]> {
  const data = API_URL ? await load<ApiFaq[]>("faq/", "faq") : null;
  if (!data) return faq;
  return data.map((item) => ({ q: item.question, a: item.answer, onHome: item.on_home }));
}

export async function getProjects(): Promise<Project[]> {
  const data = API_URL ? await load<ApiProject[]>("projects/", "projects") : null;
  if (!data) return projects;
  return data.map(({ product_slugs, ...project }) => ({ ...project, products: product_slugs }));
}

const toCard = ({ published_at, read_minutes, ...post }: ApiPostCard): PostCard => ({
  ...post,
  date: published_at,
  readMinutes: read_minutes,
});

export async function getPosts(): Promise<PostCard[]> {
  const data = API_URL ? await load<ApiPostCard[]>("posts/", "posts") : null;
  if (!data) return posts;
  return data.map(toCard);
}

export async function getPost(slug: string): Promise<Post | null> {
  if (!API_URL) return posts.find((p) => p.slug === slug) ?? null;
  const data = await load<ApiPost>(`posts/${encodeURIComponent(slug)}/`, "posts");
  return data && { ...toCard(data), body: data.body };
}

export async function getShowroom(): Promise<ImageAsset[]> {
  const data = API_URL ? await load<{ image: ImageAsset }[]>("showroom/", "showroom") : null;
  if (!data) return showroomHall;
  return data.map((photo) => photo.image);
}
