// Контакты и реквизиты — в одном месте (принцип из brief.md).
// ВРЕМЕННО: основные контакты не подтверждены заказчиком (вопрос 9), юрлицо и УНП неизвестны.

export const FOUNDED_YEAR = 2000;

export const site = {
  name: "АртТепло",
  tagline: "Студия тепла",
  city: "Минск",
  address: "ул. Леонида Беды, 39",
  phone: "+375 29 319-02-86",
  phoneHref: "tel:+375293190286",
  email: "plagcity@gmail.com",
  hours: [
    { days: "Пн–Пт", time: "9:00–18:00" },
    { days: "Сб", time: "10:00–17:00" },
    { days: "Вс", time: "выходной" },
  ],
  viber: "viber://chat?number=%2B375293190286",
  telegram: "https://t.me/+375293190286",
  instagram: "https://www.instagram.com/artteplo_minsk/",
  instagramHandle: "@artteplo_minsk",
  legalName: "[юрлицо]",
  unp: "[УНП]",
  replyPromise: "Перезвоним в течение 30 минут в рабочее время",
  mapUrl: "https://yandex.by/maps/?text=%D0%9C%D0%B8%D0%BD%D1%81%D0%BA%2C%20%D1%83%D0%BB.%20%D0%9B%D0%B5%D0%BE%D0%BD%D0%B8%D0%B4%D0%B0%20%D0%91%D0%B5%D0%B4%D1%8B%2C%2039",
} as const;

// Короткий ряд в шапке — то, за чем приходят чаще всего (как у radiator.center)
export const nav = [
  { href: "/catalog", label: "Каталог" },
  { href: "/podbor", label: "Подбор" },
  { href: "/proekty", label: "Проекты" },
  { href: "/shourum", label: "Шоурум" },
  { href: "/klientam", label: "Доставка и оплата" },
  { href: "/kontakty", label: "Контакты" },
] as const;

// Полное меню по кнопке «Меню»: все разделы из docs/brief.md
export const menu = [
  {
    title: "Каталог",
    href: "/catalog",
    links: [
      { href: "/catalog/radiatory", label: "Радиаторы" },
      { href: "/catalog/konvektory", label: "Конвекторы" },
      { href: "/catalog/polotentsesushiteli", label: "Полотенцесушители" },
      { href: "/catalog/armatura", label: "Арматура" },
      { href: "/brendy", label: "Бренды" },
    ],
  },
  {
    title: "Подбор и услуги",
    href: "/podbor",
    links: [
      { href: "/podbor", label: "Подобрать радиатор" },
      { href: "/podbor#lead", label: "Цена по спецификации" },
      { href: "/uslugi#raschet", label: "Тепловой расчёт" },
      { href: "/uslugi#zamena", label: "Замена с согласованием" },
      { href: "/uslugi#montazh", label: "Монтаж" },
      { href: "/uslugi#pokraska", label: "Покраска в RAL" },
    ],
  },
  {
    title: "Клиентам",
    href: "/klientam",
    links: [
      { href: "/klientam#dostavka", label: "Доставка и оплата" },
      { href: "/klientam#sroki", label: "Сроки изготовления" },
      { href: "/klientam#garantiya", label: "Гарантия" },
      { href: "/klientam#faq", label: "Вопрос-ответ" },
    ],
  },
  {
    title: "Партнёрам",
    href: "/partneram",
    links: [
      { href: "/partneram#dizajneram", label: "Дизайнерам и архитекторам" },
      { href: "/partneram#stroitelyam", label: "Строительным компаниям" },
      { href: "/partneram#anketa", label: "Стать партнёром" },
    ],
  },
  {
    title: "О нас",
    href: "/shourum",
    links: [
      { href: "/shourum", label: "Шоурум и команда" },
      { href: "/proekty", label: "Проекты" },
      { href: "/blog", label: "Блог и акции" },
      { href: "/kontakty", label: "Контакты" },
    ],
  },
] as const;
