/* C-Tech Archives — interactions de l’interface (sans dépendance).
 *
 * Tout est amélioration progressive : chaque page fonctionne sans JavaScript.
 * Les autorisations restent décidées par le serveur ; ce script ne fait
 * qu’afficher ce que le serveur a déjà filtré (palette, recherche, aperçus).
 */
(() => {
  "use strict";

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));
  const root = document.documentElement;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

  const storage = {
    get(key) {
      try {
        return window.localStorage.getItem(key);
      } catch (error) {
        return null;
      }
    },
    set(key, value) {
      try {
        if (value === null) {
          window.localStorage.removeItem(key);
        } else {
          window.localStorage.setItem(key, value);
        }
      } catch (error) {
        /* Préférence non mémorisée : sans conséquence. */
      }
    },
  };

  const normalize = (value) =>
    String(value || "")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase();

  const isTyping = (target) =>
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} o`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1).replace(".", ",")} Ko`;
    return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} Mo`;
  };

  const iconMarkup = (name) =>
    `<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-${name}"></use></svg>`;

  /* ------------------------------------------------------------------ */
  /* Sceau génératif — même algorithme que archives/presentation.py.     */
  /* ------------------------------------------------------------------ */
  const SEAL_RINGS = [
    [13, 22, 6],
    [24, 33, 12],
    [35, 43.5, 18],
  ];
  const SEAL_OPACITIES = [0, 0.38, 0.66, 0.95];

  const sealPoint = (radius, angle) => {
    const radians = (angle * Math.PI) / 180;
    return [50 + radius * Math.sin(radians), 50 - radius * Math.cos(radians)];
  };

  const sectorPath = (inner, outer, start, end) => {
    const large = end - start > 180 ? 1 : 0;
    const [x1, y1] = sealPoint(outer, start);
    const [x2, y2] = sealPoint(outer, end);
    const [x3, y3] = sealPoint(inner, end);
    const [x4, y4] = sealPoint(inner, start);
    const f = (value) => value.toFixed(2);
    return `M${f(x1)} ${f(y1)}A${outer} ${outer} 0 ${large} 1 ${f(x2)} ${f(y2)}L${f(x3)} ${f(y3)}A${inner} ${inner} 0 ${large} 0 ${f(x4)} ${f(y4)}Z`;
  };

  const sealSvg = async (reference, size) => {
    if (!window.crypto || !window.crypto.subtle) return "";
    const buffer = await window.crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(String(reference || "").trim())
    );
    const digest = new Uint8Array(buffer);
    const hue = Math.floor((digest[0] * 360) / 256);
    const accent = (hue + 40 + (digest[1] % 100)) % 360;
    const rotation = digest[7] % 30;
    const levels = [];
    for (let index = 2; index < digest.length; index += 1) {
      for (const shift of [6, 4, 2, 0]) levels.push((digest[index] >> shift) & 3);
    }
    let cursor = 0;
    let paths = "";
    SEAL_RINGS.forEach(([inner, outer, count], ringIndex) => {
      const span = 360 / count;
      const half = levels.slice(cursor, cursor + count / 2);
      cursor += count / 2;
      const values = half.concat(half.slice().reverse());
      const ringHue = ringIndex % 2 === 0 ? accent : hue;
      values.forEach((level, index) => {
        if (!level) return;
        const start = rotation + index * span + 2.2;
        const end = rotation + (index + 1) * span - 2.2;
        paths += `<path d="${sectorPath(inner, outer, start, end)}" fill="hsl(${ringHue}, 78%, 66%)" fill-opacity="${SEAL_OPACITIES[level]}"/>`;
      });
    });
    let ticks = "";
    for (let index = 0; index < 48; index += 1) {
      const angle = (index * 360) / 48;
      const [x1, y1] = sealPoint(45.6, angle);
      const [x2, y2] = sealPoint(index % 4 ? 47.6 : 48.6, angle);
      ticks += `M${x1.toFixed(2)} ${y1.toFixed(2)}L${x2.toFixed(2)} ${y2.toFixed(2)}`;
    }
    return (
      `<svg class="seal" viewBox="0 0 100 100" width="${size}" height="${size}" aria-hidden="true" focusable="false">` +
      `<circle cx="50" cy="50" r="49" fill="hsl(${hue}, 42%, 15%)"/>` +
      `<circle cx="50" cy="50" r="44.6" fill="none" stroke="hsl(${hue}, 70%, 70%)" stroke-opacity=".35" stroke-width=".8"/>` +
      `<path d="${ticks}" stroke="hsl(${hue}, 75%, 75%)" stroke-opacity=".55" stroke-width=".9" stroke-linecap="round"/>` +
      paths +
      `<circle cx="50" cy="50" r="9" fill="hsl(${accent}, 85%, 72%)"/>` +
      `<circle cx="50" cy="50" r="4.2" fill="hsl(${hue}, 42%, 15%)"/>` +
      `</svg>`
    );
  };

  /* ------------------------------------------------------------------ */
  /* Touche de modification selon la plateforme.                         */
  /* ------------------------------------------------------------------ */
  if (isMac) {
    $$("[data-mod-key]").forEach((element) => {
      element.textContent = "⌘";
    });
  }

  /* ------------------------------------------------------------------ */
  /* Thème clair / sombre / système.                                     */
  /* ------------------------------------------------------------------ */
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)");
  const effectiveTheme = () => root.dataset.theme || (prefersDark.matches ? "dark" : "light");

  const syncThemeChoices = () => {
    const stored = root.dataset.theme || "auto";
    $$("[data-theme-choice]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.themeChoice === stored));
    });
  };

  const applyTheme = (theme) => {
    if (theme === "light" || theme === "dark") {
      root.dataset.theme = theme;
      storage.set("ctech-theme", theme);
    } else {
      delete root.dataset.theme;
      storage.set("ctech-theme", null);
    }
    syncThemeChoices();
  };

  const toggleTheme = () => applyTheme(effectiveTheme() === "dark" ? "light" : "dark");

  $$("[data-theme-toggle]").forEach((button) => button.addEventListener("click", toggleTheme));
  $$("[data-theme-choice]").forEach((button) =>
    button.addEventListener("click", () => applyTheme(button.dataset.themeChoice))
  );
  syncThemeChoices();

  /* ------------------------------------------------------------------ */
  /* Barre latérale : réduction (bureau) et tiroir (mobile).             */
  /* ------------------------------------------------------------------ */
  const setNavOpen = (open) => {
    document.body.classList.toggle("is-nav-open", open);
    $$("[data-nav-open]").forEach((button) => button.setAttribute("aria-expanded", String(open)));
  };

  $$("[data-sidebar-toggle]").forEach((button) =>
    button.addEventListener("click", () => {
      const collapsed = root.dataset.sidebar !== "collapsed";
      if (collapsed) {
        root.dataset.sidebar = "collapsed";
      } else {
        delete root.dataset.sidebar;
      }
      storage.set("ctech-sidebar", collapsed ? "collapsed" : null);
    })
  );
  $$("[data-nav-open]").forEach((button) => button.addEventListener("click", () => setNavOpen(true)));
  $$("[data-nav-close]").forEach((element) => element.addEventListener("click", () => setNavOpen(false)));
  $$(".sidebar .nav-link").forEach((link) => link.addEventListener("click", () => setNavOpen(false)));

  /* ------------------------------------------------------------------ */
  /* Menu utilisateur : fermeture au clic extérieur et à Échap.          */
  /* ------------------------------------------------------------------ */
  const userMenu = $("[data-user-menu]");
  if (userMenu) {
    document.addEventListener("click", (event) => {
      if (userMenu.open && !userMenu.contains(event.target)) userMenu.open = false;
    });
  }

  /* ------------------------------------------------------------------ */
  /* Notifications.                                                       */
  /* ------------------------------------------------------------------ */
  const dismissToast = (toast) => {
    if (!toast || toast.classList.contains("is-leaving")) return;
    toast.classList.add("is-leaving");
    window.setTimeout(() => toast.remove(), reducedMotion ? 0 : 300);
  };

  $$(".toast-stack .message").forEach((toast) => {
    $("[data-toast-close]", toast)?.addEventListener("click", () => dismissToast(toast));
    if (toast.classList.contains("error")) return;
    let timer = window.setTimeout(() => dismissToast(toast), 7000);
    toast.addEventListener("mouseenter", () => window.clearTimeout(timer));
    toast.addEventListener("mouseleave", () => {
      timer = window.setTimeout(() => dismissToast(toast), 2500);
    });
  });

  /* ------------------------------------------------------------------ */
  /* Compteurs animés.                                                    */
  /* ------------------------------------------------------------------ */
  const counters = $$("[data-count]");
  if (counters.length && !reducedMotion && "IntersectionObserver" in window) {
    const animate = (element) => {
      const target = Number.parseInt(element.dataset.count, 10);
      if (!Number.isFinite(target) || target <= 0) return;
      const duration = Math.min(1400, 500 + target * 12);
      const start = performance.now();
      const step = (now) => {
        const progress = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - progress, 4);
        element.textContent = Math.round(target * eased).toLocaleString("fr-FR");
        if (progress < 1) window.requestAnimationFrame(step);
      };
      window.requestAnimationFrame(step);
    };
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animate(entry.target);
          observer.unobserve(entry.target);
        }
      });
    });
    counters.forEach((counter) => observer.observe(counter));
  }

  /* ------------------------------------------------------------------ */
  /* Dialogues génériques.                                                */
  /* ------------------------------------------------------------------ */
  $$("dialog").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  });
  $$("[data-dialog-close]").forEach((button) =>
    button.addEventListener("click", () => button.closest("dialog")?.close())
  );

  const shortcutsDialog = $("[data-shortcuts]");
  const openShortcuts = () => {
    if (shortcutsDialog && !shortcutsDialog.open) shortcutsDialog.showModal();
  };
  $$("[data-shortcuts-open]").forEach((button) =>
    button.addEventListener("click", () => {
      if (userMenu) userMenu.open = false;
      openShortcuts();
    })
  );

  /* ------------------------------------------------------------------ */
  /* Palette de commandes.                                                */
  /* ------------------------------------------------------------------ */
  const palette = $("[data-palette]");
  const paletteInput = $("[data-palette-input]");
  const paletteResults = $("[data-palette-results]");
  const commandData = $("#command-items");
  const searchUrl = document.body.dataset.searchUrl;
  const commands = commandData ? JSON.parse(commandData.textContent) : [];
  let paletteItems = [];
  let activeIndex = 0;
  let searchController = null;
  let searchTimer = null;
  let archiveResults = [];
  let archiveQuery = "";

  const runAction = (action) => {
    palette?.close();
    if (action === "toggle-theme") toggleTheme();
    if (action === "open-guide") $("[data-guide-launcher]")?.click();
    if (action === "open-shortcuts") openShortcuts();
    if (action === "logout") $("form.logout-form")?.requestSubmit();
  };

  const highlight = (container, text, query) => {
    const tokens = normalize(query).split(/\s+/).filter(Boolean);
    const plain = normalize(text);
    let matchStart = -1;
    let matchLength = 0;
    for (const token of tokens) {
      const index = plain.indexOf(token);
      if (index >= 0) {
        matchStart = index;
        matchLength = token.length;
        break;
      }
    }
    if (matchStart < 0) {
      container.append(document.createTextNode(text));
      return;
    }
    const mark = document.createElement("mark");
    mark.textContent = text.slice(matchStart, matchStart + matchLength);
    container.append(
      document.createTextNode(text.slice(0, matchStart)),
      mark,
      document.createTextNode(text.slice(matchStart + matchLength))
    );
  };

  const setActive = (index) => {
    if (!paletteItems.length) return;
    activeIndex = (index + paletteItems.length) % paletteItems.length;
    paletteItems.forEach((item, itemIndex) => {
      const selected = itemIndex === activeIndex;
      item.element.setAttribute("aria-selected", String(selected));
      if (selected) {
        item.element.scrollIntoView({ block: "nearest" });
        paletteInput?.setAttribute("aria-activedescendant", item.element.id);
      }
    });
  };

  const buildItem = ({ label, sub, icon, shortcut }, query, index) => {
    const element = document.createElement("div");
    element.className = "palette-item";
    element.id = `palette-item-${index}`;
    element.setAttribute("role", "option");
    element.setAttribute("aria-selected", "false");
    const glyph = document.createElement("span");
    glyph.className = icon === "seal" ? "palette-seal" : "";
    glyph.innerHTML = icon === "seal" ? "" : iconMarkup(icon || "dot");
    const text = document.createElement("span");
    text.className = "palette-item-text";
    const title = document.createElement("span");
    highlight(title, label, query);
    text.append(title);
    if (sub) {
      const small = document.createElement("small");
      small.textContent = sub;
      text.append(small);
    }
    element.append(glyph, text);
    if (shortcut) {
      const keys = document.createElement("span");
      shortcut.split(" ").forEach((key) => {
        const kbd = document.createElement("kbd");
        kbd.textContent = key;
        keys.append(kbd);
      });
      element.append(keys);
    }
    return { element, glyph };
  };

  const renderPalette = () => {
    if (!paletteResults) return;
    const query = paletteInput ? paletteInput.value.trim() : "";
    const tokens = normalize(query).split(/\s+/).filter(Boolean);
    const matches = commands.filter((command) => {
      const haystack = normalize(`${command.label} ${command.keywords} ${command.group}`);
      return tokens.every((token) => haystack.includes(token));
    });

    paletteResults.replaceChildren();
    paletteItems = [];
    const groups = new Map();

    if (query.length >= 2 && archiveQuery === query && archiveResults.length) {
      groups.set(
        "Archives",
        archiveResults.map((archive) => ({
          label: `${archive.reference} — ${archive.title}`,
          sub: `${archive.level_label} · ${archive.status_label}`,
          icon: "seal",
          seal: archive.reference,
          url: archive.url,
        }))
      );
    }
    matches.forEach((command) => {
      if (!groups.has(command.group)) groups.set(command.group, []);
      groups.get(command.group).push({ ...command, sub: command.url ? "" : "Action" });
    });

    groups.forEach((items, groupName) => {
      const heading = document.createElement("div");
      heading.className = "palette-group";
      heading.setAttribute("role", "presentation");
      heading.textContent = groupName;
      paletteResults.append(heading);
      items.forEach((item) => {
        const { element, glyph } = buildItem(item, query, paletteItems.length);
        if (item.seal) {
          sealSvg(item.seal, 26).then((markup) => {
            glyph.innerHTML = markup || iconMarkup("archive");
          });
        }
        const entry = { element, item };
        element.addEventListener("click", () => execute(entry));
        element.addEventListener("mousemove", () => setActive(paletteItems.indexOf(entry)));
        paletteItems.push(entry);
        paletteResults.append(element);
      });
    });

    if (!paletteItems.length) {
      const empty = document.createElement("p");
      empty.className = "palette-empty";
      empty.textContent =
        query.length >= 2 && searchUrl ? "Aucun résultat dans votre périmètre." : "Aucune commande correspondante.";
      paletteResults.append(empty);
    }
    setActive(0);
  };

  const execute = (entry) => {
    if (!entry) return;
    const { item } = entry;
    if (item.url) {
      palette?.close();
      window.location.assign(item.url);
    } else if (item.action) {
      runAction(item.action);
    }
  };

  const searchArchives = () => {
    if (!searchUrl || !paletteInput) return;
    const query = paletteInput.value.trim();
    window.clearTimeout(searchTimer);
    if (query.length < 2) {
      archiveResults = [];
      archiveQuery = "";
      return;
    }
    searchTimer = window.setTimeout(async () => {
      searchController?.abort();
      searchController = new AbortController();
      try {
        const response = await fetch(`${searchUrl}?q=${encodeURIComponent(query)}`, {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
          signal: searchController.signal,
        });
        if (!response.ok) return;
        const payload = await response.json();
        archiveResults = Array.isArray(payload.results) ? payload.results : [];
        archiveQuery = payload.query;
        if (paletteInput.value.trim() === query) renderPalette();
      } catch (error) {
        /* Requête annulée ou réseau indisponible : la palette reste utilisable. */
      }
    }, 160);
  };

  const openPalette = () => {
    if (!palette) return;
    if (userMenu) userMenu.open = false;
    if (!palette.open) palette.showModal();
    if (paletteInput) {
      paletteInput.value = "";
      paletteInput.focus();
    }
    archiveResults = [];
    renderPalette();
  };

  $$("[data-palette-open]").forEach((button) => button.addEventListener("click", openPalette));
  paletteInput?.addEventListener("input", () => {
    renderPalette();
    searchArchives();
  });
  paletteInput?.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive(activeIndex + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive(activeIndex - 1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      execute(paletteItems[activeIndex]);
    }
  });

  /* ------------------------------------------------------------------ */
  /* Raccourcis clavier globaux.                                          */
  /* ------------------------------------------------------------------ */
  const goTargets = {
    d: commands.find((command) => command.shortcut === "G D")?.url,
    a: commands.find((command) => command.shortcut === "G A")?.url,
    j: commands.find((command) => command.shortcut === "G J")?.url,
    p: commands.find((command) => command.shortcut === "G P")?.url,
    r: commands.find((command) => command.shortcut === "G R")?.url,
    v: commands.find((command) => command.shortcut === "G V")?.url,
  };
  let awaitingGo = false;
  let goTimer = null;

  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      if (!palette) return;
      event.preventDefault();
      if (palette.open) {
        palette.close();
      } else {
        openPalette();
      }
      return;
    }
    if (event.key === "Escape") {
      setNavOpen(false);
      if (userMenu) userMenu.open = false;
      return;
    }
    if (!palette || event.metaKey || event.ctrlKey || event.altKey || isTyping(event.target)) return;
    if ($("dialog[open]")) return;

    const key = event.key.toLowerCase();
    if (awaitingGo) {
      awaitingGo = false;
      window.clearTimeout(goTimer);
      if (goTargets[key]) {
        event.preventDefault();
        window.location.assign(goTargets[key]);
      }
      return;
    }
    if (key === "g") {
      awaitingGo = true;
      goTimer = window.setTimeout(() => {
        awaitingGo = false;
      }, 900);
    } else if (event.key === "/") {
      event.preventDefault();
      const pageSearch = $("[data-page-search]");
      if (pageSearch) {
        pageSearch.focus();
        pageSearch.select();
      } else {
        openPalette();
      }
    } else if (key === "n" && document.body.dataset.createUrl) {
      event.preventDefault();
      window.location.assign(document.body.dataset.createUrl);
    } else if (key === "t") {
      toggleTheme();
    } else if (event.key === "?") {
      event.preventDefault();
      openShortcuts();
    }
  });

  /* ------------------------------------------------------------------ */
  /* Formulaires : sélecteurs auto-soumis, URL de recherche épurées.     */
  /* ------------------------------------------------------------------ */
  $$("[data-auto-submit]").forEach((select) =>
    select.addEventListener("change", () => select.form?.requestSubmit())
  );
  $$("[data-filter-form]").forEach((form) =>
    form.addEventListener("submit", () => {
      $$("input, select", form).forEach((field) => {
        if (field.name && !field.value) field.disabled = true;
      });
    })
  );

  /* Mot de passe : affichage et robustesse indicative. */
  $$("[data-password-toggle]").forEach((button) => {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) return;
    button.addEventListener("click", () => {
      const visible = input.type === "password";
      input.type = visible ? "text" : "password";
      button.setAttribute("aria-pressed", String(visible));
      button.setAttribute("aria-label", visible ? "Masquer le mot de passe" : "Afficher le mot de passe");
      input.focus();
    });
  });

  const STRENGTH_LABELS = [
    "Au moins 8 caractères, ni trop courant, ni uniquement numérique.",
    "Fragile : allongez-le et variez les caractères.",
    "Moyen : ajoutez de la longueur ou des symboles.",
    "Solide.",
    "Excellent : long et varié.",
  ];
  $$("[data-strength-for]").forEach((meter) => {
    const input = document.getElementById(meter.dataset.strengthFor);
    const label = $("[data-strength-label]", meter);
    if (!input) return;
    input.addEventListener("input", () => {
      const value = input.value;
      let score = 0;
      if (value.length >= 8) score += 1;
      if (value.length >= 12) score += 1;
      const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((pattern) => pattern.test(value)).length;
      if (classes >= 3) score += 1;
      if (value.length >= 16 && classes >= 2) score += 1;
      if (/^\d+$/.test(value) || /^(.)\1+$/.test(value) || /(password|motdepasse|azerty|qwerty|123456)/i.test(value)) {
        score = Math.min(score, 1);
      }
      score = value ? Math.max(1, Math.min(4, score)) : 0;
      meter.dataset.score = String(score);
      if (label) label.textContent = STRENGTH_LABELS[score];
    });
  });

  /* Zones de dépôt : retour visuel et contrôle anticipé (le serveur décide). */
  $$("[data-dropzone]").forEach((zone) => {
    const input = $("input[type=file]", zone);
    const info = $("[data-dropzone-file]", zone);
    if (!input || !info) return;
    const maxSize = Number.parseInt(zone.dataset.maxSize || "0", 10);
    const allowed = (zone.dataset.allowed || "")
      .split(",")
      .map((extension) => extension.trim().toLowerCase())
      .filter(Boolean);

    const describe = () => {
      const file = input.files && input.files[0];
      zone.classList.toggle("has-file", Boolean(file));
      zone.classList.remove("has-error");
      info.classList.remove("is-invalid");
      if (!file) {
        info.replaceChildren();
        return;
      }
      const extension = `.${file.name.split(".").pop().toLowerCase()}`;
      let problem = "";
      if (allowed.length && !allowed.includes(extension)) problem = "Format non autorisé";
      else if (maxSize && file.size > maxSize) problem = `Dépasse ${formatSize(maxSize)}`;
      else if (file.size === 0) problem = "Fichier vide";
      info.innerHTML = iconMarkup(problem ? "alert" : "file");
      const name = document.createElement("span");
      name.textContent = `${file.name} · ${formatSize(file.size)}${problem ? ` — ${problem}` : ""}`;
      info.append(name);
      if (problem) {
        zone.classList.add("has-error");
        info.classList.add("is-invalid");
      }
    };

    ["dragenter", "dragover"].forEach((type) =>
      zone.addEventListener(type, () => zone.classList.add("is-dragging"))
    );
    ["dragleave", "drop"].forEach((type) =>
      zone.addEventListener(type, () => zone.classList.remove("is-dragging"))
    );
    input.addEventListener("change", describe);
  });

  /* Aperçu du sceau pendant la saisie de la référence. */
  const sealSource = $("[data-seal-source]");
  const sealPreview = $("[data-seal-preview]");
  if (sealSource && sealPreview) {
    const target = $("[data-seal-target]", sealPreview);
    const label = $("[data-seal-label]", sealPreview);
    let sealTimer = null;
    sealSource.addEventListener("input", () => {
      window.clearTimeout(sealTimer);
      sealPreview.classList.add("is-updating");
      sealTimer = window.setTimeout(async () => {
        const reference = sealSource.value.trim();
        const markup = await sealSvg(reference || "C-Tech", 112);
        if (markup && target) target.innerHTML = markup;
        if (label) label.textContent = reference || "Référence à saisir";
        sealPreview.classList.remove("is-updating");
      }, 180);
    });
  }

  /* Calendrier de conservation : durées usuelles depuis la date du document. */
  const retentionTarget = $("[data-retention-target]");
  $$("[data-retention-years]").forEach((button) =>
    button.addEventListener("click", () => {
      if (!retentionTarget) return;
      const source = $("#id_document_date");
      const base = source && source.value ? new Date(`${source.value}T12:00:00`) : new Date();
      base.setFullYear(base.getFullYear() + Number.parseInt(button.dataset.retentionYears, 10));
      retentionTarget.value = base.toISOString().slice(0, 10);
      retentionTarget.dispatchEvent(new Event("input", { bubbles: true }));
      retentionTarget.focus();
    })
  );

  /* Étapes du formulaire d’archive : section courante. */
  const stepLinks = $$("[data-step-link]");
  if (stepLinks.length && "IntersectionObserver" in window) {
    const sections = stepLinks.map((link) => document.querySelector(link.getAttribute("href"))).filter(Boolean);
    const stepObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          stepLinks.forEach((link) =>
            link.classList.toggle("is-current", link.getAttribute("href") === `#${entry.target.id}`)
          );
        });
      },
      { rootMargin: "-40% 0px -55% 0px" }
    );
    sections.forEach((section) => stepObserver.observe(section));
  }

  /* ------------------------------------------------------------------ */
  /* Fiche d’archive : copie, impression, aperçu à la demande.           */
  /* ------------------------------------------------------------------ */
  $$("[data-copy]").forEach((button) =>
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        button.classList.add("is-copied");
        button.innerHTML = iconMarkup("check");
        window.setTimeout(() => {
          button.classList.remove("is-copied");
          button.innerHTML = iconMarkup("copy");
        }, 1600);
      } catch (error) {
        /* Presse-papiers refusé : rien à faire. */
      }
    })
  );

  $$("[data-print]").forEach((button) => button.addEventListener("click", () => window.print()));

  $$("[data-preview-url]").forEach((button) => {
    const panel = $("[data-preview-panel]");
    const frame = $("[data-preview-frame]");
    if (!panel || !frame) return;
    let loaded = false;
    button.addEventListener("click", async () => {
      const opening = panel.hidden;
      panel.hidden = !opening;
      button.setAttribute("aria-expanded", String(opening));
      if (!opening || loaded) return;
      loaded = true;
      frame.replaceChildren();
      if (button.dataset.previewKind === "image") {
        const image = document.createElement("img");
        image.alt = button.dataset.previewAlt || "Aperçu";
        image.decoding = "async";
        image.src = button.dataset.previewUrl;
        frame.append(image);
        return;
      }
      try {
        const response = await fetch(button.dataset.previewUrl, { credentials: "same-origin" });
        if (!response.ok) throw new Error(String(response.status));
        const pre = document.createElement("pre");
        pre.textContent = await response.text();
        if (response.headers.get("X-Preview-Truncated") === "true") {
          pre.textContent += "\n\n[…] Aperçu limité aux 64 premiers Ko.";
        }
        frame.append(pre);
      } catch (error) {
        loaded = false;
        const message = document.createElement("p");
        message.className = "upload-hint";
        message.textContent = "L’aperçu n’a pas pu être chargé.";
        frame.append(message);
      }
    });
  });
})();
