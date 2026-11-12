import type { Metadata } from "next";
import { CatalogPage } from "@/sections/catalog/CatalogPage";

export const metadata: Metadata = {
  title: "Каталог радиаторов, конвекторов и полотенцесушителей",
  description: "Радиаторы КЗТО, Guardo, Радимакс, Royal Thermo и других брендов. Фильтры по размерам, мощности, подключению и цвету.",
};

export default function CatalogIndexPage() {
  return <CatalogPage />;
}
