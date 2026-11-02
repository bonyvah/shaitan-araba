#!/usr/bin/env python3
"""Render the Shaitan Araba shop into static HTML.

    python3 build.py            # writes ./public
    python3 build.py --out dist

Input lives in src/data/*.json and src/assets/. Every page is plain HTML
with all products and prices in the markup, so the site can be read
without running JavaScript. JavaScript only adds the cart, catalog
filters and the order form.
"""

import argparse
import json
import shutil
from datetime import date
from html import escape
from pathlib import Path

import art

ROOT = Path(__file__).parent
SRC = ROOT / "src"

STATUS = {
    "in_stock": ("В наличии", "ok"),
    "preorder": ("Под заказ", "wait"),
    "sold_out": ("Нет в наличии", "out"),
}
# Some accessories get their own drawing instead of the category's.
ART_OVERRIDES = {
    "bottle-cage-set": "bottle",
    "tube-29": "tire",
    "schwalbe-smart-sam-29": "tire",
    "sport-glasses": "glasses",
}
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]

e = escape
CURRENT = ' aria-current="page"'


def price(value: int) -> str:
    # 49 900 сом, with a narrow no-break space between thousands
    return f"{value:,}".replace(",", " ") + " сом"


def human_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


class Site:
    def __init__(self, out: Path):
        self.out = out
        catalog = json.loads((SRC / "data/catalog.json").read_text(encoding="utf-8"))
        data = json.loads((SRC / "data/site.json").read_text(encoding="utf-8"))
        self.categories = catalog["categories"]
        self.cat_by_slug = {c["slug"]: c for c in self.categories}
        self.products = catalog["products"]
        for p in self.products:
            cat = self.cat_by_slug[p["category"]]
            p["group"] = cat["group"]
            p["art"] = ART_OVERRIDES.get(p["slug"], cat["art"])
        self.shop = data["shop"]
        self.delivery = data["delivery"]
        self.posts = sorted(data["posts"], key=lambda p: p["date"], reverse=True)
        self.news = sorted(data["news"], key=lambda n: n["date"], reverse=True)
        self.pages: list[str] = []

    # ── output ────────────────────────────────────────────────────────────
    def write(self, path: str, html: str) -> None:
        target = self.out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        if path.endswith(".html") and path != "404.html":
            self.pages.append(path)

    def build(self) -> None:
        # Empty the folder rather than replacing it, so a server that has
        # it mounted (docker-compose.yml) keeps serving the new files.
        self.out.mkdir(parents=True, exist_ok=True)
        for child in self.out.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
        shutil.copytree(SRC / "assets", self.out / "assets")
        self.write_art()
        self.write_data_js()

        self.write("index.html", self.home())
        self.write("catalog/index.html", self.catalog_page(None))
        for group in ("bikes", "accessories"):
            self.write(f"catalog/{group}.html", self.catalog_page(group))
        for cat in self.categories:
            self.write(f"catalog/{cat['slug']}.html", self.catalog_page(cat["group"], cat))
        for p in self.products:
            self.write(f"product/{p['slug']}.html", self.product_page(p))
        self.write("delivery.html", self.delivery_page())
        self.write("order.html", self.order_page())
        self.write("guide.html", self.guide_page())
        self.write("blog/index.html", self.blog_index())
        for post in self.posts:
            self.write(f"blog/{post['slug']}.html", self.post_page(post))
        self.write("news.html", self.news_page())
        self.write("contacts.html", self.contacts_page())
        self.write("404.html", self.not_found())
        self.write("robots.txt", "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")
        self.write("sitemap.xml", self.sitemap())

    def write_art(self) -> None:
        for p in self.products:
            self.write(f"assets/img/products/{p['slug']}.svg", art.render(p["art"], p["color"], p["name"]))
        for c in self.categories:
            color = "#d7263d" if c["group"] == "bikes" else "#1d232a"
            self.write(f"assets/img/categories/{c['slug']}.svg", art.render(c["art"], color, c["name"]))

    def write_data_js(self) -> None:
        """What the cart and order form need, so they work on any page."""
        data = {
            "products": {
                p["slug"]: {
                    "name": p["name"], "price": p["price"], "status": p["status"],
                    "group": p["group"], "sizes": p.get("sizes", []), "sku": p["sku"],
                }
                for p in self.products
            },
            "regions": self.delivery["regions"],
            "hours": [{"days": h["schema"], "open": h["open"], "close": h["close"]} for h in self.shop["hours"]],
        }
        js = "// Generated by build.py from src/data. Do not edit.\nwindow.SA_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n"
        self.write("assets/js/data.js", js)

    # ── layout ────────────────────────────────────────────────────────────
    def layout(self, path: str, title: str, description: str, body: str, active: str = "", extra_head: str = "",
               scripts: tuple[str, ...] = (), root: str | None = None) -> str:
        if root is None:
            root = "../" * path.count("/")
        full_title = f"{title} — {self.shop['name']}" if title else f"{self.shop['name']} — {self.shop['tagline']}"
        nav_items = [
            ("bikes", "catalog/bikes.html", "Велосипеды"),
            ("accessories", "catalog/accessories.html", "Аксессуары"),
            ("delivery", "delivery.html", "Доставка и оплата"),
            ("guide", "guide.html", "Как выбрать"),
            ("blog", "blog/index.html", "Блог"),
            ("news", "news.html", "Новости"),
            ("contacts", "contacts.html", "Контакты"),
        ]
        nav = "".join(
            f'<li><a href="{root}{href}"{CURRENT if key == active else ""}>{label}</a></li>'
            for key, href, label in nav_items
        )
        hours = " · ".join(f"{h['days']} {h['time']}" for h in self.shop["hours"])
        script_tags = "".join(f'<script src="{root}assets/js/{s}" defer></script>' for s in ("data.js", "main.js", *scripts))
        return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
<link rel="icon" href="{root}assets/img/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/css/style.css">
{extra_head}{script_tags}
</head>
<body data-root="{root}">
<a class="skip" href="#main">Перейти к содержимому</a>
<div class="topbar">
  <div class="wrap topbar__inner">
    <span class="topbar__item"><svg class="i" aria-hidden="true"><use href="{root}assets/img/icons.svg#pin"/></svg>{e(self.shop['city'])}, {e(self.shop['address'])}</span>
    <span class="topbar__item" data-open-status><svg class="i" aria-hidden="true"><use href="{root}assets/img/icons.svg#clock"/></svg><span class="topbar__hours">{e(hours)}</span></span>
    <span class="topbar__item topbar__promo">Бесплатная доставка по Бишкеку</span>
  </div>
</div>
<header class="header">
  <div class="wrap header__inner">
    <a class="logo" href="{root}index.html" aria-label="{e(self.shop['name'])} — на главную">
      <svg class="logo__mark" viewBox="0 0 40 40" aria-hidden="true"><use href="{root}assets/img/icons.svg#logo"/></svg>
      <span class="logo__text">Shaitan<b>Araba</b></span>
    </a>
    <nav class="nav" aria-label="Основное меню">
      <ul class="nav__list" id="nav-list">{nav}</ul>
    </nav>
    <div class="header__actions">
      <a class="header__phone" href="tel:{e(self.shop['phone'])}"><svg class="i" aria-hidden="true"><use href="{root}assets/img/icons.svg#phone"/></svg><span>{e(self.shop['phone_display'])}</span></a>
      <a class="cart-link" href="{root}order.html" aria-label="Корзина">
        <svg class="i i--lg" aria-hidden="true"><use href="{root}assets/img/icons.svg#cart"/></svg>
        <span class="cart-link__count" data-cart-count hidden>0</span>
      </a>
      <button class="burger" type="button" aria-label="Меню" aria-expanded="false" aria-controls="nav-list"><span></span></button>
    </div>
  </div>
</header>
<main id="main">
{body}
</main>
{self.footer(root)}
<div class="toast" role="status" aria-live="polite" hidden></div>
</body>
</html>
"""

    def footer(self, root: str) -> str:
        cats = lambda group: "".join(
            f'<li><a href="{root}catalog/{c["slug"]}.html">{e(c["name"])}</a></li>'
            for c in self.categories if c["group"] == group
        )
        hours = "".join(f"<li><span>{e(h['days'])}</span> {e(h['time'])}</li>" for h in self.shop["hours"])
        return f"""<footer class="footer">
  <div class="wrap footer__grid">
    <div class="footer__brand">
      <a class="logo logo--light" href="{root}index.html">
        <svg class="logo__mark" viewBox="0 0 40 40" aria-hidden="true"><use href="{root}assets/img/icons.svg#logo"/></svg>
        <span class="logo__text">Shaitan<b>Araba</b></span>
      </a>
      <p>Магазин и мастерская велосипедов в Бишкеке. Собираем, настраиваем и доставляем по всему Кыргызстану.</p>
    </div>
    <div><h2 class="footer__title">Велосипеды</h2><ul>{cats("bikes")}</ul></div>
    <div><h2 class="footer__title">Аксессуары</h2><ul>{cats("accessories")}</ul></div>
    <div>
      <h2 class="footer__title">Покупателям</h2>
      <ul>
        <li><a href="{root}delivery.html">Доставка и оплата</a></li>
        <li><a href="{root}guide.html">Как выбрать велосипед</a></li>
        <li><a href="{root}order.html">Корзина и заказ</a></li>
        <li><a href="{root}news.html">Новости магазина</a></li>
      </ul>
    </div>
    <div>
      <h2 class="footer__title">Контакты</h2>
      <address>
        <a class="footer__phone" href="tel:{e(self.shop['phone'])}">{e(self.shop['phone_display'])}</a>
        {e(self.shop['city'])}, {e(self.shop['address'])}
      </address>
      <ul class="footer__hours">{hours}</ul>
    </div>
  </div>
  <div class="wrap footer__bottom">
    <span>© {date.today().year} {e(self.shop['name'])}. Цены указаны в сомах.</span>
    <span>Учебный сайт: заказы не обрабатываются.</span>
  </div>
</footer>"""

    def crumbs(self, root: str, items: list[tuple[str, str | None]]) -> str:
        parts = [f'<li><a href="{root}index.html">Главная</a></li>']
        for label, href in items:
            parts.append(f'<li><a href="{root}{href}">{e(label)}</a></li>' if href else f'<li aria-current="page">{e(label)}</li>')
        return f'<nav class="crumbs" aria-label="Навигация"><ol>{"".join(parts)}</ol></nav>'

    # ── pieces ────────────────────────────────────────────────────────────
    def card(self, p: dict, root: str) -> str:
        label, tone = STATUS[p["status"]]
        old = f'<s class="price__old">{price(p["old_price"])}</s>' if p.get("old_price") else ""
        badges = ""
        if p.get("old_price"):
            pct = round(100 - p["price"] * 100 / p["old_price"])
            badges += f'<span class="badge badge--sale">−{pct}%</span>'
        if p.get("new"):
            badges += '<span class="badge badge--new">Новинка</span>'
        button = (
            f'<button class="btn btn--sm" type="button" data-add="{e(p["slug"])}">В корзину</button>'
            if p["status"] != "sold_out"
            else f'<a class="btn btn--sm btn--ghost" href="tel:{e(self.shop["phone"])}">Позвонить</a>'
        )
        return f"""<article class="card" data-product data-category="{e(p['category'])}" data-group="{p['group']}" data-brand="{e(p['brand'])}" data-price="{p['price']}" data-status="{p['status']}">
  <a class="card__media" href="{root}product/{e(p['slug'])}.html" tabindex="-1" aria-hidden="true">
    <img src="{root}assets/img/products/{e(p['slug'])}.svg" alt="" width="480" height="320" loading="lazy">
    <span class="card__badges">{badges}</span>
  </a>
  <div class="card__body">
    <span class="card__brand">{e(p['brand'])} · <span class="stock stock--{tone}">{label}</span></span>
    <h3 class="card__title"><a href="{root}product/{e(p['slug'])}.html">{e(p['name'])}</a></h3>
    <p class="card__summary">{e(p['summary'])}</p>
    <div class="card__foot">
      <span class="price"><span class="price__now">{price(p['price'])}</span> {old}</span>
      {button}
    </div>
  </div>
</article>"""

    def grid(self, products: list[dict], root: str) -> str:
        return '<div class="grid">' + "".join(self.card(p, root) for p in products) + "</div>"

    def delivery_strip(self, root: str) -> str:
        return f"""<section class="perks" aria-label="Почему мы">
  <div class="wrap perks__grid">
    <div class="perk"><svg class="i i--xl" aria-hidden="true"><use href="{root}assets/img/icons.svg#truck"/></svg><div><b>Бесплатно по Бишкеку</b><span>Привезём в день заказа или на следующий день</span></div></div>
    <div class="perk"><svg class="i i--xl" aria-hidden="true"><use href="{root}assets/img/icons.svg#map"/></svg><div><b>Доставка по Кыргызстану</b><span>По тарифу курьерской службы, без наценки</span></div></div>
    <div class="perk"><svg class="i i--xl" aria-hidden="true"><use href="{root}assets/img/icons.svg#wrench"/></svg><div><b>Сборка и настройка</b><span>Каждый велосипед проверяет механик</span></div></div>
    <div class="perk"><svg class="i i--xl" aria-hidden="true"><use href="{root}assets/img/icons.svg#shield"/></svg><div><b>Гарантия до 3 лет</b><span>И бесплатное ТО через месяц после покупки</span></div></div>
  </div>
</section>"""

    # ── pages ─────────────────────────────────────────────────────────────
    def home(self) -> str:
        root = ""
        featured = [p for p in self.products if p.get("featured")]
        fresh = [p for p in self.products if p.get("new")][:4]
        cat_tiles = "".join(
            f"""<a class="tile" href="catalog/{c['slug']}.html">
  <img src="assets/img/categories/{c['slug']}.svg" alt="" width="480" height="320" loading="lazy">
  <span class="tile__name">{e(c['short'])}</span>
  <span class="tile__count">{sum(1 for p in self.products if p['category'] == c['slug'])} товаров</span>
</a>"""
            for c in self.categories
        )
        posts = "".join(
            f"""<article class="post-card"><time datetime="{p['date']}">{human_date(p['date'])}</time>
<h3><a href="blog/{p['slug']}.html">{e(p['title'])}</a></h3><p>{e(p['excerpt'])}</p></article>"""
            for p in self.posts[:3]
        )
        hero_bike = next(p for p in self.products if p["slug"] == "merida-big-nine-20")
        body = f"""<section class="hero">
  <div class="wrap hero__grid">
    <div class="hero__copy">
      <p class="eyebrow">Сезон 2026 · новая поставка</p>
      <h1>Велосипеды для города, гор и&nbsp;всей семьи</h1>
      <p class="hero__lead">Горные, шоссейные, городские и детские велосипеды, электровелосипеды и всё для поездок. Соберём, настроим и бесплатно привезём по Бишкеку.</p>
      <div class="hero__cta">
        <a class="btn btn--lg" href="catalog/bikes.html">Выбрать велосипед</a>
        <a class="btn btn--lg btn--ghost" href="catalog/accessories.html">Аксессуары</a>
      </div>
      <dl class="hero__facts">
        <div><dt>{len([p for p in self.products if p['group'] == 'bikes'])}</dt><dd>моделей в каталоге</dd></div>
        <div><dt>0&nbsp;сом</dt><dd>доставка по Бишкеку</dd></div>
        <div><dt>7</dt><dd>областей с доставкой</dd></div>
      </dl>
    </div>
    <a class="hero__visual" href="product/{hero_bike['slug']}.html">
      <img src="assets/img/products/{hero_bike['slug']}.svg" alt="{e(hero_bike['name'])}" width="480" height="320">
      <span class="hero__tag"><b>{e(hero_bike['name'])}</b><span><span class="price__now">{price(hero_bike['price'])}</span> <s>{price(hero_bike['old_price'])}</s></span></span>
    </a>
  </div>
</section>
{self.delivery_strip(root)}
<section class="section">
  <div class="wrap">
    <div class="section__head"><h2>Каталог</h2><a class="link-arrow" href="catalog/index.html">Все товары</a></div>
    <div class="tiles">{cat_tiles}</div>
  </div>
</section>
<section class="section section--alt">
  <div class="wrap">
    <div class="section__head"><h2>Хиты продаж</h2><a class="link-arrow" href="catalog/index.html">Смотреть все</a></div>
    {self.grid(featured, root)}
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="section__head"><h2>Новинки</h2><a class="link-arrow" href="news.html">Новости магазина</a></div>
    {self.grid(fresh, root)}
  </div>
</section>
<section class="section section--dark">
  <div class="wrap split">
    <div>
      <p class="eyebrow">Доставка</p>
      <h2>По Бишкеку — бесплатно. По Кыргызстану — по тарифу перевозчика.</h2>
      <p>Отправляем велосипеды в заводской коробке через партнёрскую курьерскую службу во все области. Вы платите ровно её тариф — от {price(min(r['bike'] for r in self.delivery['regions'] if r['bike']))} за велосипед.</p>
      <a class="btn btn--lg btn--light" href="delivery.html">Тарифы по областям</a>
    </div>
    <ul class="checklist">
      <li>Сборка и настройка перед отправкой</li>
      <li>Оплата при получении для Бишкека</li>
      <li>Предоплата 30% для регионов</li>
      <li>Самовывоз с Паланчиева, 6/7</li>
    </ul>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="section__head"><h2>Блог</h2><a class="link-arrow" href="blog/index.html">Все статьи</a></div>
    <div class="posts">{posts}</div>
  </div>
</section>
{self.visit_block(root)}"""
        ld = {
            "@context": "https://schema.org", "@type": "BicycleStore", "name": self.shop["name"],
            "telephone": self.shop["phone"],
            "address": {"@type": "PostalAddress", "streetAddress": self.shop["address"], "addressLocality": self.shop["city"], "addressCountry": "KG"},
            "openingHoursSpecification": [
                {"@type": "OpeningHoursSpecification", "dayOfWeek": h["schema"], "opens": h["open"], "closes": h["close"]}
                for h in self.shop["hours"]
            ],
        }
        return self.layout("index.html", "", "Велосипеды и аксессуары в Бишкеке. Бесплатная доставка по городу, доставка по всему Кыргызстану.", body,
                           extra_head=f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n')

    def visit_block(self, root: str) -> str:
        hours = "".join(f"<li><span>{e(h['days'])}</span><b>{e(h['time'])}</b></li>" for h in self.shop["hours"])
        return f"""<section class="section section--alt">
  <div class="wrap visit">
    <div>
      <h2>Приходите в магазин</h2>
      <p>Можно примерить велосипед, прокатиться у входа и сразу забрать покупку. Механик подгонит седло и руль под ваш рост.</p>
      <ul class="hours">{hours}</ul>
    </div>
    <div class="visit__card">
      <p class="visit__addr"><svg class="i i--lg" aria-hidden="true"><use href="{root}assets/img/icons.svg#pin"/></svg>{e(self.shop['city'])}, {e(self.shop['address'])}</p>
      <a class="visit__phone" href="tel:{e(self.shop['phone'])}">{e(self.shop['phone_display'])}</a>
      <div class="visit__actions">
        <a class="btn" href="tel:{e(self.shop['phone'])}">Позвонить</a>
        <a class="btn btn--ghost" href="{e(self.shop['map_url'])}" target="_blank" rel="noopener">Открыть на карте</a>
      </div>
    </div>
  </div>
</section>"""

    def catalog_page(self, group: str | None, category: dict | None = None) -> str:
        if category:
            path, title, intro = f"catalog/{category['slug']}.html", category["name"], category["blurb"]
            items = [p for p in self.products if p["category"] == category["slug"]]
        elif group:
            path = f"catalog/{group}.html"
            title = "Велосипеды" if group == "bikes" else "Аксессуары"
            intro = ("Горные, шоссейные, городские, детские, складные и электровелосипеды." if group == "bikes"
                     else "Шлемы, замки, фонари, насосы, сумки, запчасти и экипировка.")
            items = [p for p in self.products if p["group"] == group]
        else:
            path, title, intro = "catalog/index.html", "Каталог", "Все велосипеды и аксессуары в наличии и под заказ."
            items = self.products
        root = "../"
        groups = [("bikes", "Велосипеды"), ("accessories", "Аксессуары")]
        side = ""
        for g, gname in groups:
            links = "".join(
                f'<li><a href="{c["slug"]}.html"{CURRENT if category and c["slug"] == category["slug"] else ""}>{e(c["short"])}'
                f'<span>{sum(1 for p in self.products if p["category"] == c["slug"])}</span></a></li>'
                for c in self.categories if c["group"] == g
            )
            current = CURRENT if group == g and not category else ""
            side += f'<div class="side__group"><a class="side__title" href="{g}.html"{current}>{gname}</a><ul>{links}</ul></div>'
        brands = sorted({p["brand"] for p in items})
        brand_boxes = "".join(
            f'<label class="check"><input type="checkbox" name="brand" value="{e(b)}"> {e(b)}</label>' for b in brands
        )
        prices = [p["price"] for p in items] or [0]
        crumbs = [("Каталог", "catalog/index.html" if group else None)]
        if group:
            crumbs.append(("Велосипеды" if group == "bikes" else "Аксессуары", f"catalog/{group}.html" if category else None))
        if category:
            crumbs.append((category["name"], None))
        body = f"""<div class="wrap page">
  {self.crumbs(root, crumbs)}
  <header class="page__head"><h1>{e(title)}</h1><p>{e(intro)}</p></header>
  <div class="catalog">
    <aside class="side" aria-label="Категории и фильтры">
      <a class="side__title side__all" href="index.html"{"" if group else CURRENT}>Все товары <span>{len(self.products)}</span></a>
      {side}
      <details class="filters-box" data-filters-box hidden>
      <summary class="btn btn--ghost btn--sm">Фильтры</summary>
      <form class="filters" data-filters>
        <fieldset><legend>Цена, сом</legend>
          <div class="range"><input type="number" name="min" inputmode="numeric" placeholder="{min(prices)}" aria-label="Цена от"><span>—</span><input type="number" name="max" inputmode="numeric" placeholder="{max(prices)}" aria-label="Цена до"></div>
        </fieldset>
        <fieldset><legend>Бренд</legend>{brand_boxes}</fieldset>
        <fieldset><legend>Наличие</legend><label class="check"><input type="checkbox" name="available"> Только в наличии</label></fieldset>
        <button class="btn btn--ghost btn--sm" type="reset">Сбросить</button>
      </form>
      </details>
    </aside>
    <section aria-label="Товары">
      <div class="toolbar" data-toolbar hidden>
        <span data-result-count>{len(items)} товаров</span>
        <label>Сортировка
          <select data-sort>
            <option value="popular">По популярности</option>
            <option value="price-asc">Сначала дешевле</option>
            <option value="price-desc">Сначала дороже</option>
            <option value="name">По названию</option>
          </select>
        </label>
      </div>
      {self.grid(items, root)}
      <p class="empty" data-empty hidden></p>
    </section>
  </div>
</div>"""
        active = group or ""
        return self.layout(path, title, f"{title} в Бишкеке: {intro}", body, active=active)

    def product_page(self, p: dict) -> str:
        root = "../"
        cat = self.cat_by_slug[p["category"]]
        label, tone = STATUS[p["status"]]
        specs = "".join(f"<tr><th scope=\"row\">{e(k)}</th><td>{e(v)}</td></tr>" for k, v in p["specs"].items())
        sizes = ""
        if p.get("sizes") and len(p["sizes"]) > 1:
            opts = "".join(
                f'<label class="size"><input type="radio" name="size" value="{e(s)}"{" checked" if i == 0 else ""}><span>{e(s)}</span></label>'
                for i, s in enumerate(p["sizes"])
            )
            sizes = f'<fieldset class="sizes"><legend>Размер{" рамы" if p["group"] == "bikes" else ""} · <a href="../guide.html">как выбрать</a></legend>{opts}</fieldset>'
        elif p.get("sizes"):
            sizes = f'<p class="muted">Размер: {e(p["sizes"][0])}</p>'
        old = f'<s class="price__old">{price(p["old_price"])}</s>' if p.get("old_price") else ""
        fee_key = "bike" if p["group"] == "bikes" else "small"
        region_rows = "".join(
            f"<li><span>{e(r['name'])}</span><b>{price(r[fee_key]) if r[fee_key] else 'бесплатно'}</b></li>"
            for r in self.delivery["regions"][:4]
        )
        if p["status"] == "sold_out":
            buy = f'<a class="btn btn--lg btn--ghost" href="tel:{e(self.shop["phone"])}">Позвонить и узнать о поступлении</a>'
        else:
            buy = (f'<button class="btn btn--lg" type="button" data-add="{e(p["slug"])}" data-with-size>В корзину</button>'
                   f'<button class="btn btn--lg btn--ghost" type="button" data-buy="{e(p["slug"])}" data-with-size>Купить сейчас</button>')
        related = [x for x in self.products if x["category"] == p["category"] and x["slug"] != p["slug"]][:4]
        if len(related) < 4:
            related += [x for x in self.products if x["group"] != p["group"] and x.get("featured")][: 4 - len(related)]
        body = f"""<div class="wrap page">
  {self.crumbs(root, [("Каталог", "catalog/index.html"), (cat["name"], f"catalog/{cat['slug']}.html"), (p["name"], None)])}
  <div class="product" data-product-page="{e(p['slug'])}">
    <div class="product__media"><img src="../assets/img/products/{e(p['slug'])}.svg" alt="{e(p['name'])}" width="480" height="320"></div>
    <div class="product__info">
      <p class="product__brand">{e(p['brand'])} · Артикул {e(p['sku'])}</p>
      <h1>{e(p['name'])}</h1>
      <p class="product__summary">{e(p['summary'])}</p>
      <div class="product__price"><span class="price__now">{price(p['price'])}</span> {old}</div>
      <p class="stock stock--{tone} stock--lg">{label}</p>
      {sizes}
      <div class="product__buy">{buy}</div>
      <div class="product__ship">
        <p><svg class="i" aria-hidden="true"><use href="../assets/img/icons.svg#truck"/></svg><b>Доставка</b> — <a href="../delivery.html">все тарифы</a></p>
        <ul>{region_rows}</ul>
      </div>
    </div>
  </div>
  <div class="product__details">
    <section><h2>Описание</h2><p>{e(p['description'])}</p></section>
    <section><h2>Характеристики</h2><table class="specs"><tbody>{specs}</tbody></table></section>
  </div>
  <section class="section section--flush"><div class="section__head"><h2>Вам может понравиться</h2></div>{self.grid(related, root)}</section>
</div>"""
        ld = {
            "@context": "https://schema.org", "@type": "Product", "name": p["name"], "sku": p["sku"],
            "brand": {"@type": "Brand", "name": p["brand"]}, "description": p["description"],
            "offers": {
                "@type": "Offer", "priceCurrency": "KGS", "price": p["price"],
                "availability": {"in_stock": "https://schema.org/InStock", "preorder": "https://schema.org/PreOrder", "sold_out": "https://schema.org/OutOfStock"}[p["status"]],
            },
        }
        return self.layout(f"product/{p['slug']}.html", p["name"], f"{p['name']} за {price(p['price'])} в Бишкеке. {p['summary']}", body,
                           active=p["group"], extra_head=f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n')

    def delivery_page(self) -> str:
        root = ""
        d = self.delivery
        rows = "".join(
            f"<tr><th scope=\"row\">{e(r['name'])}</th>"
            f"<td>{'Бесплатно' if not r['bike'] else price(r['bike'])}</td>"
            f"<td>{'Бесплатно' if not r['small'] else price(r['small'])}</td>"
            f"<td>{e(r['eta'])}</td></tr>"
            for r in d["regions"]
        )
        pay = "".join(f"<li>{e(x)}</li>" for x in d["payment"])
        body = f"""<div class="wrap page page--narrow">
  {self.crumbs(root, [("Доставка и оплата", None)])}
  <header class="page__head"><h1>Доставка и оплата</h1><p>По Бишкеку доставляем бесплатно {e(d['bishkek']['eta'])}. По Кыргызстану — по тарифу {e(d['carrier'])}.</p></header>
  <div class="callout"><svg class="i i--xl" aria-hidden="true"><use href="assets/img/icons.svg#truck"/></svg><div><b>Бишкек — 0 сом</b><span>Любой заказ, любой суммы. Курьер поможет занести велосипед и проверить его при вас.</span></div></div>
  <section class="prose">
    <h2>Тарифы по Кыргызстану</h2>
    <p>{e(d['note'])}</p>
    <div class="table-wrap">
      <table class="tariffs">
        <thead><tr><th scope="col">Регион</th><th scope="col">Велосипед, за штуку</th><th scope="col">Аксессуары, за заказ</th><th scope="col">Срок</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <p class="muted">Пример: два велосипеда и шлем в Иссык-Кульскую область — 2 × {price(d['regions'][2]['bike'])} + {price(d['regions'][2]['small'])} = {price(2 * d['regions'][2]['bike'] + d['regions'][2]['small'])}. Итоговую сумму доставки форма заказа считает автоматически.</p>
    <h2>Самовывоз</h2>
    <p>Бесплатно из магазина: {e(self.shop['city'])}, {e(self.shop['address'])}. {" · ".join(f"{h['days']} {h['time']}" for h in self.shop['hours'])}. Заказ хранится 5 дней.</p>
    <h2>Оплата</h2>
    <ul>{pay}</ul>
    <h2>Возврат и обмен</h2>
    <p>Велосипед без следов эксплуатации можно вернуть или обменять в течение 14 дней. Доставку обратно по регионам оплачивает покупатель, кроме случаев заводского брака.</p>
  </section>
  <a class="btn btn--lg" href="order.html">Перейти к оформлению заказа</a>
</div>"""
        return self.layout("delivery.html", "Доставка и оплата", "Бесплатная доставка велосипедов по Бишкеку. Тарифы доставки по областям Кыргызстана.", body, active="delivery")

    def order_page(self) -> str:
        regions = "".join(f'<option value="{e(r["slug"])}">{e(r["name"])}</option>' for r in self.delivery["regions"])
        body = f"""<div class="wrap page">
  {self.crumbs("", [("Корзина и заказ", None)])}
  <header class="page__head"><h1>Корзина и оформление заказа</h1></header>
  <noscript><p class="callout">Для оформления онлайн включите JavaScript или позвоните нам: <a href="tel:{e(self.shop['phone'])}">{e(self.shop['phone_display'])}</a>.</p></noscript>
  <div class="order" data-order>
    <section class="order__cart" aria-labelledby="cart-title">
      <h2 id="cart-title">Товары</h2>
      <ul class="cart" data-cart-items></ul>
      <div class="cart-empty" data-cart-empty hidden>
        <p>Корзина пуста.</p>
        <a class="btn" href="catalog/bikes.html">Выбрать велосипед</a>
        <a class="btn btn--ghost" href="catalog/accessories.html">Аксессуары</a>
      </div>
    </section>
    <form class="order__form" data-order-form novalidate>
      <h2>Получатель</h2>
      <div class="field"><label for="o-name">Имя и фамилия</label><input id="o-name" name="name" autocomplete="name" required></div>
      <div class="field"><label for="o-phone">Телефон</label><input id="o-phone" name="phone" type="tel" inputmode="tel" autocomplete="tel" placeholder="0XXX XX XX XX" required></div>
      <h2>Доставка</h2>
      <div class="segmented" role="radiogroup" aria-label="Способ получения">
        <label><input type="radio" name="method" value="courier" checked><span>Курьером</span></label>
        <label><input type="radio" name="method" value="pickup"><span>Самовывоз</span></label>
      </div>
      <div data-courier>
        <div class="field"><label for="o-region">Регион</label><select id="o-region" name="region">{regions}</select></div>
        <div class="field"><label for="o-city">Город или село</label><input id="o-city" name="city" autocomplete="address-level2" value="Бишкек"></div>
        <div class="field"><label for="o-address">Адрес: улица, дом, квартира</label><input id="o-address" name="address" autocomplete="street-address" required></div>
      </div>
      <p class="muted" data-pickup hidden>Заберите заказ по адресу {e(self.shop['city'])}, {e(self.shop['address'])}. {" · ".join(f"{h['days']} {h['time']}" for h in self.shop['hours'])}.</p>
      <div class="field"><label for="o-comment">Комментарий <span class="muted">(необязательно)</span></label><textarea id="o-comment" name="comment" rows="3" placeholder="Удобное время доставки, этаж, домофон"></textarea></div>
      <h2>Оплата</h2>
      <div class="field"><select name="payment" aria-label="Способ оплаты">
        <option value="cash">Наличными при получении</option>
        <option value="card">Картой при получении</option>
        <option value="qr">QR-переводом</option>
      </select></div>
      <dl class="summary">
        <div><dt>Товары</dt><dd data-sum-items>0 сом</dd></div>
        <div><dt>Доставка</dt><dd data-sum-delivery>Бесплатно</dd></div>
        <div class="summary__total"><dt>Итого</dt><dd data-sum-total>0 сом</dd></div>
      </dl>
      <p class="muted small" data-delivery-note></p>
      <p class="form-error" data-form-error role="alert" hidden></p>
      <button class="btn btn--lg btn--block" type="submit">Оформить заказ</button>
      <p class="muted small">Нажимая кнопку, вы соглашаетесь, что менеджер перезвонит для подтверждения заказа.</p>
    </form>
  </div>
  <section class="done" data-order-done hidden tabindex="-1">
    <svg class="i i--xl" aria-hidden="true"><use href="assets/img/icons.svg#check"/></svg>
    <h2>Спасибо! Заказ <span data-order-number></span> принят</h2>
    <p>Менеджер перезвонит в рабочее время, чтобы подтвердить заказ и время доставки. Если вопрос срочный — звоните: <a href="tel:{e(self.shop['phone'])}">{e(self.shop['phone_display'])}</a>.</p>
    <a class="btn" href="index.html">На главную</a>
  </section>
</div>"""
        return self.layout("order.html", "Корзина и заказ", "Оформление заказа с доставкой по Бишкеку и Кыргызстану.", body, scripts=("order.js",))

    def guide_page(self) -> str:
        rows = [
            ("150–165", "S / 15–16\"", "48–50 см", "Беговел 12\" — 2–4 года"),
            ("165–175", "M / 17–18\"", "52–54 см", "16\" — 4–6 лет, рост 105–120 см"),
            ("175–185", "L / 19–20\"", "56–58 см", "20\" — 6–9 лет, рост 120–140 см"),
            ("185–195", "XL / 21–22\"", "58–60 см", "24\" — 9–12 лет, рост 135–150 см"),
        ]
        table = "".join(f"<tr><th scope=\"row\">{a}</th><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in rows)
        body = f"""<div class="wrap page page--narrow">
  {self.crumbs("", [("Как выбрать велосипед", None)])}
  <header class="page__head"><h1>Как выбрать велосипед</h1><p>Тип, размер рамы и что проверить при покупке.</p></header>
  <section class="prose">
    <h2>1. Определитесь с типом</h2>
    <ul>
      <li><b>Горный</b> — для гор, грунта и плохого асфальта. Широкие покрышки и амортизационная вилка.</li>
      <li><b>Шоссейный</b> — для быстрых поездок по асфальту. Лёгкий, с узкими покрышками и рулём-баранкой.</li>
      <li><b>Гравийный</b> — шоссейник с широкими покрышками: асфальт, грунтовки и туризм.</li>
      <li><b>Городской</b> — прямая посадка, крылья и багажник. Для работы, учёбы и покупок.</li>
      <li><b>Электро</b> — мотор помогает крутить педали, удобно для дальних поездок и подъёмов.</li>
      <li><b>Складной</b> — для тех, кто возит велосипед в машине или хранит в маленькой квартире.</li>
    </ul>
    <h2>2. Подберите размер</h2>
    <div class="table-wrap"><table class="tariffs">
      <thead><tr><th scope="col">Рост, см</th><th scope="col">Горный / городской</th><th scope="col">Шоссе и гравий</th><th scope="col">Детские</th></tr></thead>
      <tbody>{table}</tbody>
    </table></div>
    <p class="muted">Если рост на границе двух размеров: для активного катания берите меньший, для прогулок и комфорта — больший. В магазине подберём размер на примерке.</p>
    <h2>3. Что проверить при покупке</h2>
    <ul>
      <li>Стоя над рамой, между верхней трубой и пахом должно оставаться 5–10 см.</li>
      <li>В нижней точке педали нога почти полностью выпрямлена.</li>
      <li>До руля удобно тянуться, спина и плечи не напряжены.</li>
      <li>Тормоза срабатывают при неполном нажатии ручки.</li>
    </ul>
    <h2>4. Не забудьте аксессуары</h2>
    <p>Минимальный набор для города — <a href="catalog/helmets.html">шлем</a>, <a href="catalog/locks.html">замок</a> и <a href="catalog/lights.html">фонари</a>. Для поездок за город добавьте <a href="catalog/pumps.html">насос</a>, <a href="catalog/parts.html">запасную камеру и мультитул</a>.</p>
  </section>
</div>"""
        return self.layout("guide.html", "Как выбрать велосипед", "Таблица размеров рам и советы по выбору велосипеда.", body, active="guide")

    def blog_index(self) -> str:
        posts = "".join(
            f"""<article class="post-card post-card--lg"><time datetime="{p['date']}">{human_date(p['date'])}</time>
<h2><a href="{p['slug']}.html">{e(p['title'])}</a></h2><p>{e(p['excerpt'])}</p><a class="link-arrow" href="{p['slug']}.html">Читать</a></article>"""
            for p in self.posts
        )
        body = f"""<div class="wrap page">
  {self.crumbs("../", [("Блог", None)])}
  <header class="page__head"><h1>Блог</h1><p>Советы механиков, маршруты и обзоры.</p></header>
  <div class="posts">{posts}</div>
</div>"""
        return self.layout("blog/index.html", "Блог", "Советы по обслуживанию велосипеда и маршруты вокруг Бишкека.", body, active="blog")

    def post_page(self, post: dict) -> str:
        paragraphs = "".join(
            f"<h2>{e(block[3:])}</h2>" if block.startswith("## ") else f"<p>{e(block)}</p>" for block in post["body"]
        )
        body = f"""<div class="wrap page page--narrow">
  {self.crumbs("../", [("Блог", "blog/index.html"), (post["title"], None)])}
  <article class="prose">
    <header class="page__head"><h1>{e(post['title'])}</h1><p class="muted"><time datetime="{post['date']}">{human_date(post['date'])}</time> · {e(post['author'])}</p></header>
    {paragraphs}
  </article>
  <a class="link-arrow" href="index.html">Все статьи</a>
</div>"""
        return self.layout(f"blog/{post['slug']}.html", post["title"], post["excerpt"], body, active="blog")

    def news_page(self) -> str:
        items = "".join(
            f'<li class="timeline__item"><time datetime="{n["date"]}">{human_date(n["date"])}</time><h2>{e(n["title"])}</h2><p>{e(n["body"])}</p></li>'
            for n in self.news
        )
        body = f"""<div class="wrap page page--narrow">
  {self.crumbs("", [("Новости", None)])}
  <header class="page__head"><h1>Новости магазина</h1><p>Поставки, изменения цен и графика работы.</p></header>
  <ol class="timeline">{items}</ol>
</div>"""
        return self.layout("news.html", "Новости", "Новые поставки, изменения цен и графика работы магазина.", body, active="news")

    def contacts_page(self) -> str:
        hours = "".join(f"<li><span>{e(h['days'])}</span><b>{e(h['time'])}</b></li>" for h in self.shop["hours"])
        body = f"""<div class="wrap page">
  {self.crumbs("", [("Контакты", None)])}
  <header class="page__head"><h1>Контакты</h1><p>Магазин и мастерская в одном месте.</p></header>
  <div class="contacts">
    <div class="contacts__card">
      <h2>Телефон</h2>
      <a class="visit__phone" href="tel:{e(self.shop['phone'])}">{e(self.shop['phone_display'])}</a>
      <p class="muted">Звонки и WhatsApp в рабочее время.</p>
    </div>
    <div class="contacts__card">
      <h2>Адрес</h2>
      <p class="visit__addr">{e(self.shop['city'])}, {e(self.shop['address'])}</p>
      <a class="link-arrow" href="{e(self.shop['map_url'])}" target="_blank" rel="noopener">Открыть на карте</a>
    </div>
    <div class="contacts__card">
      <h2>Режим работы</h2>
      <ul class="hours">{hours}</ul>
      <p class="muted" data-open-status-text></p>
    </div>
  </div>
</div>"""
        return self.layout("contacts.html", "Контакты", f"{self.shop['city']}, {self.shop['address']}. Телефон {self.shop['phone']}.", body, active="contacts")

    def not_found(self) -> str:
        # Served from any depth, so links are absolute from the site root.
        body = """<div class="wrap page page--narrow notfound">
  <p class="eyebrow">Ошибка 404</p>
  <h1>Такой страницы нет</h1>
  <p>Возможно, товар закончился или ссылка устарела.</p>
  <a class="btn" href="/index.html">На главную</a> <a class="btn btn--ghost" href="/catalog/index.html">В каталог</a>
</div>"""
        return self.layout("404.html", "Страница не найдена", "Страница не найдена.", body, root="/")

    def sitemap(self) -> str:
        urls = "".join(f"<url><loc>/{p}</loc></url>" for p in sorted(self.pages))
        return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "public", help="output directory (default: public)")
    args = parser.parse_args()
    site = Site(args.out)
    site.build()
    print(f"Built {len(site.pages)} pages into {args.out}")


if __name__ == "__main__":
    main()
