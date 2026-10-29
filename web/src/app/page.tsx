import { Hero } from "@/sections/home/Hero";
import { Categories } from "@/sections/home/Categories";
import { Paths } from "@/sections/home/Paths";
import { Facts } from "@/sections/home/Facts";
import { Services } from "@/sections/home/Services";
import { Brands } from "@/sections/home/Brands";
import { Quiz } from "@/sections/home/Quiz";
import { Projects } from "@/sections/home/Projects";
import { Showroom } from "@/sections/home/Showroom";
import { Reviews } from "@/sections/home/Reviews";
import { FaqSection } from "@/sections/home/FaqSection";
import { Blog } from "@/sections/home/Blog";
import { LeadSection } from "@/sections/home/LeadSection";

// Главная: 12 блоков из brief.md. Ритм тонов: тёмный → крем → белый → тёмный → крем → белый → тёмный → …
export default function HomePage() {
  return (
    <>
      <Hero />
      <Categories />
      <Paths />
      <Facts />
      <Services />
      <Brands />
      <Quiz />
      <Projects />
      <Showroom />
      <Reviews />
      <FaqSection />
      <Blog />
      <LeadSection />
    </>
  );
}
