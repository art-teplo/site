import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Breadcrumbs } from "@/components/Breadcrumbs/Breadcrumbs";
import { Frame } from "@/components/Frame/Frame";
import { Picture } from "@/components/Picture/Picture";
import { ProductCard } from "@/components/ProductCard/ProductCard";
import { Reveal } from "@/components/Reveal/Reveal";
import { getProduct, priceFrom, products } from "@/data/catalog";
import { getBrands, getCategories, getProjects } from "@/data/api";
import { formatPrice } from "@/lib/format";
import { LeadSection } from "@/sections/home/LeadSection";
import { ProductHero } from "@/sections/product/ProductHero";
import { ProductSpecs } from "@/sections/product/ProductSpecs";
import styles from "./page.module.css";

export function generateStaticParams() {
  return products.map((p) => ({ category: p.category, product: p.slug }));
}

export async function generateMetadata({ params }: PageProps<"/catalog/[category]/[product]">): Promise<Metadata> {
  const { product: slug } = await params;
  const p = getProduct(slug);
  return p ? { title: p.name, description: `${p.name} — ${p.summary} От ${formatPrice(priceFrom(p))}.` } : {};
}

export default async function ProductPage({ params }: PageProps<"/catalog/[category]/[product]">) {
  const { category: categorySlug, product: slug } = await params;
  const product = getProduct(slug);
  const [categories, brands] = await Promise.all([getCategories(), getBrands()]);
  const category = categories.find((c) => c.slug === categorySlug);
  if (!product || !category || product.category !== category.slug) notFound();

  const brand = brands.find((b) => b.slug === product.brand);
  const inProjects = (await getProjects()).filter((p) => p.products.includes(product.slug));
  const related = products.filter((p) => p.category === product.category && p.slug !== product.slug).slice(0, 3);

  return (
    <>
      <Section className={styles.top}>
        <Container>
          <Breadcrumbs
            items={[
              { href: "/", label: "Главная" },
              { href: "/catalog", label: "Каталог" },
              { href: `/catalog/${category.slug}`, label: category.name },
              { label: product.name },
            ]}
          />
          <div className={styles.hero}>
            <ProductHero product={product} brand={brand} />
          </div>
        </Container>
      </Section>

      <ProductSpecs product={product} brand={brand} />

      {inProjects.length > 0 && (
        <Section tone="dark" labelledBy="in-projects-title">
          <Container>
            <SectionHead titleId="in-projects-title" title="Этот радиатор в интерьерах" />
            <ul className={styles.projects}>
              {inProjects.map((p, i) => (
                <Reveal as="li" key={p.slug} index={i}>
                  <Link href="/#projects" className={styles.project}>
                    <Frame ratio="4 / 3">
                      <Picture image={p.image} sizes="(max-width: 767px) 100vw, 50vw" />
                    </Frame>
                    <span className={styles.projectTitle}>
                      {p.title}, {p.place}
                    </span>
                  </Link>
                </Reveal>
              ))}
            </ul>
          </Container>
        </Section>
      )}

      {related.length > 0 && (
        <Section labelledBy="related-title">
          <Container>
            <SectionHead titleId="related-title" title="Посмотрите также" />
            <ul className={styles.related}>
              {related.map((p, i) => (
                <Reveal as="li" key={p.slug} index={i}>
                  <ProductCard product={p} brand={brands.find((b) => b.slug === p.brand)?.name} sizes="(max-width: 767px) 50vw, 33vw" />
                </Reveal>
              ))}
            </ul>
          </Container>
        </Section>
      )}

      <LeadSection source={`product/${product.slug}`} />
    </>
  );
}
