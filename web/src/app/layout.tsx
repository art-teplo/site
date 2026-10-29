import type { Metadata, Viewport } from "next";
import { Onest } from "next/font/google";
import { Header } from "@/components/Header/Header";
import { Footer } from "@/components/Footer/Footer";
import { SmoothScroll } from "@/components/SmoothScroll/SmoothScroll";
import "@/styles/tokens.css";
import "@/styles/base.css";

const onest = Onest({ subsets: ["cyrillic", "latin"], variable: "--font-onest", display: "swap" });

export const metadata: Metadata = {
  title: {
    default: "АртТепло — дизайн-радиаторы и отопление в Минске",
    template: "%s — АртТепло",
  },
  description:
    "Шоурум радиаторов на Леонида Беды, 39. Подбор, расчёт, замена с согласованием и монтаж. Официальный представитель КЗТО в Беларуси.",
  // ВРЕМЕННО: демо для заказчика с чужими фото — не индексируем. Убрать вместе с app/robots.ts при запуске.
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  themeColor: "#0e0c0b",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ru" className={onest.variable} suppressHydrationWarning>
      <head>
        {/* Reveal прячет элементы только при работающем JS */}
        <script dangerouslySetInnerHTML={{ __html: "document.documentElement.classList.add('js')" }} />
      </head>
      <body>
        <a href="#main" className="skip-link">
          К содержанию
        </a>
        <SmoothScroll />
        <Header />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
