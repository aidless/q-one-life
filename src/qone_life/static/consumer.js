'use strict';

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHTML = (value) =>
  String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[character]);
const e = escapeHTML;

const state = {
  data: null,
  messages: null,
  locale: 'zh-CN',
  localeChoice: null,
  route: 'today',
  onboardingStep: 0,
  showGoalForm: false,
  editingGoalId: null,
  showTaskForm: false,
  backup: null,
  backupDraft: null,
  model: null,
  update: null,
  busy: false,
  plannerSignature: '',
};

const ROUTES = new Set(['today', 'goals', 'review', 'settings']);
let toastTimer;
let plannerTimer;
let plannerPollInFlight = false;

function activeRoute() {
  const route = location.hash.slice(1);
  return ROUTES.has(route) ? route : 'today';
}

class ApiError extends Error {
  constructor(code, requestId, retryable) {
    super(code);
    this.name = 'ApiError';
    this.code = code;
    this.requestId = requestId;
    this.retryable = retryable;
  }
}

function interpolate(template, values) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) =>
    values[key] === undefined ? `{${key}}` : String(values[key]),
  );
}

function t(key, values = {}) {
  const template =
    state.messages?.[state.locale]?.[key] ??
    state.messages?.['zh-CN']?.[key] ??
    key;
  return interpolate(template, values);
}

function recoveryQrMarkup(draft) {
  const svg = draft?.recoveryKeyQr;
  if (
    typeof svg !== 'string' ||
    !/^<svg\b[\s\S]*<\/svg>$/.test(svg) ||
    /<(?:script|foreignObject|image|use)\b|\son\w+\s*=|(?:href|xlink:href)\s*=/i.test(svg)
  ) {
    return '';
  }
  return `<figure class="recovery-qr" role="img" aria-label="${e(t('backup.qrAria'))}">
    ${svg}
    <figcaption>${e(t('backup.scanQr'))}</figcaption>
  </figure>`;
}

function browserLocale() {
  return String(navigator.language || '').toLowerCase().startsWith('en')
    ? 'en-US'
    : 'zh-CN';
}

async function loadMessages() {
  const [zh, en] = await Promise.all([
    fetch('/static/zh-CN.json', { headers: { Accept: 'application/json' } }).then((r) => {
      if (!r.ok) throw new Error('locale load failed');
      return r.json();
    }),
    fetch('/static/en-US.json', { headers: { Accept: 'application/json' } }).then((r) => {
      if (!r.ok) throw new Error('locale load failed');
      return r.json();
    }),
  ]);
  state.messages = { 'zh-CN': zh, 'en-US': en };
}

async function pollPlanner() {
  if (plannerPollInFlight) return 1_000;
  if (document.hidden || !state.data || !state.data.settings.onboarding_complete) {
    return 15_000;
  }
  plannerPollInFlight = true;
  try {
    const previous = state.plannerSignature;
    const planner = await api('planner');
    const next = JSON.stringify(planner);
    if (next !== previous) {
      state.data.planner = planner;
      state.plannerSignature = next;
      if (state.route === 'today' && !$('#consumer-dialog').open) renderTodayOnly();
    }
    return ['pending', 'running'].includes(planner.status) ? 1_000 : 15_000;
  } catch {
    // Polling is best-effort; explicit actions still surface actionable errors.
    return 5_000;
  } finally {
    plannerPollInFlight = false;
  }
}

function schedulePlannerPoll(delay = 1_000) {
  clearTimeout(plannerTimer);
  plannerTimer = setTimeout(async () => {
    const nextDelay = await pollPlanner();
    schedulePlannerPoll(nextDelay);
  }, delay);
}

function setLocale(locale, focus = false) {
  state.locale = locale === 'en-US' ? 'en-US' : 'zh-CN';
  state.localeChoice = state.locale;
  document.documentElement.lang = state.locale;
  document.title = `Q-One · ${t('brand.documentTitle')}`;
  $$('[data-i18n]').forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  $$('[data-i18n-placeholder]').forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  const nav = $('.primary-nav');
  if (nav) nav.setAttribute('aria-label', t('nav.aria'));
  const skip = $('.skip-link');
  if (skip) skip.textContent = t('common.skip');
  if (focus) $('#main')?.focus();
}

async function api(path, options = {}) {
  const response = await fetch(`/api/${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-QOne-Client': 'web',
      ...(options.headers || {}),
    },
  });
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError('SERVICE_UNAVAILABLE', '', true);
  }
  if (!response.ok) {
    throw new ApiError(
      payload?.error?.code || 'REQUEST_FAILED',
      payload?.error?.request_id || '',
      Boolean(payload?.error?.retryable),
    );
  }
  return payload;
}

const post = (path, body) =>
  api(path, { method: 'POST', body: JSON.stringify(body) });

function messageFor(error) {
  if (error instanceof ApiError) {
    const localized = t(`error.${error.code}`);
    const base =
      localized === `error.${error.code}` ? t('error.REQUEST_FAILED') : localized;
    return error.requestId
      ? `${base} (${t('common.requestId', { id: error.requestId.slice(0, 8) })})`
      : base;
  }
  return error instanceof Error && error.message
    ? error.message
    : t('error.REQUEST_FAILED');
}

function toast(message, error = false) {
  const node = $('#toast');
  node.textContent = message;
  node.classList.toggle('error', error);
  node.classList.add('visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove('visible'), error ? 7000 : 3600);
}

function formatDate(value, options = {}) {
  if (!value) return t('common.notSet');
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return t('common.notSet');
  return new Intl.DateTimeFormat(state.locale, {
    month: 'short',
    day: 'numeric',
    ...options,
  }).format(date);
}

function todayLabel() {
  return new Intl.DateTimeFormat(state.locale, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  }).format(new Date());
}

function domainLabel(domain) {
  return t(`domain.${domain}`);
}

function plannerStatusLabel(status) {
  return t(`planner.${status}`);
}

function goalStatusLabel(status) {
  return t(`goalStatus.${status}`);
}

function sourceLabel(source) {
  if (!source) return t('source.rules');
  if (source === 'rules') return t('source.rules');
  if (source === 'adaptive') return t('source.adaptive');
  if (source === 'scenario') return t('source.scenario');
  if (source.startsWith('laya')) return t('source.laya');
  return t('source.model');
}

function activeGoals() {
  return state.data?.goals.filter((goal) => goal.status === 'active') ?? [];
}

function todaysTasks() {
  const today = state.data?.planner?.date;
  return state.data?.tasks.filter(
    (task) => task.focus_date === today || (!task.done && !task.focus_date),
  ) ?? [];
}

function completedToday() {
  const today = state.data?.planner?.date;
  return state.data?.tasks.filter(
    (task) => task.done && (task.completed_at?.startsWith(today) || task.focus_date === today),
  ) ?? [];
}

function renderLoading() {
  $('#main').innerHTML = `
    <section class="loading-card" aria-live="polite">
      <span class="orbit" aria-hidden="true"></span>
      <p>${e(t('common.loading'))}</p>
    </section>`;
}

function renderFailure(message) {
  $('#main').innerHTML = `
    <section class="failure-card">
      <span class="eyebrow">${e(t('error.title'))}</span>
      <h1>${e(t('error.openFailed'))}</h1>
      <p>${e(message)}</p>
      <button class="button primary" type="button" data-action="reload-app">${e(t('common.tryAgain'))}</button>
    </section>`;
}

function render() {
  if (!state.data) return;
  setLocale(state.locale);
  $('#app-version').textContent = `v${state.data.version}`;
  document.body.classList.toggle('onboarding-mode', !state.data.settings.onboarding_complete);
  if (!state.data.settings.onboarding_complete) {
    renderOnboarding();
    return;
  }
  const route = ROUTES.has(location.hash.slice(1)) ? location.hash.slice(1) : 'today';
  state.route = route;
  $$('.primary-nav [data-route]').forEach((button) => {
    const selected = button.dataset.route === route;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-current', selected ? 'page' : 'false');
  });
  const pages = {
    today: renderToday,
    goals: renderGoals,
    review: renderReview,
    settings: renderSettings,
  };
  $('#main').innerHTML = pages[route]();
  if (route === 'settings') {
    if (!state.backup) loadBackupStatus();
    else renderBackupIntoPage();
    if (!state.model) loadModelStatus();
    else renderModelIntoPage();
    if (window.qoneDesktop?.updateStatus) {
      if (!state.update) loadUpdateStatus();
      else renderUpdateIntoPage();
    }
  }
}

function renderOnboarding() {
  const steps = [
    t('onboarding.stepLanguage'),
    t('onboarding.stepGoal'),
    t('onboarding.stepBackup'),
    t('onboarding.stepModel'),
  ];
  const progress = steps
    .map(
      (label, index) => `
        <li class="${index === state.onboardingStep ? 'active' : ''} ${index < state.onboardingStep ? 'done' : ''}">
          <span>${String(index + 1).padStart(2, '0')}</span>${e(label)}
        </li>`,
    )
    .join('');
  let body = '';
  if (state.onboardingStep === 0) body = onboardingLanguage();
  if (state.onboardingStep === 1) body = onboardingGoal();
  if (state.onboardingStep === 2) body = onboardingBackup();
  if (state.onboardingStep === 3) body = onboardingModel();
  $('#main').innerHTML = `
    <section class="onboarding">
      <aside class="onboarding-aside">
        <span class="eyebrow">${e(t('onboarding.kicker'))}</span>
        <h1>${e(t('onboarding.title'))}</h1>
        <p>${e(t('onboarding.intro'))}</p>
        <ol class="step-list">${progress}</ol>
        <p class="privacy-note">${e(t('onboarding.privacy'))}</p>
      </aside>
      <div class="onboarding-card" aria-live="polite">${body}</div>
    </section>`;
}

function onboardingLanguage() {
  const choices = [
    ['zh-CN', '简体中文', '中文界面与建议'],
    ['en-US', 'English', 'English interface and suggestions'],
  ];
  return `
    <span class="step-count">01 / 04</span>
    <h2>${e(t('onboarding.languageTitle'))}</h2>
    <p class="lede">${e(t('onboarding.languageBody'))}</p>
    <div class="language-choices" role="radiogroup" aria-label="${e(t('onboarding.languageTitle'))}">
      ${choices
        .map(
          ([value, label, detail]) => `
          <button type="button" role="radio" aria-checked="${state.localeChoice === value}"
            class="language-choice ${state.localeChoice === value ? 'selected' : ''}"
            data-action="onboarding-language" data-locale="${value}">
            <strong>${label}</strong><small>${detail}</small>
          </button>`,
        )
        .join('')}
    </div>
    <div class="step-actions">
      <span></span>
      <button class="button primary" type="button" data-action="onboarding-language-next">
        ${e(t('common.continue'))} <span aria-hidden="true">→</span>
      </button>
    </div>`;
}

function onboardingGoal() {
  return `
    <span class="step-count">02 / 04</span>
    <h2>${e(t('onboarding.goalTitle'))}</h2>
    <p class="lede">${e(t('onboarding.goalBody'))}</p>
    <form id="onboarding-goal-form" class="form-stack">
      <label>${e(t('goal.titleLabel'))}
        <input name="title" required maxlength="150" autofocus
          placeholder="${e(t('onboarding.goalPlaceholder'))}">
      </label>
      <label>${e(t('goal.criterionLabel'))}
        <textarea name="success_criterion" rows="3" required maxlength="1000"
          placeholder="${e(t('onboarding.criterionPlaceholder'))}"></textarea>
      </label>
      <label>${e(t('goal.domainLabel'))}
        <select name="domain">
          ${['work', 'learning', 'energy', 'recovery', 'other']
            .map((domain) => `<option value="${domain}">${e(domainLabel(domain))}</option>`)
            .join('')}
        </select>
      </label>
      <div class="step-actions">
        <button class="text-button" type="button" data-action="onboarding-skip-goal">${e(t('common.skipAction'))}</button>
        <button class="button primary" type="submit">${e(t('common.continue'))} <span aria-hidden="true">→</span></button>
      </div>
    </form>`;
}

function onboardingBackup() {
  if (!window.qoneDesktop) {
    return `
      <span class="step-count">03 / 04</span>
      <h2>${e(t('onboarding.backupTitle'))}</h2>
      <p class="lede">${e(t('onboarding.browserBackup'))}</p>
      <div class="callout">${e(t('onboarding.desktopOnly'))}</div>
      <div class="step-actions">
        <button class="text-button" type="button" data-action="onboarding-next-model">${e(t('common.skipAction'))}</button>
        <button class="button primary" type="button" data-action="onboarding-next-model">${e(t('common.continue'))} <span aria-hidden="true">→</span></button>
      </div>`;
  }
  const backup = state.backup;
  if (!backup) {
    void loadBackupStatus();
    return `
      <span class="step-count">03 / 04</span>
      <h2>${e(t('onboarding.backupTitle'))}</h2>
      <p class="lede">${e(t('onboarding.backupBody'))}</p>
      <div class="loading-line">${e(t('common.loading'))}</div>`;
  }
  if (!backup.persistent) {
    return `
      <span class="step-count">03 / 04</span>
      <h2>${e(t('onboarding.backupTitle'))}</h2>
      <div class="callout warning">${e(t('backup.sessionOnly'))}</div>
      <p class="lede">${e(t('backup.manualOnly'))}</p>
      <div class="step-actions">
        <button class="text-button" type="button" data-action="onboarding-next-model">${e(t('common.skipAction'))}</button>
        <button class="button" type="button" data-action="backup-now">${e(t('backup.createNow'))}</button>
        <button class="button primary" type="button" data-action="onboarding-next-model">${e(t('common.continue'))} <span aria-hidden="true">→</span></button>
      </div>`;
  }
  if (state.backupDraft) {
    return `
      <span class="step-count">03 / 04</span>
      <h2>${e(t('backup.saveKeyTitle'))}</h2>
      <p class="lede">${e(t('backup.saveKeyBody'))}</p>
      <label>${e(t('backup.recoveryKey'))}
        <textarea id="backup-recovery-key" readonly rows="4">${e(state.backupDraft.recoveryKey)}</textarea>
      </label>
      ${recoveryQrMarkup(state.backupDraft)}
      <label class="check-row">
        <input id="backup-key-confirmed" type="checkbox">
        <span>${e(t('backup.confirmSaved'))}</span>
      </label>
      <div class="step-actions">
        <button class="text-button" type="button" data-action="backup-copy-key">${e(t('backup.copyKey'))}</button>
        <button class="button primary" type="button" data-action="onboarding-enable-backup">${e(t('backup.enableAuto'))}</button>
      </div>`;
  }
  const configured = backup.directory && backup.recovery_key_confirmed;
  return `
    <span class="step-count">03 / 04</span>
    <h2>${e(t('onboarding.backupTitle'))}</h2>
    <p class="lede">${e(t('onboarding.backupBody'))}</p>
    ${configured
      ? `<div class="summary-line"><span>${e(t('backup.location'))}</span><strong>${e(backup.directory)}</strong></div>`
      : `<div class="callout">${e(t('backup.noDirectory'))}</div>`}
    <div class="step-actions">
      <button class="text-button" type="button" data-action="onboarding-next-model">${e(t('common.skipAction'))}</button>
      ${configured
        ? `<button class="button primary" type="button" data-action="onboarding-next-model">${e(t('common.continue'))} <span aria-hidden="true">→</span></button>`
        : `<button class="button primary" type="button" data-action="backup-choose-directory">${e(t('backup.chooseDirectory'))}</button>`}
    </div>`;
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return t('common.unknown');
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  return `${Math.max(1, Math.round(bytes / 1024 ** 2))} MB`;
}

function modelPercent(status) {
  const total = Number(status?.total || 0);
  const received = Number(status?.received || 0);
  if (!total) return 0;
  return Math.min(100, Math.max(0, Math.round((received / total) * 100)));
}

function modelErrorMessage(status) {
  const code = status?.error_code;
  if (code) {
    const localized = t(`error.${code}`);
    if (localized !== `error.${code}`) return localized;
  }
  if (status?.service_error) {
    const localized = t(`error.${status.service_error}`);
    if (localized !== `error.${status.service_error}`) return localized;
  }
  return status?.error || t('model.failed');
}

function modelProgress(status, compact = false) {
  const total = Number(status?.total || 0);
  const received = Number(status?.received || 0);
  const percent = modelPercent(status);
  return `
    <div class="model-progress ${compact ? 'compact' : ''}">
      <div class="model-progress-head">
        <strong>${e(status?.phase === 'verifying' ? t('model.verifying') : t('model.downloading'))}</strong>
        <span>${percent}%</span>
      </div>
      <div class="meter-track" role="progressbar" aria-valuemin="0" aria-valuemax="100"
        aria-valuenow="${percent}" aria-label="${e(t('model.downloading'))}">
        <span style="width:${percent}%"></span>
      </div>
      <small>${e(formatBytes(received))} / ${e(formatBytes(total))}</small>
    </div>`;
}

function onboardingModel() {
  if (!window.qoneDesktop) {
    return `
      <span class="step-count">04 / 04</span>
      <h2>${e(t('model.onboardingTitle'))}</h2>
      <p class="lede">${e(t('model.onboardingBody'))}</p>
      <div class="callout">${e(t('settings.rulesReady'))} · ${e(t('settings.rulesReadyHelp'))}</div>
      <div class="step-actions">
        <span></span>
        <button class="button primary" type="button" data-action="onboarding-finish">${e(t('onboarding.finish'))} <span aria-hidden="true">→</span></button>
      </div>`;
  }
  if (!state.model) {
    void loadModelStatus();
    return `
      <span class="step-count">04 / 04</span>
      <h2>${e(t('model.onboardingTitle'))}</h2>
      <p class="lede">${e(t('model.onboardingBody'))}</p>
      <div class="loading-line">${e(t('common.loading'))}</div>`;
  }
  const status = state.model;
  const ready = status.phase === 'installed';
  const busy = status.downloading || status.phase === 'verifying';
  return `
    <span class="step-count">04 / 04</span>
    <h2>${e(t('model.onboardingTitle'))}</h2>
    <p class="lede">${e(t('model.onboardingBody'))}</p>
    ${ready
      ? `<div class="model-ready-card"><span class="model-orbit" aria-hidden="true"></span><div><strong>${e(t('model.ready'))}</strong><p>${e(t('model.onboardingReady'))}</p></div></div>`
      : busy
        ? modelProgress(status)
        : `<div class="model-facts">
            <span>${e(t('model.size'))}</span><span>${e(t('model.license'))}</span>
          </div>
          ${status.phase === 'error' || status.error_code ? `<div class="callout warning">${e(modelErrorMessage(status))}</div>` : ''}
          <p class="fine-print">${e(t('model.requirements'))}</p>`}
    <div class="step-actions model-step-actions">
      ${busy
        ? `<button class="text-button" type="button" data-action="model-cancel">${e(t('model.cancel'))}</button>
           <button class="text-button" type="button" data-action="onboarding-finish">${e(t('common.skipAction'))}</button>`
        : ready
          ? `<span class="fine-print">${e(t('model.onboardingDownloaded'))}</span>
             <button class="button primary" type="button" data-action="onboarding-finish">${e(t('onboarding.finish'))} <span aria-hidden="true">→</span></button>`
          : `<button class="text-button" type="button" data-action="onboarding-finish">${e(t('model.keepRules'))}</button>
             <button class="button primary" type="button" data-action="model-download">${e(t('model.download'))}</button>`}
    </div>`;
}

function renderToday() {
  const planner = state.data.planner;
  const goals = activeGoals();
  const tasks = todaysTasks();
  const completed = completedToday();
  const primary = planner.items[0];
  const remaining = Math.max(
    0,
    Number(state.data.settings.daily_available_minutes || 0) -
      tasks.reduce(
        (total, task) => total + Number(task.focus_minutes || task.estimate_minutes || 0),
        0,
      ),
  );
  return `
    <section class="page-intro today-intro">
      <div>
        <span class="eyebrow">${e(todayLabel())}</span>
        <h1>${e(t('today.title'))}</h1>
        <p>${e(t('today.subtitle'))}</p>
      </div>
      <button class="button" type="button" data-action="show-goal-form">＋ ${e(t('goal.add'))}</button>
    </section>
    ${state.showGoalForm
      ? renderGoalForm(
          state.editingGoalId
            ? state.data.goals.find((goal) => goal.id === state.editingGoalId)
            : null,
        )
      : ''}
    <div class="today-grid">
      <section class="recommendation-panel" aria-labelledby="recommendation-heading">
        <div class="section-kicker">
          <span>${e(t('today.recommendation'))}</span>
          <span class="status-pill">${e(plannerStatusLabel(planner.status))}</span>
        </div>
        ${primary ? renderRecommendation(primary) : renderRecommendationEmpty(goals, planner)}
      </section>
      <aside class="day-map" aria-label="${e(t('today.overview'))}">
        <span class="section-kicker">${e(t('today.overview'))}</span>
        <div class="day-stat">
          <strong>${goals.length}</strong>
          <span>${e(t('today.activeGoals'))}</span>
        </div>
        <div class="day-stat">
          <strong>${completed.length}<small>/${tasks.length}</small></strong>
          <span>${e(t('today.actionsDone'))}</span>
        </div>
        <div class="time-meter">
          <div class="time-meter-label"><span>${e(t('today.freeTime'))}</span><strong>${remaining} min</strong></div>
          <div class="meter-track" role="img" aria-label="${e(t('today.freeTimeAria', { minutes: remaining }))}">
            <span style="width:${Math.min(100, Math.max(0, 100 - (remaining / Math.max(1, Number(state.data.settings.daily_available_minutes))) * 100))}%"></span>
          </div>
          <small>${e(t('today.budget', { minutes: state.data.settings.daily_available_minutes }))}</small>
        </div>
        <p class="day-quote">${e(t('today.quote'))}</p>
      </aside>
    </div>
    <section class="schedule-panel" aria-labelledby="schedule-heading">
      <div class="section-heading">
        <div>
          <span class="section-kicker">${e(t('today.commitments'))}</span>
          <h2 id="schedule-heading">${e(t('today.schedule'))}</h2>
        </div>
        <button class="text-button" type="button" data-action="show-task-form">＋ ${e(t('task.add'))}</button>
      </div>
      ${state.showTaskForm ? renderTaskForm() : ''}
      ${
        tasks.length
          ? `<div class="task-list">${tasks.map(renderTask).join('')}</div>`
          : `<div class="quiet-empty"><p>${e(t('today.noTasks'))}</p><button class="text-button" type="button" data-action="show-task-form">${e(t('task.addFirst'))}</button></div>`
      }
    </section>
    ${goals.length ? '' : `<section class="first-goal-card"><div><span class="section-kicker">${e(t('today.firstGoalKicker'))}</span><h2>${e(t('today.firstGoalTitle'))}</h2><p>${e(t('today.firstGoalBody'))}</p></div><button class="button primary" type="button" data-action="show-goal-form">${e(t('goal.add'))}</button></section>`}`;
}

function renderRecommendation(item) {
  return `
    <article class="recommendation-card">
      <div class="recommendation-meta">
        <span>${e(domainLabel(item.domain))}</span>
        <span>${Number(item.minutes)} min</span>
        <span>${e(sourceLabel(item.source))}</span>
      </div>
      <h2>${e(item.title)}</h2>
      <p class="recommendation-reason">${e(item.reason)}</p>
      <div class="step-grid">
        <div><span>01</span><h3>${e(t('recommendation.firstStep'))}</h3><p>${e(item.first_step || t('common.notSet'))}</p></div>
        <div><span>02</span><h3>${e(t('recommendation.doneWhen'))}</h3><p>${e(item.done_when || t('common.notSet'))}</p></div>
      </div>
      <div class="recommendation-actions">
        <button class="button primary" type="button" data-action="accept-suggestion"
          data-id="${e(item.id)}" data-proposal="${e(item.proposal_sha256)}">${e(t('recommendation.accept'))}</button>
        <button class="text-button" type="button" data-action="dismiss-suggestion"
          data-id="${e(item.id)}" data-proposal="${e(item.proposal_sha256)}">${e(t('recommendation.dismiss'))}</button>
      </div>
      <p class="fine-print">${e(t('recommendation.confirm'))}</p>
    </article>`;
}

function renderRecommendationEmpty(goals, planner) {
  if (!goals.length) {
    return `<div class="recommendation-empty">
      <span class="empty-glyph" aria-hidden="true">↗</span>
      <h2>${e(t('today.goalFirst'))}</h2>
      <p>${e(t('today.goalFirstBody'))}</p>
      <button class="button primary" type="button" data-action="show-goal-form">${e(t('goal.add'))}</button>
    </div>`;
  }
  return `<div class="recommendation-empty">
    <span class="empty-glyph" aria-hidden="true">○</span>
    <h2>${e(t('today.noRecommendation'))}</h2>
    <p>${e(t('today.noRecommendationBody'))}</p>
    <button class="button" type="button" data-action="refresh-planner">${e(t('common.refresh'))}</button>
  </div>`;
}

function renderTask(task) {
  return `
    <label class="task-row ${task.done ? 'done' : ''}">
      <input type="checkbox" data-task-id="${e(task.id)}" ${task.done ? 'checked' : ''}>
      <span class="custom-check" aria-hidden="true"></span>
      <span class="task-copy">
        <strong>${e(task.title)}</strong>
        <small>${e(domainLabel(task.domain))}${task.focus_minutes || task.estimate_minutes ? ` · ${task.focus_minutes || task.estimate_minutes} min` : ''}</small>
      </span>
    </label>`;
}

function renderTaskForm() {
  return `
    <form id="task-form" class="inline-form">
      <label>${e(t('task.name'))}<input name="title" required maxlength="300" autofocus></label>
      <label>${e(t('task.minutes'))}<input name="estimate_minutes" type="number" min="5" max="480" value="25" required></label>
      <label>${e(t('goal.domainLabel'))}<select name="domain">${['work', 'learning', 'energy', 'recovery', 'other']
        .map((domain) => `<option value="${domain}">${e(domainLabel(domain))}</option>`)
        .join('')}</select></label>
      <div class="inline-actions">
        <button class="button primary" type="submit">${e(t('common.save'))}</button>
        <button class="text-button" type="button" data-action="cancel-task-form">${e(t('common.cancel'))}</button>
      </div>
    </form>`;
}

function renderGoals() {
  const goals = [...state.data.goals].sort(
    (a, b) =>
      Number(a.status === 'active' ? 0 : 1) - Number(b.status === 'active' ? 0 : 1) ||
      Number(b.priority) - Number(a.priority) ||
      String(a.created_at).localeCompare(String(b.created_at)),
  );
  return `
    <section class="page-intro">
      <div>
        <span class="eyebrow">${e(t('goals.kicker'))}</span>
        <h1>${e(t('goals.title'))}</h1>
        <p>${e(t('goals.subtitle'))}</p>
      </div>
      <button class="button primary" type="button" data-action="show-goal-form">＋ ${e(t('goal.add'))}</button>
    </section>
    ${state.showGoalForm
      ? renderGoalForm(
          state.editingGoalId
            ? state.data.goals.find((goal) => goal.id === state.editingGoalId)
            : null,
        )
      : ''}
    <div class="goals-board">
      ${goals.length
        ? goals.map((goal, index) => renderGoal(goal, index)).join('')
        : `<div class="quiet-empty wide"><p>${e(t('goals.empty'))}</p><button class="button primary" type="button" data-action="show-goal-form">${e(t('goal.addFirst'))}</button></div>`}
    </div>`;
}

function renderGoal(goal, index) {
  const tasks = state.data.tasks.filter((task) => task.goal_id === goal.id);
  const done = tasks.filter((task) => task.done).length;
  return `
    <article class="goal-card ${goal.status !== 'active' ? 'inactive' : ''}">
      <span class="goal-index">${String(index + 1).padStart(2, '0')}</span>
      <div class="goal-main">
        <div class="goal-meta">
          <span>${e(domainLabel(goal.domain))}</span>
          <span>${e(t('goal.priority', { priority: goal.priority }))}</span>
          <span class="goal-status ${e(goal.status)}">${e(goalStatusLabel(goal.status))}</span>
        </div>
        <h2>${e(goal.title)}</h2>
        <p>${e(goal.success_criterion)}</p>
        <div class="goal-progress">
          <span>${e(t('goals.actions', { done, total: tasks.length }))}</span>
          <span>${goal.deadline ? e(t('goal.due', { date: formatDate(goal.deadline, { year: 'numeric' }) })) : e(t('goal.noDeadline'))}</span>
        </div>
      </div>
      <div class="goal-actions">
        <button class="text-button" type="button" data-action="edit-goal" data-id="${e(goal.id)}">${e(t('common.edit'))}</button>
        ${goal.status === 'active'
          ? `<button class="text-button" type="button" data-action="goal-status" data-id="${e(goal.id)}" data-status="completed">${e(t('goal.complete'))}</button>
             <button class="text-button" type="button" data-action="goal-status" data-id="${e(goal.id)}" data-status="paused">${e(t('goal.pause'))}</button>`
          : `<button class="text-button" type="button" data-action="goal-status" data-id="${e(goal.id)}" data-status="active">${e(t('goal.resume'))}</button>`}
      </div>
    </article>`;
}

function renderGoalForm(goal = null) {
  const value = goal || {};
  return `
    <form id="goal-form" data-id="${e(goal?.id || '')}" class="editor-card form-stack">
      <div class="editor-heading">
        <div><span class="section-kicker">${e(t('goal.editorKicker'))}</span><h2>${e(goal ? t('goal.editTitle') : t('goal.newTitle'))}</h2></div>
        <button class="icon-button" type="button" data-action="cancel-goal-form" aria-label="${e(t('common.close'))}">×</button>
      </div>
      <label>${e(t('goal.titleLabel'))}<input name="title" required maxlength="150" value="${e(value.title || '')}" autofocus></label>
      <label>${e(t('goal.criterionLabel'))}<textarea name="success_criterion" required maxlength="1000" rows="3">${e(value.success_criterion || '')}</textarea></label>
      <div class="form-grid">
        <label>${e(t('goal.domainLabel'))}<select name="domain">${['work', 'learning', 'energy', 'recovery', 'other']
          .map((domain) => `<option value="${domain}" ${domain === (value.domain || 'learning') ? 'selected' : ''}>${e(domainLabel(domain))}</option>`)
          .join('')}</select></label>
        <label>${e(t('goal.priorityLabel'))}<select name="priority">${[5, 4, 3, 2, 1]
          .map((priority) => `<option value="${priority}" ${priority === (value.priority || 3) ? 'selected' : ''}>${priority}${priority === 5 ? ` · ${e(t('goal.highest'))}` : ''}</option>`)
          .join('')}</select></label>
      </div>
      <label>${e(t('goal.deadlineLabel'))} <small>${e(t('common.optional'))}</small><input name="deadline" type="datetime-local" value="${toLocalInput(value.deadline)}"></label>
      <div class="inline-actions">
        <button class="button primary" type="submit">${e(t('goal.save'))}</button>
        <button class="text-button" type="button" data-action="cancel-goal-form">${e(t('common.cancel'))}</button>
      </div>
    </form>`;
}

function toLocalInput(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function renderReview() {
  const report = state.data.report;
  const calibration = report.calibration;
  return `
    <section class="page-intro">
      <div>
        <span class="eyebrow">${e(t('review.kicker'))}</span>
        <h1>${e(t('review.title'))}</h1>
        <p>${e(t('review.subtitle'))}</p>
      </div>
    </section>
    <div class="review-grid">
      <section class="review-prompt">
        <span class="section-kicker">${e(t('review.write'))}</span>
        <h2>${e(t('review.promptTitle'))}</h2>
        <ol>
          <li>${e(t('review.question1'))}</li>
          <li>${e(t('review.question2'))}</li>
          <li>${e(t('review.question3'))}</li>
        </ol>
        <form id="review-form" class="form-stack">
          <label>${e(t('review.notes'))}<textarea name="text" rows="7" maxlength="12000" required></textarea></label>
          <div class="inline-actions">
            <label class="period-label">${e(t('review.window'))}<select name="days">${[7, 30, 90]
              .map((days) => `<option value="${days}" ${days === 7 ? 'selected' : ''}>${e(t('review.days', { days }))}</option>`)
              .join('')}</select></label>
            <button class="button primary" type="submit">${e(t('review.save'))}</button>
          </div>
        </form>
      </section>
      <aside class="review-stats">
        <span class="section-kicker">${e(t('review.evidence'))}</span>
        <div class="review-stat"><strong>${report.resolved_decisions}<small>/${report.decisions}</small></strong><span>${e(t('review.reviewed'))}</span></div>
        <div class="review-stat"><strong>${percent(report.recommendation_adoption)}</strong><span>${e(t('review.adoption'))}</span></div>
        <div class="review-stat"><strong>${calibration.n}</strong><span>${e(t('review.scoredForecasts'))}</span></div>
        <p>${e(t('review.interpretation'))}</p>
      </aside>
    </div>
    <section class="history-section">
      <div class="section-heading">
        <div><span class="section-kicker">${e(t('review.historyKicker'))}</span><h2>${e(t('review.history'))}</h2></div>
        <span>${state.data.reviews.length}</span>
      </div>
      ${
        state.data.reviews.length
          ? state.data.reviews
              .slice(0, 10)
              .map(
                (review) => `
                <article class="history-row">
                  <div class="history-meta"><span>${e(formatDate(review.created_at, { hour: '2-digit', minute: '2-digit' }))}</span><span>${e(t('review.days', { days: review.days }))}</span></div>
                  <p>${e(review.text)}</p>
                </article>`,
              )
              .join('')
          : `<div class="quiet-empty"><p>${e(t('review.empty'))}</p></div>`
      }
    </section>`;
}

function percent(value) {
  return value === null || value === undefined
    ? '—'
    : `${Math.round(Number(value) * 100)}%`;
}

function renderSettings() {
  const settings = state.data.settings;
  return `
    <section class="page-intro">
      <div>
        <span class="eyebrow">${e(t('settings.kicker'))}</span>
        <h1>${e(t('settings.title'))}</h1>
        <p>${e(t('settings.subtitle'))}</p>
      </div>
    </section>
    <div class="settings-layout">
      <form id="settings-form" class="settings-card form-stack">
        <div class="section-heading"><div><span class="section-kicker">${e(t('settings.preferencesKicker'))}</span><h2>${e(t('settings.preferences'))}</h2></div></div>
        <label>${e(t('settings.language'))}
          <select name="language">
            <option value="system" ${settings.language === 'system' ? 'selected' : ''}>${e(t('settings.systemLanguage'))}</option>
            <option value="zh-CN" ${settings.language === 'zh-CN' ? 'selected' : ''}>简体中文</option>
            <option value="en-US" ${settings.language === 'en-US' ? 'selected' : ''}>English</option>
          </select>
        </label>
        <label>${e(t('settings.dailyMinutes'))}
          <input name="daily_available_minutes" type="number" min="5" max="480" value="${Number(settings.daily_available_minutes)}" required>
          <small>${e(t('settings.dailyMinutesHelp'))}</small>
        </label>
        <label class="check-row">
          <input name="auto_recommend_enabled" type="checkbox" ${settings.auto_recommend_enabled ? 'checked' : ''}>
          <span><strong>${e(t('settings.autoRecommend'))}</strong><small>${e(t('settings.autoRecommendHelp'))}</small></span>
        </label>
        <button class="button primary" type="submit">${e(t('settings.save'))}</button>
      </form>
      <section class="settings-card">
        <div class="section-heading"><div><span class="section-kicker">${e(t('settings.backupKicker'))}</span><h2>${e(t('settings.backup'))}</h2></div></div>
        <div id="backup-status" class="backup-box"><p>${e(t('common.loading'))}</p></div>
      </section>
      <section class="settings-card">
        <div class="section-heading"><div><span class="section-kicker">${e(t('model.kicker'))}</span><h2>${e(t('model.title'))}</h2></div></div>
        <div id="model-status" class="model-box"><p>${e(t('common.loading'))}</p></div>
        <a class="button" href="/advanced">${e(t('settings.advancedModels'))} <span aria-hidden="true">↗</span></a>
      </section>
      <section class="settings-card about-card">
        <div class="section-heading"><div><span class="section-kicker">${e(t('settings.aboutKicker'))}</span><h2>${e(t('settings.about'))}</h2></div></div>
        <dl>
          <div><dt>${e(t('settings.version'))}</dt><dd>${e(state.data.version)}</dd></div>
          <div><dt>${e(t('settings.storage'))}</dt><dd>${e(state.data.settings.secret_management === 'os_keychain' ? t('settings.storageKeychain') : t('settings.storageLocal'))}</dd></div>
          <div><dt>${e(t('settings.telemetry'))}</dt><dd>${e(t('settings.telemetryValue'))}</dd></div>
        </dl>
        ${window.qoneDesktop?.updateStatus ? `
          <div class="update-block">
            <div class="section-heading"><div><span class="section-kicker">${e(t('update.kicker'))}</span><h2>${e(t('update.title'))}</h2></div></div>
            <div id="update-status" class="update-box"><p>${e(t('common.loading'))}</p></div>
          </div>` : ''}
        <p class="fine-print">${e(t('settings.workingData'))}</p>
        ${
          window.qoneDesktop
            ? `<div class="support-block">
                <strong>${e(t('settings.supportTitle'))}</strong>
                <p>${e(t('settings.supportHelp'))}</p>
                <div class="backup-actions">
                  <button class="button" type="button" data-action="support-preview">${e(t('support.preview'))}</button>
                  <button class="text-button" type="button" data-action="support-export">${e(t('support.export'))}</button>
                </div>
              </div>`
            : ''
        }
      </section>
    </div>`;
}

async function loadBackupStatus() {
  if (!window.qoneDesktop) {
    state.backup = { browser: true, persistent: false };
  } else {
    try {
      state.backup = await window.qoneDesktop.backupStatus();
    } catch (error) {
      state.backup = { error: messageFor(error), persistent: false };
    }
  }
  if (state.data?.settings.onboarding_complete) renderBackupIntoPage();
  else render();
}

function renderBackupIntoPage() {
  const target = $('#backup-status');
  if (!target) return;
  const backup = state.backup;
  if (!backup) {
    target.innerHTML = `<p>${e(t('common.loading'))}</p>`;
    return;
  }
  if (backup.browser) {
    target.innerHTML = `<p>${e(t('backup.desktopOnly'))}</p><a class="button" href="/advanced">${e(t('backup.browserBackup'))} ↗</a>`;
    return;
  }
  if (backup.error) {
    target.innerHTML = `<div class="callout warning">${e(backup.error)}</div>`;
    return;
  }
  const statusText = backup.enabled
    ? t('backup.enabled')
    : backup.paused
      ? t('backup.paused')
      : t('backup.disabled');
  const pause =
    backup.pause_reason === 'SECRET_STORE_SESSION_ONLY'
      ? t('backup.sessionOnly')
      : backup.pause_reason === 'RECOVERY_KEY_MISSING'
        ? t('backup.keyMissing')
        : '';
  target.innerHTML = `
    <div class="backup-headline"><span class="backup-icon" aria-hidden="true">◇</span><div><strong>${e(statusText)}</strong><p>${e(backup.directory || t('backup.noDirectory'))}</p></div></div>
    ${pause ? `<div class="callout warning">${e(pause)}</div>` : ''}
    <dl class="backup-details">
      <div><dt>${e(t('backup.lastBackup'))}</dt><dd>${backup.last_backup_at ? e(formatDate(backup.last_backup_at, { hour: '2-digit', minute: '2-digit' })) : e(t('backup.never'))}</dd></div>
      <div><dt>${e(t('backup.protection'))}</dt><dd>${e(backup.persistent ? t('backup.keychain') : t('backup.sessionOnlyShort'))}</dd></div>
    </dl>
    <div class="backup-actions">
      <button class="button primary" type="button" data-action="backup-now">${e(t('backup.createNow'))}</button>
      ${backup.automatic_available && !backup.recovery_key_confirmed
        ? `<button class="button" type="button" data-action="backup-choose-directory">${e(t('backup.chooseDirectory'))}</button>`
        : ''}
      ${backup.enabled
        ? `<button class="text-button" type="button" data-action="backup-disable">${e(t('backup.disableAuto'))}</button>`
        : backup.automatic_available && backup.recovery_key_confirmed
          ? `<button class="text-button" type="button" data-action="backup-enable-existing">${e(t('backup.enableAuto'))}</button>`
          : ''}
      <button class="text-button" type="button" data-action="backup-inspect">${e(t('backup.restore'))}</button>
    </div>
    <p class="fine-print">${e(t('backup.encryptionNote'))}</p>`;
}

async function loadModelStatus() {
  if (!window.qoneDesktop) {
    state.model = { phase: 'browser', downloading: false };
  } else {
    try {
      state.model = await window.qoneDesktop.modelStatus();
    } catch (error) {
      state.model = {
        phase: 'error',
        downloading: false,
        error: messageFor(error),
        error_code: 'LOCAL_MODEL_SERVICE_FAILED',
      };
    }
  }
  if (state.data?.settings.onboarding_complete) renderModelIntoPage();
  else render();
}

function renderModelIntoPage() {
  const target = $('#model-status');
  if (!target) return;
  const status = state.model;
  if (!status) {
    target.innerHTML = `<p>${e(t('common.loading'))}</p>`;
    return;
  }
  if (status.phase === 'browser') {
    target.innerHTML = `
      <div class="engine-row"><span class="engine-dot"></span><div><strong>${e(t('settings.rulesReady'))}</strong><p>${e(t('settings.rulesReadyHelp'))}</p></div></div>`;
    return;
  }
  const ready = status.phase === 'installed';
  const busy = status.downloading || status.phase === 'verifying';
  const error = status.phase === 'error' || Boolean(status.error_code);
  target.innerHTML = `
    <div class="model-status-head">
      <span class="engine-dot ${ready && status.service_active ? 'ready' : ''}" aria-hidden="true"></span>
      <div>
        <strong>${e(ready ? t('model.ready') : busy ? t('model.downloading') : error ? t('model.failed') : t('model.notInstalled'))}</strong>
        <p>${e(ready ? t('model.readyHelp') : busy ? t('model.body') : error ? modelErrorMessage(status) : t('model.notInstalledHelp'))}</p>
      </div>
    </div>
    ${busy ? modelProgress(status, true) : ''}
    ${ready && status.service_error ? `<div class="callout warning">${e(t('model.serviceUnavailable'))}</div>` : ''}
    <div class="model-facts">
      <span>${e(status.model?.name || 'Qwen3-0.6B-Q8_0')}</span>
      <span>${e(t('model.size'))}</span>
      <span>${e(t('model.license'))}</span>
    </div>
    <div class="model-actions">
      ${busy
        ? `<button class="button" type="button" data-action="model-cancel">${e(t('model.cancel'))}</button>`
        : ready
          ? `<button class="text-button" type="button" data-action="model-remove">${e(t('model.remove'))}</button>`
          : `<button class="button primary" type="button" data-action="model-download">${e(status.phase === 'error' ? t('common.tryAgain') : t('model.download'))}</button>`}
    </div>
    <p class="fine-print">${e(t('model.requirements'))}</p>`;
}

async function loadUpdateStatus() {
  if (!window.qoneDesktop?.updateStatus) {
    state.update = null;
    return;
  }
  try {
    state.update = await window.qoneDesktop.updateStatus();
  } catch (error) {
    state.update = {
      phase: 'error',
      error_code: 'UPDATE_FAILED',
      retryable: true,
      manual_only: false,
      can_download: false,
      can_install: false,
    };
  }
  if (state.data?.settings.onboarding_complete) renderUpdateIntoPage();
}

function updateErrorMessage(status) {
  const code = status?.error_code;
  if (!code) return t('update.error');
  const localized = t(`error.${code}`);
  return localized === `error.${code}` ? t('update.error') : localized;
}

function renderUpdateIntoPage() {
  const target = $('#update-status');
  if (!target) return;
  const status = state.update;
  if (!status) {
    target.innerHTML = `<p>${e(t('common.loading'))}</p>`;
    return;
  }
  const phase = status.phase || 'error';
  const busy = phase === 'checking' || phase === 'downloading';
  const available = phase === 'available';
  const ready = phase === 'ready';
  let headline = t('update.upToDate');
  let detail = t('update.security');
  if (phase === 'checking') {
    headline = t('update.checking');
    detail = t('update.checkingHelp');
  } else if (phase === 'downloading') {
    headline = t('update.downloading');
    detail = t('update.downloadHelp');
  } else if (available) {
    headline = t('update.available', { version: status.available_version || '' });
    detail = status.manual_only ? t('update.manualOnly') : t('update.availableHelp');
  } else if (ready) {
    headline = t('update.ready');
    detail = t('update.readyHelp');
  } else if (phase === 'unavailable') {
    headline = t('update.unavailable');
    detail = t('update.notConfigured');
  } else if (phase === 'up_to_date') {
    headline = t('update.upToDateHelp');
  } else if (phase === 'error') {
    headline = t('update.failed');
    detail = updateErrorMessage(status);
  }
  const progress =
    phase === 'downloading' && Number.isFinite(Number(status.progress_percent))
      ? `<div class="update-progress">
           <div class="model-progress-head"><strong>${e(t('update.downloading'))}</strong><span>${Math.round(Number(status.progress_percent))}%</span></div>
           <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(Number(status.progress_percent))}" aria-label="${e(t('update.downloading'))}">
             <span style="width:${Math.min(100, Math.max(0, Number(status.progress_percent)))}%"></span>
           </div>
           <small>${e(formatBytes(status.transferred))} / ${e(formatBytes(status.total))}</small>
         </div>`
      : '';
  const actions = [];
  if (!busy && !ready) {
    actions.push(
      `<button class="button${available ? '' : ' primary'}" type="button" data-action="update-check">${e(t('update.check'))}</button>`,
    );
  }
  if (available && status.manual_only && status.manual_download_url) {
    actions.push(
      `<button class="button primary" type="button" data-action="update-open-download">${e(t('update.manualDownload'))}</button>`,
    );
  } else if (available && status.can_download) {
    actions.push(
      `<button class="button primary" type="button" data-action="update-download">${e(t('update.download'))}</button>`,
    );
  }
  if (status.rollback_available) {
    actions.push(
      `<button class="button" type="button" data-action="update-open-rollback">${e(t('update.rollback'))}</button>`,
    );
  }
  if (ready && status.can_install) {
    actions.push(
      `<button class="button primary" type="button" data-action="update-install">${e(t('update.install'))}</button>`,
    );
  }
  target.innerHTML = `
    <div class="update-headline">
      <span class="update-mark ${ready ? 'ready' : busy ? 'busy' : ''}" aria-hidden="true">↻</span>
      <div><strong>${e(headline)}</strong><p>${e(detail)}</p></div>
    </div>
    ${progress}
    <div class="update-meta">
      <span>${e(t('update.current', { version: status.current_version || state.data.version }))}</span>
      <span>${e(t(`update.channel.${status.channel || 'stable'}`))}</span>
    </div>
    ${actions.length ? `<div class="update-actions">${actions.join('')}</div>` : ''}
    <p class="fine-print">${e(t('update.security'))}</p>`;
}

async function refresh(options = {}) {
  const routeAtStart = activeRoute();
  const previousSignature = state.plannerSignature;
  state.data = await api('bootstrap?days=30');
  state.plannerSignature = JSON.stringify(state.data.planner);
  const locale = state.data.locale || state.data.settings.resolved_language || browserLocale();
  if (options.preserveLocale && state.localeChoice) state.locale = state.localeChoice;
  else state.locale = locale;
  setLocale(state.locale);
  // An async action may finish after the user has moved to another route.
  // Keep the newer page and its in-progress form intact.
  if (routeAtStart !== activeRoute()) return;
  render();
  if (!options.silent && previousSignature && previousSignature !== state.plannerSignature) {
    toast(t('common.updated'));
  }
}

function showDialog(title, html) {
  $('#dialog-title').textContent = title;
  $('#dialog-body').innerHTML = html;
  const dialog = $('#consumer-dialog');
  if (!dialog.open) dialog.showModal();
}

function closeDialog() {
  const dialog = $('#consumer-dialog');
  if (dialog.open) dialog.close();
}

async function submitGoal(form) {
  const data = Object.fromEntries(new FormData(form));
  const body = {
    ...data,
    priority: Number(data.priority || 3),
    deadline: data.deadline ? new Date(data.deadline).toISOString() : null,
  };
  const id = form.dataset.id;
  await api(`goals${id ? `/${id}` : ''}`, {
    method: id ? 'PATCH' : 'POST',
    body: JSON.stringify(body),
  });
}

async function handleSubmit(event) {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  event.preventDefault();
  const submit = form.querySelector('[type="submit"]');
  if (submit) submit.disabled = true;
  try {
    if (form.id === 'onboarding-goal-form') {
      await submitGoal(form);
      state.onboardingStep = 2;
      await loadBackupStatus();
      return;
    }
    if (form.id === 'goal-form') {
      await submitGoal(form);
      state.showGoalForm = false;
      state.editingGoalId = null;
      await refresh();
      toast(t('goal.saved'));
      return;
    }
    if (form.id === 'task-form') {
      const data = Object.fromEntries(new FormData(form));
      await post('tasks', {
        ...data,
        estimate_minutes: Number(data.estimate_minutes),
        priority: 3,
      });
      state.showTaskForm = false;
      await refresh();
      toast(t('task.saved'));
      return;
    }
    if (form.id === 'review-form') {
      const data = Object.fromEntries(new FormData(form));
      await post('reviews', { text: data.text, days: Number(data.days) });
      await refresh();
      toast(t('review.saved'));
      return;
    }
    if (form.id === 'settings-form') {
      const data = Object.fromEntries(new FormData(form));
      const result = await post('settings', {
        language: data.language,
        daily_available_minutes: Number(data.daily_available_minutes),
        auto_recommend_enabled: form.elements.auto_recommend_enabled.checked,
      });
      state.localeChoice = result.resolved_language;
      await refresh();
      toast(t('settings.saved'));
      return;
    }
    if (form.id === 'restore-key-form') {
      const key = new FormData(form).get('recovery_key')?.toString().trim();
      if (!key) throw new Error(t('backup.enterKey'));
      await window.qoneDesktop.restoreBackup(key);
      closeDialog();
      location.reload();
    }
  } catch (error) {
    toast(messageFor(error), true);
  } finally {
    if (submit) submit.disabled = false;
  }
}

async function handleTaskChange(input) {
  const routeAtStart = activeRoute();
  try {
    await api(`tasks/${input.dataset.taskId}`, {
      method: 'PATCH',
      body: JSON.stringify({ done: input.checked }),
    });
    // Do not let a late task refresh replace a form the user opened while the
    // request was in flight.
    if (activeRoute() !== routeAtStart) return;
    await refresh();
  } catch (error) {
    input.checked = !input.checked;
    toast(messageFor(error), true);
  }
}

async function chooseBackupDirectory() {
  try {
    const result = await window.qoneDesktop.chooseBackupDirectory();
    if (result.canceled) return;
    state.backupDraft = result;
    await loadBackupStatus();
    if (state.data.settings.onboarding_complete) {
      showDialog(
        t('backup.saveKeyTitle'),
        `<p>${e(t('backup.saveKeyBody'))}</p>
         <label>${e(t('backup.recoveryKey'))}<textarea id="backup-recovery-key" readonly rows="4">${e(result.recoveryKey)}</textarea></label>
         ${recoveryQrMarkup(result)}
         <label class="check-row"><input id="backup-key-confirmed" type="checkbox"><span>${e(t('backup.confirmSaved'))}</span></label>
         <div class="dialog-actions">
           <button class="button" type="button" data-action="backup-copy-key">${e(t('backup.copyKey'))}</button>
           <button class="button primary" type="button" data-action="backup-enable-auto">${e(t('backup.enableAuto'))}</button>
         </div>`,
      );
    }
  } catch (error) {
    toast(messageFor(error), true);
  }
}

async function enableAutoBackup() {
  if (!$('#backup-key-confirmed')?.checked) {
    toast(t('backup.confirmFirst'), true);
    return;
  }
  await window.qoneDesktop.enableAutoBackup(true);
  state.backupDraft = null;
  closeDialog();
  await loadBackupStatus();
  if (!state.data.settings.onboarding_complete) {
    state.onboardingStep = 2;
    render();
  }
  toast(t('backup.enabled'));
}

async function handleAction(action, node) {
  if (state.busy) return;
  state.busy = true;
  try {
    if (action === 'reload-app') return location.reload();
    if (action === 'close-dialog') return closeDialog();
    if (action === 'show-goal-form') {
      state.editingGoalId = null;
      state.showGoalForm = true;
      return render();
    }
    if (action === 'cancel-goal-form') {
      state.showGoalForm = false;
      state.editingGoalId = null;
      return render();
    }
    if (action === 'edit-goal') {
      state.editingGoalId = node.dataset.id;
      state.showGoalForm = true;
      render();
      return $('#goal-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    if (action === 'show-task-form') {
      state.showTaskForm = true;
      return render();
    }
    if (action === 'cancel-task-form') {
      state.showTaskForm = false;
      return render();
    }
    if (action === 'goal-status') {
      await api(`goals/${node.dataset.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: node.dataset.status }),
      });
      await refresh();
      return toast(t('goal.updated'));
    }
    if (action === 'refresh-planner') {
      await post('planner/refresh', {});
      await refresh();
      return toast(t('today.refreshing'));
    }
    if (action === 'accept-suggestion' || action === 'dismiss-suggestion') {
      await post(`planner/${node.dataset.id}/feedback`, {
        action: action === 'accept-suggestion' ? 'accept' : 'dismiss',
        proposal_sha256: node.dataset.proposal,
      });
      await refresh();
      return toast(
        action === 'accept-suggestion'
          ? t('recommendation.accepted')
          : t('recommendation.dismissed'),
      );
    }
    if (action === 'onboarding-language') {
      state.locale = node.dataset.locale;
      state.localeChoice = node.dataset.locale;
      setLocale(state.locale);
      return render();
    }
    if (action === 'onboarding-language-next') {
      state.onboardingStep = 1;
      return render();
    }
    if (action === 'onboarding-skip-goal') {
      state.onboardingStep = 2;
      await loadBackupStatus();
      return;
    }
    if (action === 'onboarding-skip-backup' || action === 'onboarding-next-model') {
      state.onboardingStep = 3;
      await loadModelStatus();
      return;
    }
    if (action === 'onboarding-enable-backup') {
      await enableAutoBackup();
      state.onboardingStep = 3;
      await loadModelStatus();
      return render();
    }
    if (action === 'onboarding-finish') {
      await post('settings', {
        language: state.localeChoice,
        onboarding_complete: true,
      });
      await refresh({ preserveLocale: true });
      return;
    }
    if (action === 'backup-choose-directory') return await chooseBackupDirectory();
    if (action === 'backup-copy-key') {
      const text = $('#backup-recovery-key')?.value;
      if (!text) throw new Error(t('backup.keyUnavailable'));
      await navigator.clipboard.writeText(text);
      return toast(t('backup.copied'));
    }
    if (action === 'backup-enable-auto') return await enableAutoBackup();
    if (action === 'backup-enable-existing') {
      const confirmed = window.confirm(t('backup.reuseKeyConfirm'));
      if (!confirmed) return;
      await window.qoneDesktop.enableAutoBackup(true);
      await loadBackupStatus();
      return toast(t('backup.enabled'));
    }
    if (action === 'backup-disable') {
      await window.qoneDesktop.setBackupEnabled(false);
      await loadBackupStatus();
      return toast(t('backup.disabled'));
    }
    if (action === 'backup-now') {
      if (!window.qoneDesktop) throw new Error(t('backup.desktopOnly'));
      const result = await window.qoneDesktop.backupNow();
      if (result.canceled) return;
      showDialog(
        t('backup.createdTitle'),
        `<p>${e(t('backup.createdAt', { path: result.path }))}</p>
         <label>${e(t('backup.recoveryKey'))}<textarea id="backup-recovery-key" readonly rows="4">${e(result.recoveryKey)}</textarea></label>
         ${recoveryQrMarkup(result)}
         <div class="dialog-actions"><button class="button primary" type="button" data-action="backup-copy-key">${e(t('backup.copyKey'))}</button></div>
         <p class="fine-print">${e(t('backup.noKeyWarning'))}</p>`,
      );
      if (!state.data.settings.onboarding_complete) render();
      return;
    }
    if (action === 'backup-inspect') {
      if (!window.qoneDesktop) throw new Error(t('backup.desktopOnly'));
      const result = await window.qoneDesktop.inspectBackup();
      if (result.canceled) return;
      showDialog(
        t('backup.restoreTitle'),
        `<p>${e(t('backup.restoreBody', {
          date: result.metadata?.created_at
            ? formatDate(result.metadata.created_at, {
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })
            : t('common.unknown'),
        }))}</p>
         <form id="restore-key-form" class="form-stack">
           <label>${e(t('backup.recoveryKey'))}<textarea name="recovery_key" rows="4" required autocomplete="off" placeholder="Q1-..."></textarea></label>
           <div class="dialog-actions"><button class="button primary" type="submit">${e(t('backup.restore'))}</button></div>
         </form>`,
      );
      return;
    }
    if (action === 'support-preview' || action === 'support-export') {
      if (!window.qoneDesktop) throw new Error(t('support.desktopOnly'));
      if (action === 'support-export') {
        const result = await window.qoneDesktop.exportSupportPackage();
        if (result.canceled) return;
        toast(t('support.exported', { path: result.path }));
        return;
      }
      const support = await window.qoneDesktop.previewSupportPackage();
      showDialog(
        t('support.previewTitle'),
        `<p>${e(t('support.previewBody'))}</p>
         <pre class="support-preview">${e(JSON.stringify(support, null, 2))}</pre>
         <div class="dialog-actions">
           <button class="button primary" type="button" data-action="support-export">${e(t('support.export'))}</button>
         </div>`,
      );
      return;
    }
    if (action === 'update-check') {
      if (!window.qoneDesktop?.checkForUpdates) throw new Error(t('update.unavailable'));
      state.update = await window.qoneDesktop.checkForUpdates();
      renderUpdateIntoPage();
      return;
    }
    if (action === 'update-download') {
      if (!window.qoneDesktop?.downloadUpdate) throw new Error(t('update.unavailable'));
      state.update = await window.qoneDesktop.downloadUpdate();
      renderUpdateIntoPage();
      return;
    }
    if (action === 'update-install') {
      if (!window.qoneDesktop?.installUpdate) throw new Error(t('update.unavailable'));
      await window.qoneDesktop.installUpdate();
      return;
    }
    if (action === 'update-open-download') {
      if (!window.qoneDesktop?.openUpdateDownload) throw new Error(t('update.unavailable'));
      await window.qoneDesktop.openUpdateDownload('update');
      return;
    }
    if (action === 'update-open-rollback') {
      if (!window.qoneDesktop?.openUpdateDownload) throw new Error(t('update.unavailable'));
      await window.qoneDesktop.openUpdateDownload('rollback');
      return;
    }
    if (action === 'model-download') {
      if (!window.qoneDesktop) throw new Error(t('settings.rulesReady'));
      state.model = await window.qoneDesktop.downloadModel();
      if (state.data.settings.onboarding_complete) renderModelIntoPage();
      else render();
      return;
    }
    if (action === 'model-cancel') {
      if (!window.qoneDesktop) throw new Error(t('settings.rulesReady'));
      state.model = await window.qoneDesktop.cancelModelDownload();
      if (state.data.settings.onboarding_complete) renderModelIntoPage();
      else render();
      return;
    }
    if (action === 'model-remove') {
      if (!window.qoneDesktop) throw new Error(t('settings.rulesReady'));
      if (!window.confirm(t('model.remove'))) return;
      state.model = await window.qoneDesktop.removeModel();
      if (state.data.settings.onboarding_complete) renderModelIntoPage();
      else render();
      return;
    }
  } catch (error) {
    toast(messageFor(error), true);
  } finally {
    state.busy = false;
  }
}

document.addEventListener('click', (event) => {
  const route = event.target.closest('[data-route]');
  if (route) {
    event.preventDefault();
    location.hash = route.dataset.route;
    return;
  }
  const action = event.target.closest('[data-action]');
  if (action) {
    event.preventDefault();
    void handleAction(action.dataset.action, action);
  }
});

document.addEventListener('change', (event) => {
  if (event.target.matches('[data-task-id]')) void handleTaskChange(event.target);
});

document.addEventListener('submit', handleSubmit);

window.addEventListener('hashchange', () => {
  if (!state.data) return;
  render();
  $('#main').focus();
});

$('#consumer-dialog').addEventListener('click', (event) => {
  if (event.target === $('#consumer-dialog')) closeDialog();
});

async function start() {
  try {
    await loadMessages();
    if (window.qoneDesktop?.onModelStatus) {
      window.qoneDesktop.onModelStatus((status) => {
        state.model = status;
        if (state.data?.settings.onboarding_complete) renderModelIntoPage();
        else if (state.data && state.onboardingStep === 3) render();
        if (status.phase === 'installed' && status.service_active) {
          schedulePlannerPoll(0);
        }
      });
    }
    if (window.qoneDesktop?.onUpdateStatus) {
      window.qoneDesktop.onUpdateStatus((status) => {
        state.update = status;
        if (state.data?.settings.onboarding_complete && state.route === 'settings') {
          renderUpdateIntoPage();
        }
      });
    }
    state.locale = browserLocale();
    state.localeChoice = state.locale;
    setLocale(state.locale);
    renderLoading();
    await refresh();
    schedulePlannerPoll(0);
  } catch (error) {
    renderFailure(messageFor(error));
  }
}

function renderTodayOnly() {
  const current = $('#main');
  if (!current || state.route !== 'today') return;
  current.innerHTML = renderToday();
}

void start();
