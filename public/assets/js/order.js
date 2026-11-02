// Cart and checkout on order.html. There is no backend: a placed order is
// kept in localStorage ("sa-orders") and the cart is cleared.
(function () {
  "use strict";

  var DATA = window.SA_DATA;
  var SA = window.SA;
  var root = document.querySelector("[data-order]");
  if (!root || !DATA || !SA) return;

  var list = root.querySelector("[data-cart-items]");
  var empty = root.querySelector("[data-cart-empty]");
  var form = root.querySelector("[data-order-form]");
  var courierBlock = form.querySelector("[data-courier]");
  var pickupNote = form.querySelector("[data-pickup]");
  var errorBox = form.querySelector("[data-form-error]");
  var done = document.querySelector("[data-order-done]");

  function region() {
    var slug = form.elements.region.value;
    return DATA.regions.find(function (r) { return r.slug === slug; }) || DATA.regions[0];
  }

  function method() {
    return form.querySelector('input[name="method"]:checked').value;
  }

  /** Bikes pay the carrier's per-bike tariff; accessories ship as one small parcel. */
  function deliveryFee(lines) {
    if (method() === "pickup") return 0;
    var r = region();
    var bikes = 0;
    var hasSmall = false;
    lines.forEach(function (l) {
      if (DATA.products[l.slug].group === "bikes") bikes += l.qty;
      else hasSmall = true;
    });
    return bikes * r.bike + (hasSmall ? r.small : 0);
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderLines(lines) {
    list.textContent = "";
    lines.forEach(function (line, index) {
      var p = DATA.products[line.slug];
      var li = el("li", "cart__item");

      var img = el("img", "cart__img");
      img.src = SA.root + "assets/img/products/" + line.slug + ".svg";
      img.alt = "";
      img.width = 96;
      img.height = 64;

      var info = el("div");
      var name = el("a", "cart__name", p.name);
      name.href = SA.root + "product/" + line.slug + ".html";
      var meta = [p.sku];
      if (line.size) meta.push("Размер " + line.size);
      if (p.status === "preorder") meta.push("Под заказ");
      info.append(name, el("div", "cart__meta", meta.join(" · ")), el("div", "cart__meta", SA.formatPrice(p.price) + " за шт."));

      var side = el("div", "cart__side");
      side.appendChild(el("b", "", SA.formatPrice(p.price * line.qty)));
      var qty = el("div", "qty");
      var minus = el("button", "", "−");
      minus.type = "button";
      minus.setAttribute("aria-label", "Уменьшить количество");
      var count = el("output", "", String(line.qty));
      count.setAttribute("aria-label", "Количество");
      var plus = el("button", "", "+");
      plus.type = "button";
      plus.setAttribute("aria-label", "Увеличить количество");
      minus.addEventListener("click", function () { changeQty(index, -1); });
      plus.addEventListener("click", function () { changeQty(index, 1); });
      qty.append(minus, count, plus);
      var remove = el("button", "cart__remove", "Удалить");
      remove.type = "button";
      remove.addEventListener("click", function () { changeQty(index, -Infinity); });
      side.append(qty, remove);

      li.append(img, info, side);
      list.appendChild(li);
    });
  }

  function changeQty(index, delta) {
    var lines = SA.readCart();
    var line = lines[index];
    if (!line) return;
    line.qty = Math.min(Math.max(line.qty + delta, 0), 20);
    SA.writeCart(lines.filter(function (l) { return l.qty > 0; }));
  }

  function renderTotals() {
    var lines = SA.readCart();
    var items = lines.reduce(function (sum, l) { return sum + DATA.products[l.slug].price * l.qty; }, 0);
    var fee = deliveryFee(lines);
    form.querySelector("[data-sum-items]").textContent = SA.formatPrice(items);
    form.querySelector("[data-sum-delivery]").textContent = fee ? SA.formatPrice(fee) : "Бесплатно";
    form.querySelector("[data-sum-total]").textContent = SA.formatPrice(items + fee);

    var note = form.querySelector("[data-delivery-note]");
    if (method() === "pickup") note.textContent = "Самовывоз бесплатно.";
    else if (region().slug === "bishkek") note.textContent = "По Бишкеку доставка бесплатная, " + region().eta + ".";
    else note.textContent = region().name + ": тариф курьерской службы, срок " + region().eta + ".";
  }

  function render() {
    var lines = SA.readCart();
    empty.hidden = lines.length > 0;
    list.hidden = lines.length === 0;
    form.hidden = lines.length === 0;
    renderLines(lines);
    renderTotals();
  }

  function syncMethod() {
    var pickup = method() === "pickup";
    courierBlock.hidden = pickup;
    pickupNote.hidden = !pickup;
    form.elements.address.required = !pickup;
    renderTotals();
  }

  form.addEventListener("change", function (e) {
    if (e.target.name === "method") syncMethod();
    if (e.target.name === "region") {
      var city = form.elements.city;
      if (region().slug === "bishkek") city.value = "Бишкек";
      else if (city.value === "Бишкек") city.value = "";
      renderTotals();
    }
  });

  // ── Validation & submit ──────────────────────────────────────────────
  function setError(input, message) {
    var field = input.closest(".field");
    var old = field.querySelector(".field__error");
    if (old) old.remove();
    field.classList.toggle("field--error", !!message);
    input.setAttribute("aria-invalid", message ? "true" : "false");
    if (message) {
      var hint = el("span", "field__error", message);
      hint.id = input.id + "-error";
      input.setAttribute("aria-describedby", hint.id);
      field.appendChild(hint);
    } else {
      input.removeAttribute("aria-describedby");
    }
  }

  function validate() {
    var f = form.elements;
    var problems = [];
    var check = function (input, message) {
      setError(input, message);
      if (message) problems.push(input);
    };
    check(f.name, f.name.value.trim().length < 2 ? "Укажите имя" : "");
    var digits = f.phone.value.replace(/\D/g, "");
    check(f.phone, digits.length < 9 || digits.length > 13 ? "Укажите номер телефона, например 0555 12 34 56" : "");
    if (method() === "courier") {
      check(f.city, f.city.value.trim() ? "" : "Укажите город или село");
      check(f.address, f.address.value.trim().length < 5 ? "Укажите улицу и дом" : "");
    } else {
      setError(f.city, "");
      setError(f.address, "");
    }
    return problems;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var lines = SA.readCart();
    var problems = validate();
    errorBox.hidden = true;
    if (!lines.length) {
      errorBox.textContent = "Корзина пуста.";
      errorBox.hidden = false;
      return;
    }
    if (problems.length) {
      problems[0].focus();
      return;
    }

    var f = form.elements;
    var items = lines.reduce(function (sum, l) { return sum + DATA.products[l.slug].price * l.qty; }, 0);
    var fee = deliveryFee(lines);
    var number = "SA-" + Date.now().toString(36).toUpperCase().slice(-6);
    var order = {
      number: number,
      created_at: new Date().toISOString(),
      customer: { name: f.name.value.trim(), phone: f.phone.value.trim() },
      delivery: method() === "pickup"
        ? { method: "pickup" }
        : { method: "courier", region: region().slug, city: f.city.value.trim(), address: f.address.value.trim(), fee: fee },
      payment: f.payment.value,
      comment: f.comment.value.trim(),
      lines: lines.map(function (l) {
        var p = DATA.products[l.slug];
        return { slug: l.slug, sku: p.sku, name: p.name, size: l.size, qty: l.qty, price: p.price };
      }),
      total: items + fee,
    };
    try {
      var orders = JSON.parse(localStorage.getItem("sa-orders") || "[]");
      orders.push(order);
      localStorage.setItem("sa-orders", JSON.stringify(orders));
    } catch (err) {
      /* storage unavailable: still show the confirmation */
    }
    SA.writeCart([]);
    root.hidden = true;
    done.querySelector("[data-order-number]").textContent = number;
    done.hidden = false;
    done.focus();
    window.scrollTo(0, 0);
  });

  document.addEventListener("sa:cart", render);
  window.addEventListener("storage", function (e) { if (e.key === "sa-cart") render(); });
  syncMethod();
  render();
})();
