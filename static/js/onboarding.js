(() => {
  "use strict";

  const dialog = document.querySelector("[data-onboarding-dialog]");
  const launchers = document.querySelectorAll("[data-guide-launcher]");
  if (!dialog || launchers.length === 0) {
    return;
  }

  const steps = [
    {
      title: "Bienvenue dans C-Tech Archives",
      description: "Votre espace adapte les actions disponibles à votre rôle. Ce guide vous donne les repères essentiels.",
    },
    {
      title: "Retrouvez vos archives",
      description: "Utilisez l’onglet Archives pour consulter et rechercher les documents auxquels vous avez accès.",
    },
    {
      title: "Travaillez selon vos autorisations",
      description: "Les options de création, de mise à jour et d’audit apparaissent uniquement lorsque votre rôle les autorise.",
    },
    {
      title: "Gardez le contrôle",
      description: "Votre profil, les traces d’audit et l’onglet Futures améliorations restent accessibles depuis l’interface.",
    },
  ];
  const storageKey = "c-tech-onboarding-v1-completed";
  const title = dialog.querySelector("[data-guide-title]");
  const description = dialog.querySelector("[data-guide-description]");
  const stepLabel = dialog.querySelector("[data-guide-step-label]");
  const progress = dialog.querySelector("[data-guide-progress]");
  const previous = dialog.querySelector("[data-guide-previous]");
  const next = dialog.querySelector("[data-guide-next]");
  const close = dialog.querySelector("[data-guide-close]");
  let stepIndex = 0;

  const renderStep = () => {
    const step = steps[stepIndex];
    title.textContent = step.title;
    description.textContent = step.description;
    stepLabel.textContent = `Guide d’utilisation · étape ${stepIndex + 1} sur ${steps.length}`;
    progress.style.width = `${((stepIndex + 1) / steps.length) * 100}%`;
    previous.disabled = stepIndex === 0;
    next.textContent = stepIndex === steps.length - 1 ? "Terminer" : "Suivant";
  };

  const complete = () => {
    window.localStorage.setItem(storageKey, "true");
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
  dialog.addEventListener("cancel", () => window.localStorage.setItem(storageKey, "true"));

  if (!window.localStorage.getItem(storageKey)) {
    window.setTimeout(openGuide, 350);
  }
})();
