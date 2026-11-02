// Shared behaviour: cart storage, header badge, add-to-cart, catalog
// filters, mobile menu and the "open now" indicator. Pages work without it;
// it only adds interactivity on top of the static markup.
(function () {
  "use strict";

  var DATA = window.SA_DATA || { products: {}, regions: [], hours: [] };
  var ROOT = document.body.getAttribute("data-root") || "";
  var CART_KEY = "sa-cart";

  // ── Cart storage ─────────────────────────────────────────────────────
  // A cart line is { slug, size, qty }; the same product in two sizes is two lines.
  function readCart() {
    try {
      var lines = JSON.parse(localStorage.getItem(CART_KEY) || "[]");
      return Array.isArray(lines) ? lines.filter(function (l) { return DATA.products[l.slug] && l.qty > 0; }) : [];
    } catch (err) {
      return [];
    }
  }

  function writeCart(lines) {
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(lines));
    } catch (err) {
      /* storage unavailable: the cart lives only for this page view */
    }
    renderCount(true);
    document.dispatchEvent(new CustomEvent("sa:cart"));
  }

  function addToCart(slug, size, qty) {
    var lines = readCart();
    var line = lines.find(function (l) { return l.slug === slug && (l.size || "") === (size || ""); });
    if (line) line.qty = Math.min(line.qty + qty, 20);
    else lines.push({ slug: slug, size: size || "", qty: qty });
    writeCart(lines);
  }

  function cartCount() {
    return readCart().reduce(function (n, l) { return n + l.qty; }, 0);
  }

  function renderCount(bump) {
    var n = cartCount();
    document.querySelectorAll("[data-cart-count]").forEach(function (el) {
      el.textContent = String(n);
      el.hidden = n === 0;
      if (bump && n) {
        el.classList.remove("bump");
        void el.offsetWidth; // restart the animation
        el.classList.add("bump");
      }
    });
  }

  // ── Formatting ───────────────────────────────────────────────────────
  function formatPrice(value) {
    return value.toLocaleString("ru-RU").replace(/\s/g, " ") + " сом";
  }

  // ── Toast ────────────────────────────────────────────────────────────
  var toastTimer;
  function toast(text, link) {
    var el = document.querySelector(".toast");
    if (!el) return;
    el.textContent = text;
    if (link) {
      var a = document.createElement("a");
      a.href = link.href;
      a.textContent = link.label;
      el.appendChild(a);
    }
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.hidden = true; }, 3500);
  }

  // ── Add to cart / buy now ────────────────────────────────────────────
  function selectedSize(button) {
    if (!button.hasAttribute("data-with-size")) return "";
    var checked = document.querySelector('input[name="size"]:checked');
    return checked ? checked.value : "";
  }

  document.addEventListener("click", function (event) {
    var add = event.target.closest("[data-add]");
    var buy = event.target.closest("[data-buy]");
    var button = add || buy;
    if (!button) return;
    var slug = button.getAttribute(add ? "data-add" : "data-buy");
    var product = DATA.products[slug];
    if (!product) return;
    // Catalog cards have no size picker: default to the first size.
    var size = selectedSize(button) || product.sizes[0] || "";
    addToCart(slug, size, 1);
    if (buy) {
      window.location.href = ROOT + "order.html";
      return;
    }
    toast("«" + product.name + "» в корзине", { href: ROOT + "order.html", label: "Оформить" });
  });

  // ── Mobile menu ──────────────────────────────────────────────────────
  var burger = document.querySelector(".burger");
  var navList = document.getElementById("nav-list");
  if (burger && navList) {
    burger.addEventListener("click", function () {
      var open = burger.getAttribute("aria-expanded") !== "true";
      burger.setAttribute("aria-expanded", String(open));
      navList.classList.toggle("is-open", open);
    });
  }

  // ── Open now (shop time is Asia/Bishkek) ─────────────────────────────
  function bishkekNow() {
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Bishkek", weekday: "long", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).formatToParts(new Date());
    var get = function (type) { return parts.find(function (p) { return p.type === type; }).value; };
    return { day: get("weekday"), minutes: Number(get("hour")) * 60 + Number(get("minute")) };
  }

  function toMinutes(hhmm) {
    var p = hhmm.split(":");
    return Number(p[0]) * 60 + Number(p[1]);
  }

  function openStatus() {
    var now = bishkekNow();
    var today = DATA.hours.find(function (h) { return h.days.indexOf(now.day) !== -1; });
    if (today && now.minutes >= toMinutes(today.open) && now.minutes < toMinutes(today.close)) {
      return { open: true, text: "Открыто до " + today.close };
    }
    if (today && now.minutes < toMinutes(today.open)) {
      return { open: false, text: "Закрыто · откроемся в " + today.open };
    }
    var week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    var tomorrow = week[(week.indexOf(now.day) + 1) % 7];
    var next = DATA.hours.find(function (h) { return h.days.indexOf(tomorrow) !== -1; });
    return { open: false, text: "Закрыто · завтра с " + (next ? next.open : "") };
  }

  try {
    var status = openStatus();
    document.querySelectorAll("[data-open-status]").forEach(function (el) {
      var dot = document.createElement("span");
      dot.className = "open-dot" + (status.open ? " open-dot--on" : "");
      dot.setAttribute("aria-hidden", "true");
      var label = document.createElement("b");
      label.textContent = status.text;
      el.prepend(dot, label, document.createTextNode(" · "));
    });
    document.querySelectorAll("[data-open-status-text]").forEach(function (el) {
      el.textContent = "Сейчас: " + status.text.toLowerCase();
    });
  } catch (err) {
    /* Intl without time zone support: keep the static hours */
  }

  // ── Catalog filters and sorting ──────────────────────────────────────
  var form = document.querySelector("[data-filters]");
  var grid = document.querySelector(".catalog .grid");
  if (form && grid) {
    var toolbar = document.querySelector("[data-toolbar]");
    var sortSelect = document.querySelector("[data-sort]");
    var countEl = document.querySelector("[data-result-count]");
    var emptyEl = document.querySelector("[data-empty]");
    // Filled here, not in the markup, so text-only readers don't see it.
    emptyEl.textContent = "Ничего не нашлось. Попробуйте изменить фильтры.";
    var cards = Array.prototype.slice.call(grid.querySelectorAll("[data-product]"));
    cards.forEach(function (card, i) { card.dataset.order = String(i); });
    var box = document.querySelector("[data-filters-box]");
    box.hidden = false;
    // Open beside the grid on wide screens, collapsed above it on narrow ones.
    var wide = window.matchMedia("(min-width: 1025px)");
    var syncBox = function () { box.open = wide.matches; };
    wide.addEventListener("change", syncBox);
    syncBox();
    toolbar.hidden = false;

    var plural = function (n) {
      var mod10 = n % 10, mod100 = n % 100;
      if (mod10 === 1 && mod100 !== 11) return n + " товар";
      if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return n + " товара";
      return n + " товаров";
    };

    var apply = function () {
      var min = Number(form.elements.min.value) || 0;
      var max = Number(form.elements.max.value) || Infinity;
      var brands = Array.prototype.slice.call(form.querySelectorAll('input[name="brand"]:checked')).map(function (b) { return b.value; });
      var availableOnly = form.elements.available.checked;
      var shown = 0;
      cards.forEach(function (card) {
        var price = Number(card.dataset.price);
        var visible =
          price >= min && price <= max &&
          (!brands.length || brands.indexOf(card.dataset.brand) !== -1) &&
          (!availableOnly || card.dataset.status === "in_stock");
        card.hidden = !visible;
        if (visible) shown++;
      });
      countEl.textContent = plural(shown);
      emptyEl.hidden = shown !== 0;

      var mode = sortSelect.value;
      var sorted = cards.slice().sort(function (a, b) {
        if (mode === "price-asc") return a.dataset.price - b.dataset.price;
        if (mode === "price-desc") return b.dataset.price - a.dataset.price;
        if (mode === "name") return a.querySelector(".card__title").textContent.localeCompare(b.querySelector(".card__title").textContent, "ru");
        return a.dataset.order - b.dataset.order;
      });
      sorted.forEach(function (card) { grid.appendChild(card); });
    };

    form.addEventListener("input", apply);
    form.addEventListener("change", apply);
    form.addEventListener("reset", function () { setTimeout(apply, 0); });
    sortSelect.addEventListener("change", apply);
    apply();
  }

  renderCount(false);
  window.addEventListener("storage", function (e) { if (e.key === CART_KEY) renderCount(false); });

  window.SA = { readCart: readCart, writeCart: writeCart, formatPrice: formatPrice, root: ROOT };
})();
