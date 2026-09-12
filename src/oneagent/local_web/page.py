SHOP_PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OneAgent shop</title>
  <style>
    :root { color-scheme: light; --bg: #fff; --ink: #202020; --muted: #717171; --line: #e5e7eb; --accent: #009bd8; }
    * { box-sizing: border-box; }
    body { margin: 0; font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: var(--bg); }
    button, input { font: inherit; }
    button, a { -webkit-tap-highlight-color: transparent; }
    button { cursor: pointer; }
    button:focus-visible, a:focus-visible, input:focus-visible { outline: 3px solid #009bd8; outline-offset: 3px; }
    a { color: inherit; }
    .announcement { background: #009bd8; color: white; text-align: center; padding: 11px 20px; font-size: 11px; font-weight: 750; letter-spacing: 1.8px; }
    header { padding: 22px 32px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--line); gap: 20px; }
    h1 { font-size: 21px; margin: 0; letter-spacing: -.8px; }
    h1 span { color: var(--accent); font-weight: 400; }
    .header-links { display: flex; align-items: center; gap: 24px; font-size: 12px; color: var(--muted); }
    .local-label { border: 1px solid #cbeaf4; border-radius: 99px; padding: 6px 12px; color: #067da5; background: #f2fbff; }
    .need { color: var(--muted); margin: 0; font-size: 12px; }
    .search-context { padding: 12px 32px 0; }
    .layout { display: grid; grid-template-columns: minmax(0, 1fr) 355px; gap: 30px; padding: 16px 32px 40px; max-width: 1800px; margin: auto; align-items: start; }
    .panel { min-width: 0; }
    .tabs { display: flex; gap: 8px; overflow-x: auto; padding: 0 0 20px; }
    .tab { flex: 0 0 auto; padding: 9px 15px; border: 1px solid var(--line); border-radius: 99px; background: white; color: var(--muted); font-size: 12px; white-space: nowrap; }
    .tab[aria-selected="true"] { background: #202020; color: white; border-color: #202020; }
    .product { min-height: 450px; }
    .store-heading { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin: 5px 0 22px; }
    .merchant-logo { text-transform: uppercase; font-size: 18px; font-weight: 800; letter-spacing: -1px; }
    .merchant-logo span { color: var(--accent); font-weight: 400; text-transform: lowercase; }
    .source-link { color: var(--muted); font-size: 11px; text-decoration: none; }
    .product-message { display: grid; grid-template-columns: minmax(0, 1.13fr) minmax(0, 1fr); gap: 28px; }
    .preview { min-width: 0; }
    .hero-image { width: 100%; height: 450px; object-fit: contain; display: block; cursor: zoom-in; background: white; }
    .gallery-thumbs { display: flex; gap: 7px; margin-top: 15px; overflow-x: auto; padding-bottom: 6px; }
    .gallery-thumb { padding: 3px; background: white; border: 1px solid transparent; border-radius: 5px; flex: 0 0 50px; }
    .gallery-thumb[aria-pressed="true"] { border-color: #202020; }
    .gallery-thumb img { width: 43px; height: 48px; object-fit: contain; display: block; }
    .gallery-hint { text-align: center; color: #969696; font-size: 10px; margin-top: 12px; }
    .product-copy { min-width: 0; padding-top: 8px; }
    .eyebrow { color: #008dbf; font-size: 10px; font-weight: 700; letter-spacing: 1.7px; text-transform: uppercase; margin: 0 0 12px; }
    .product-copy h2 { margin: 0 0 21px; font-size: clamp(23px, 2.1vw, 32px); line-height: 1.22; letter-spacing: -.9px; }
    .price-row { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 9px; }
    .price { color: #fb3e3e; font-size: 24px; font-weight: 600; }
    .original-price { color: #777; font-size: 14px; }
    .saving { border-radius: 99px; background: #ff4040; color: white; padding: 3px 8px; font-size: 10px; font-weight: 700; }
    .snapshot-note { font-size: 10px; color: #8a8a8a; line-height: 1.6; }
    .options { border-top: 1px solid var(--line); padding-top: 24px; margin-top: 23px; }
    .option-label { font-size: 13px; margin: 0 0 10px; color: var(--muted); }
    .option-label strong { color: #202020; }
    .variant-options { display: flex; flex-wrap: wrap; gap: 8px; }
    .variant { background: white; border: 1px solid #ddd; border-radius: 99px; padding: 10px 14px; font-size: 12px; }
    .variant[aria-pressed="true"] { border: 2px solid #202020; padding: 9px 13px; }
    .availability { color: #377a52; font-size: 11px; margin: 12px 0 24px; }
    .merchant-cta, .ask-product { display: block; width: 100%; text-align: center; padding: 13px 14px; border-radius: 99px; font-size: 12px; font-weight: 700; text-decoration: none; }
    .merchant-cta { background: #202020; color: white; border: 1px solid #202020; }
    .ask-product { margin-top: 10px; background: white; color: #008bbf; border: 1px solid #009bd8; }
    .product-details { border-top: 1px solid var(--line); margin-top: 24px; padding-top: 15px; color: var(--muted); font-size: 12px; }
    .product-details summary { cursor: pointer; color: #202020; font-weight: 600; }
    .product-details p { line-height: 1.8; }
    .empty, .meta { color: var(--muted); }
    .chat-panel { position: sticky; top: 18px; display: flex; flex-direction: column; height: calc(100vh - 184px); min-height: 480px; max-height: 850px; border: 1px solid var(--line); border-radius: 15px; overflow: hidden; box-shadow: 0 4px 24px #00000004; background: #fafbfc; }
    .chat-heading { padding: 20px 18px 15px; background: white; border-bottom: 1px solid var(--line); }
    .bot-title { display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 700; }
    .bot-icon { width: 31px; height: 31px; display: grid; place-items: center; background: #e3f6fd; color: #008bbf; border-radius: 10px; font-size: 19px; }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; background: #009bd8; margin-left: auto; }
    .chat-subtitle { font-size: 11px; color: var(--muted); margin: 9px 0 0; }
    #chat-product { display: block; margin-top: 4px; color: #0081ad; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .suggestions { display: flex; flex-wrap: wrap; gap: 6px; padding: 12px 14px 4px; }
    .suggestions button { background: white; border: 1px solid #dce7eb; border-radius: 7px; padding: 6px 8px; color: #49636b; font-size: 10px; }
    .chat-log { flex: 1; min-height: 100px; overflow: auto; padding: 15px 14px; display: flex; flex-direction: column; gap: 15px; font-size: 12px; }
    .bubble { padding: 11px 13px; border-radius: 12px; max-width: 95%; overflow-wrap: anywhere; }
    .bubble.plain { white-space: pre-wrap; }
    .you { align-self: flex-end; background: #e4f5fc; color: #163d4c; }
    .oneagent { align-self: flex-start; background: white; border: 1px solid #edf0f2; }
    .oneagent p { margin: 0 0 9px; }
    .oneagent p:last-child { margin-bottom: 0; }
    .oneagent ul { margin: 0 0 8px; padding-left: 17px; }
    .oneagent a { color: #0087b8; }
    .pending { color: var(--muted); font-style: italic; }
    .turn { display: flex; flex-direction: column; gap: 10px; }
    form { display: flex; gap: 8px; padding: 13px; background: white; border-top: 1px solid var(--line); order: 5; }
    input[type="text"] { min-width: 0; flex: 1; border: 1px solid var(--line); border-radius: 9px; padding: 11px 10px; font-size: 12px; }
    #composer button { background: #009bd8; color: white; border: 0; border-radius: 9px; padding: 10px 12px; font-size: 12px; }
    #composer button:disabled { opacity: .5; cursor: wait; }
    dialog { border: 0; border-radius: 14px; padding: 20px; max-width: 95vw; }
    dialog::backdrop { background: #0009; }
    dialog img { display: block; max-height: 80vh; max-width: 85vw; }
    dialog button { display: block; margin-left: auto; background: white; border: 1px solid #ddd; border-radius: 99px; padding: 5px 15px; }
    @media (min-width: 1550px) { .hero-image { height: 580px; } .layout { grid-template-columns: minmax(0, 1fr) 390px; gap: 40px; } }
    @media (max-width: 1150px) { .layout { grid-template-columns: minmax(0, 1fr) 320px; gap: 20px; padding: 16px 20px 30px; } .product-message { grid-template-columns: 1fr; } .hero-image { height: 350px; } .product-copy { max-width: 580px; } }
    @media (max-width: 760px) { header { padding: 18px; } .header-links > a { display: none; } .search-context { padding: 12px 18px 0; } .layout { grid-template-columns: 1fr; padding: 15px 18px 30px; } .chat-panel { position: static; height: 600px; min-height: 400px; } .hero-image { height: 370px; } .announcement { font-size: 9px; } }
  </style>
</head>
<body>
  <div class="announcement">YOUR NEXT SWIM, WITH A SOUNDTRACK</div>
  <header>
    <h1>OneAgent<span> shop</span></h1>
    <div class="header-links"><a href="https://www.underwateraudio.com/products/syryn-mp3-player" target="_blank" rel="noopener noreferrer">Merchant website ↗</a><span class="local-label">Local product preview</span></div>
  </header>
  <div class="search-context"><p class="need" id="need">Loading shortlist…</p><p class="need" id="jump" hidden></p></div>
  <main class="layout">
    <section class="panel" aria-label="Product details">
      <div class="tabs" id="tabs" role="tablist" aria-label="Shopping results"></div>
      <div class="product" id="product"></div>
    </section>
    <aside class="panel chat-panel" aria-label="Chat with OneAgent">
      <div class="chat-heading"><div class="bot-title"><span class="bot-icon" aria-hidden="true">✳</span>OneAgent<span class="status-dot"></span></div><p class="chat-subtitle">Ask about the product you're viewing.<span id="chat-product">Your shopping assistant</span></p></div>
      <div class="suggestions"><button type="button" data-question="Is this a good choice for swimming?">Good for swimming?</button><button type="button" data-question="Compare this with the other option.">Compare options</button><button type="button" data-question="How do I load music onto this product?">How does it work?</button></div>
      <form id="composer">
        <input id="message" aria-label="Message OneAgent" type="text" maxlength="4000" placeholder="Ask about this product…" autocomplete="off">
        <button type="submit">Send</button>
      </form>
      <div class="chat-log" id="log" role="log" aria-live="polite"></div>
    </aside>
  </main>
  <dialog id="image-zoom"><button type="button">Close</button><img alt="Product image enlarged"></dialog>
  <script>
    const params = new URLSearchParams(location.search);
    const token = params.get("token") || sessionStorage.getItem("oneagentLocalWebToken") || "";
    if (params.get("token")) sessionStorage.setItem("oneagentLocalWebToken", token);
    const parts = location.pathname.split("/").filter(Boolean);
    let shortlistId = parts[1] || "";
    let focusTab = Number(parts[2] || 0);
    let followLatest = !shortlistId;
    let latestId = "";
    let current = null;
    let renderedKey = "";
    let tabsKey = "";
    let painted = [];
    let selectedVariant = null;

    function headers() {
      const value = { "Accept": "application/json" };
      if (token) value.Authorization = "Bearer " + token;
      return value;
    }

    function pagePath(id, tab) {
      return "/shop/" + id + "/" + (tab || 1) + location.search;
    }

    function showLatestJump() {
      const el = document.getElementById("jump");
      if (!latestId || !shortlistId || latestId === shortlistId) {
        el.hidden = true;
        el.replaceChildren();
        return;
      }
      el.hidden = false;
      el.replaceChildren();
      const link = document.createElement("a");
      link.href = pagePath(latestId, 1);
      link.textContent = "Open latest shortlist (" + latestId + ")";
      link.addEventListener("click", (event) => {
        event.preventDefault();
        followLatest = true;
        shortlistId = latestId;
        focusTab = 1;
        tabsKey = "";
        renderedKey = "";
        loadShortlist();
      });
      el.appendChild(link);
    }

    async function loadShortlist() {
      const latestResponse = await fetch("/api/shop", {
        headers: headers(),
        cache: "no-store",
      });
      if (latestResponse.status === 401) {
        document.getElementById("need").textContent =
          "Open the Telegram link, or add ?token= from .oneagent/local_web.json";
        return;
      }
      let latest = null;
      if (latestResponse.ok) {
        latest = await latestResponse.json();
        if (latest && latest.id) latestId = latest.id;
      }
      if (followLatest && latest && latest.id) {
        if (latest.id !== shortlistId) {
          shortlistId = latest.id;
          focusTab = 1;
          tabsKey = "";
          renderedKey = "";
        }
        current = latest;
        if (!focusTab) focusTab = 1;
        history.replaceState({}, "", pagePath(shortlistId, focusTab));
        renderShortlist();
        return;
      }
      if (!shortlistId) {
        document.getElementById("need").textContent = "No shop shortlist yet. Run a /do product search.";
        showLatestJump();
        return;
      }
      const response = await fetch("/api/shop/" + shortlistId, {
        headers: headers(),
        cache: "no-store",
      });
      if (!response.ok) {
        document.getElementById("need").textContent =
          "No shop shortlist " + shortlistId + ". Use /shop for the latest, or check the tN from that search.";
        showLatestJump();
        return;
      }
      current = await response.json();
      if (!focusTab) focusTab = 1;
      history.replaceState({}, "", pagePath(shortlistId, focusTab));
      renderShortlist();
    }

    function thumbUrl(product) {
      const id = (current && current.id) || shortlistId;
      if (!id || !product) return "";
      const query = token ? ("?token=" + encodeURIComponent(token)) : "";
      return "/api/shop/" + id + "/thumb/" + product.index + query;
    }

    function brandName(product) {
      return (product.brand || product.store || product.name || ("Option " + product.index)).trim();
    }

    function appendInline(node, text) {
      const pattern = /(\*\*([^*]+)\*\*|\[([^\]]+)\]\((https?:[^)\s]+)\)|(https?:\/\/[^\s<]+))/g;
      let last = 0;
      let match;
      while ((match = pattern.exec(text))) {
        if (match.index > last) {
          node.appendChild(document.createTextNode(text.slice(last, match.index)));
        }
        if (match[2]) {
          const strong = document.createElement("strong");
          strong.textContent = match[2];
          node.appendChild(strong);
        } else if (match[3] && match[4]) {
          const link = document.createElement("a");
          link.href = match[4];
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = match[3];
          node.appendChild(link);
        } else if (match[5]) {
          const link = document.createElement("a");
          link.href = match[5];
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = match[5];
          node.appendChild(link);
        }
        last = match.index + match[0].length;
      }
      if (last < text.length) {
        node.appendChild(document.createTextNode(text.slice(last)));
      }
    }

    function appendMarkdown(target, text) {
      let list = null;
      String(text || "").split(/\n/).forEach((line) => {
        const bullet = line.match(/^\s*[-*]\s+(.*)$/);
        if (bullet) {
          if (!list) {
            list = document.createElement("ul");
            target.appendChild(list);
          }
          const item = document.createElement("li");
          appendInline(item, bullet[1]);
          list.appendChild(item);
          return;
        }
        list = null;
        if (!line.trim() || /^<!--.*-->$/.test(line.trim())) return;
        const paragraph = document.createElement("p");
        appendInline(paragraph, line);
        target.appendChild(paragraph);
      });
    }

    function productCardText(product) {
      const brand = brandName(product);
      const lines = ["**" + (product.name || brand) + "**"];
      if (product.price) lines[0] += " — " + product.price;
      if (brand) lines.push("Store: " + brand);
      if (product.variant) lines.push("Variant: " + product.variant);
      if (product.detail) lines.push(product.detail);
      if (product.url) {
        lines.push("[go to " + brand + " product page](" + product.url + ")");
      }
      return lines.join("\n");
    }

    function renderShortlist() {
      const title = current.title || "Shop shortlist";
      document.getElementById("need").textContent = current.id
        ? title + " (" + current.id + ")"
        : title;
      showLatestJump();
      const products = current.products || [];
      const identity = products.map((item) => item.index + ":" + brandName(item) + ":" + item.url).join("|");
      const tabs = document.getElementById("tabs");
      if (identity !== tabsKey) {
        tabsKey = identity;
        tabs.replaceChildren();
        products.forEach((product) => {
          const button = document.createElement("button");
          button.className = "tab";
          button.type = "button";
          button.dataset.index = String(product.index);
          button.textContent = product.name || brandName(product);
          button.setAttribute("role", "tab");
          button.title = product.name || brandName(product);
          button.setAttribute("aria-label", brandName(product));
          button.addEventListener("click", () => {
            focusTab = product.index;
            history.replaceState({}, "", "/shop/" + current.id + "/" + focusTab + location.search);
            renderShortlist();
          });
          tabs.appendChild(button);
        });
      }
      Array.from(tabs.querySelectorAll(".tab")).forEach((button) => {
        button.setAttribute("aria-selected", String(Number(button.dataset.index) === focusTab));
      });
      const product = products.find((item) => item.index === focusTab) || products[0];
      const panel = document.getElementById("product");
      if (!product) {
        renderedKey = "";
        panel.innerHTML = '<p class="empty">No products in this shortlist.</p>';
        return;
      }
      if (!focusTab) focusTab = product.index;
      const key = (current.id || "") + ":" + product.index + ":" + product.url;
      if (key === renderedKey) return;
      renderedKey = key;
      panel.replaceChildren();
      selectedVariant = null;
      const snapshot = product.page;
      const heading = document.createElement("div");
      heading.className = "store-heading";
      const logo = document.createElement("div");
      logo.className = "merchant-logo";
      if (snapshot) logo.innerHTML = 'Underwater<span>audio</span>';
      else logo.textContent = brandName(product);
      const source = document.createElement("a");
      source.className = "source-link";
      source.href = product.url;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = "Original product page ↗";
      heading.append(logo, source);
      panel.append(heading);
      const card = document.createElement("div");
      card.className = "product-message";
      const preview = document.createElement("div");
      preview.className = "preview";
      const img = document.createElement("img");
      img.className = "hero-image";
      img.alt = product.name || brandName(product);
      img.src = thumbUrl(product);
      img.addEventListener("error", () => { img.hidden = true; });
      img.addEventListener("click", () => {
        const dialog = document.getElementById("image-zoom");
        dialog.querySelector("img").src = img.src;
        dialog.showModal();
      });
      preview.appendChild(img);
      const gallery = document.createElement("div");
      gallery.className = "gallery-thumbs";
      function selectImage(name) {
        img.hidden = false;
        img.src = "/assets/syryn/" + name + "?token=" + encodeURIComponent(token);
        gallery.querySelectorAll("button").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.image === name)));
      }
      if (snapshot) {
        snapshot.images.forEach((name, index) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "gallery-thumb";
          button.dataset.image = name;
          button.setAttribute("aria-label", "View product image " + (index + 1));
          const thumb = document.createElement("img");
          thumb.src = "/assets/syryn/" + name + "?token=" + encodeURIComponent(token);
          thumb.alt = "Product view " + (index + 1);
          button.append(thumb);
          button.addEventListener("click", () => selectImage(name));
          gallery.append(button);
        });
        preview.append(gallery);
        const hint = document.createElement("p");
        hint.className = "gallery-hint";
        hint.textContent = "Click the image for a closer look";
        preview.append(hint);
      }
      const copy = document.createElement("div");
      copy.className = "product-copy";
      const eyebrow = document.createElement("p");
      eyebrow.className = "eyebrow";
      eyebrow.textContent = snapshot ? "Waterproof audio · made for swimming" : "From your shortlist";
      const productTitle = document.createElement("h2");
      productTitle.textContent = snapshot ? snapshot.title : product.name;
      const prices = document.createElement("div");
      prices.className = "price-row";
      const price = document.createElement("span");
      price.className = "price";
      price.textContent = (product.price || "See merchant for price").replace(/\*\*/g, "");
      prices.append(price);
      copy.append(eyebrow, productTitle, prices);
      const buy = document.createElement("a");
      buy.className = "merchant-cta";
      buy.href = product.url;
      buy.target = "_blank";
      buy.rel = "noopener noreferrer";
      buy.textContent = "View at merchant ↗";
      const status = document.createElement("p");
      status.className = "availability";
      function updateChatContext() {
        document.getElementById("chat-product").textContent = product.name + (selectedVariant ? " · " + selectedVariant.name : "");
      }
      if (snapshot) {
        const original = document.createElement("del");
        original.className = "original-price";
        const saving = document.createElement("span");
        saving.className = "saving";
        prices.append(original, saving);
        const note = document.createElement("div");
        note.className = "snapshot-note";
        note.textContent = "Merchant snapshot · " + snapshot.checked_at + ". Confirm price and availability at the store.";
        copy.append(note);
        const options = document.createElement("div");
        options.className = "options";
        const label = document.createElement("p");
        label.className = "option-label";
        label.append("Headphones: ");
        const selected = document.createElement("strong");
        label.append(selected);
        const buttons = document.createElement("div");
        buttons.className = "variant-options";
        function choose(variant) {
          selectedVariant = variant;
          selected.textContent = variant.name;
          price.textContent = "$ " + variant.price.toFixed(2) + " USD";
          original.textContent = "$ " + variant.compare_at_price.toFixed(2);
          saving.textContent = "Save $ " + (variant.compare_at_price - variant.price).toFixed(2);
          status.textContent = variant.available ? "Available in the saved merchant snapshot" : "Sold out in the saved merchant snapshot";
          status.style.color = variant.available ? "#377a52" : "#9a6940";
          buy.href = snapshot.url + "?variant=" + variant.id;
          buy.textContent = variant.available ? "View " + variant.name + " at store ↗" : "Check availability at store ↗";
          buttons.querySelectorAll("button").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.id === variant.id)));
          selectImage(variant.image);
          updateChatContext();
        }
        snapshot.variants.forEach(variant => {
          const button = document.createElement("button");
          button.className = "variant";
          button.type = "button";
          button.dataset.id = variant.id;
          button.textContent = variant.name;
          button.addEventListener("click", () => choose(variant));
          buttons.append(button);
        });
        options.append(label, buttons, status);
        copy.append(options);
        choose(snapshot.variants.find(variant => variant.available) || snapshot.variants[0]);
      }
      copy.append(buy);
      const ask = document.createElement("button");
      ask.type = "button";
      ask.className = "ask-product";
      ask.textContent = "Ask OneAgent about this product";
      ask.addEventListener("click", () => {
        document.getElementById("message").focus();
        document.querySelector(".chat-panel").scrollIntoView({behavior: "smooth", block: "nearest"});
      });
      copy.append(ask);
      const details = document.createElement("details");
      details.className = "product-details";
      const summary = document.createElement("summary");
      summary.textContent = "From your product search";
      const detail = document.createElement("p");
      detail.textContent = product.detail || product.variant || "Ask OneAgent for product specifications and a comparison.";
      details.append(summary, detail);
      copy.append(details);
      updateChatContext();
      card.append(preview, copy);
      panel.appendChild(card);
    }

    document.querySelector("#image-zoom button").addEventListener("click", () => document.getElementById("image-zoom").close());
    document.querySelectorAll(".suggestions button").forEach(button => button.addEventListener("click", () => {
      const input = document.getElementById("message");
      input.value = button.dataset.question;
      input.focus();
    }));

    function renderChat(turns) {
      const log = document.getElementById("log");
      log.replaceChildren();
      (turns || []).forEach((turn) => {
        const block = document.createElement("div");
        block.className = "turn";
        if (turn.message) {
          const you = document.createElement("div");
          you.className = "bubble you plain";
          you.textContent = turn.message;
          block.appendChild(you);
        }
        if (turn.reply) {
          const oneagent = document.createElement("div");
          oneagent.className = "bubble oneagent" + (turn.pending ? " pending plain" : "");
          if (turn.pending) oneagent.textContent = turn.reply;
          else appendMarkdown(oneagent, turn.reply);
          block.appendChild(oneagent);
        }
        log.appendChild(block);
      });
      log.scrollTop = 0;
    }

    async function loadChat() {
      const response = await fetch("/api/conversation?ts=" + Date.now(), {
        headers: headers(),
        cache: "no-store",
      });
      if (!response.ok) return;
      const data = await response.json();
      const server = data.turns || [];
      const extras = painted.filter((item) => {
        if (!(item.pending || item.local)) return false;
        if (item.pending) return true;
        return !server.some((turn) => turn.message === item.message && turn.reply === item.reply);
      });
      painted = extras.concat(server);
      renderChat(painted);
    }

    function sleep(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    }

    async function waitForTurn(requestId, pending) {
      const started = Date.now();
      while (Date.now() - started < 180000) {
        await loadChat();
        const response = await fetch("/api/chat/" + requestId, {
          headers: headers(), cache: "no-store",
        });
        const result = await response.json();
        if (!response.ok || result.status === "completed" || result.status === "failed") {
          pending.pending = false;
          pending.reply = result.reply || result.error || "Message processed.";
          renderChat(painted);
          await loadChat();
          return;
        }
        await sleep(500);
      }
      const pendingTurn = pending;
      if (pendingTurn) {
        pendingTurn.pending = false;
        pendingTurn.reply = "Still waiting for OneAgent. If Telegram already has the answer, it should show up here on the next refresh.";
        renderChat(painted);
      }
    }

    document.getElementById("composer").addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = document.getElementById("message");
      const button = event.target.querySelector("button");
      let text = input.value.trim();
      if (!text) return;
      if (selectedVariant && !text.startsWith("/")) {
        text += "\n\nI'm viewing the " + selectedVariant.name + " bundle.";
      }
      const wantsNewSearch = /^\/do\b/i.test(text);
      input.value = "";
      const pending = { message: text, reply: "OneAgent is answering…", pending: true, local: true };
      painted = [pending].concat(painted.filter((item) => !item.pending));
      renderChat(painted);
      if (button) button.disabled = true;
      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { ...headers(), "Content-Type": "application/json" },
          body: JSON.stringify({
            text,
            shortlist_id: (current && current.id) || shortlistId || "",
            tab: focusTab || null,
          }),
        });
        const data = await response.json().catch(() => ({}));
        if (data.reply) {
          pending.pending = false;
          pending.reply = data.reply;
          renderChat(painted);
        } else if (!response.ok) {
          pending.pending = false;
          pending.reply = data.error || "OneAgent could not answer on this page.";
          renderChat(painted);
          return;
        }
        if (data.request_id) await waitForTurn(data.request_id, pending);
        if (wantsNewSearch) {
          followLatest = true;
          tabsKey = "";
          renderedKey = "";
          await loadShortlist();
        }
      } catch (error) {
        pending.pending = false;
        pending.reply = "Could not reach the local shop page.";
        renderChat(painted);
      } finally {
        if (button) button.disabled = false;
      }
    });

    loadShortlist();
    loadChat();
    setInterval(() => { loadShortlist(); loadChat(); }, 4000);
  </script>
</body>
</html>
"""
