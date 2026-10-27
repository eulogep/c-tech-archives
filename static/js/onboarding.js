(() => {
  "use strict";

  const dialog = document.querySelector("[data-onboarding-dialog]");
  const launchers = document.querySelectorAll("[data-guide-launcher]");
  if (!dialog || launchers.length === 0) {
    return;
  }

  const steps = [
    {
      icon: "compass",
      title: "Bienvenue dans C-Tech Archives",
      description: "Votre espace adapte les actions disponibles à votre rôle. Ce guide vous donne les repères essentiels en quatre étapes.",
    },
    {
      icon: "archive",
      title: "Retrouvez vos archives",
      description: "L’onglet Archives recherche par référence, titre ou description. Chaque dossier porte un sceau unique dérivé de sa référence pour le reconnaître d’un coup d’œil.",
    },
    {
      icon: "command",
      title: "Allez plus vite",
      description: "Ouvrez la palette de commandes avec Ctrl K (⌘ K sur Mac) pour rechercher une archive ou lancer une action. Appuyez sur ? pour voir tous les raccourcis.",
    },
    {
      icon: "fingerprint",
      title: "Gardez le contrôle",
      description: "Vérifiez l’intégrité SHA-256 d’un fichier depuis sa fiche. Votre habilitation, en bas de la barre latérale, indique les niveaux que vous pouvez consulter.",
    },
  ];
  const storageKey = "c-tech-onboarding-v2-completed";
  const title = dialog.querySelector("[data-guide-title]");
  const description = dialog.querySelector("[data-guide-description]");
  const stepLabel = dialog.querySelector("[data-guide-step-label]");
  const progress = dialog.querySelector("[data-guide-progress]");
  const icon = dialog.querySelector("[data-guide-icon]");
  const previous = dialog.querySelector("[data-guide-previous]");
  const next = dialog.querySelector("[data-guide-next]");
  const close = dialog.querySelector("[data-guide-close]");
  let stepIndex = 0;

  const remember = () => {
    try {
      window.localStorage.setItem(storageKey, "true");
    } catch (error) {
      /* Préférence non mémorisée : le guide pourra réapparaître. */
    }
  };

  const alreadySeen = () => {
    try {
      return Boolean(window.localStorage.getItem(storageKey));
    } catch (error) {
      return true;
    }
  };

  const renderStep = () => {
    const step = steps[stepIndex];
    title.textContent = step.title;
    description.textContent = step.description;
    stepLabel.textContent = `Guide d’utilisation · étape ${stepIndex + 1} sur ${steps.length}`;
    progress.style.width = `${((stepIndex + 1) / steps.length) * 100}%`;
    if (icon) {
      icon.innerHTML = `<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-${step.icon}"></use></svg>`;
    }
    previous.disabled = stepIndex === 0;
    next.textContent = stepIndex === steps.length - 1 ? "Terminer" : "Suivant";
  };

  const complete = () => {
    remember();
    dialog.close();
  };

  const openGuide = () => {
    stepIndex = 0;
    renderStep();
    if (!dialog.open) {
      dialog.showModal();
    }
    next.focus();
  };

  launchers.forEach((launcher) => launcher.addEventListener("click", openGuide));
  previous.addEventListener("click", () => {
    if (stepIndex > 0) {
      stepIndex -= 1;
      renderStep();
    }
  });
  next.addEventListener("click", () => {
    if (stepIndex === steps.length - 1) {
      complete();
      return;
    }
    stepIndex += 1;
    renderStep();
  });
  close.addEventListener("click", complete);
  dialog.addEventListener("cancel", remember);

  // Ouverture automatique une seule fois, depuis le tableau de bord uniquement.
  if (document.querySelector("[data-welcome-hero]") && !alreadySeen()) {
    window.setTimeout(openGuide, 450);
  }
})();
