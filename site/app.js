export const translations = {
  zh: {
    skip: "跳到主要内容",
    navHow: "如何工作",
    navPrivacy: "隐私边界",
    navDownload: "下载",
    heroTitle: "把决定，<br><em>落到今天。</em>",
    heroBody:
      "目标、下一步、真实反馈与复盘，放在同一个安静的工作台。Q-One 先给出可执行的规则建议；需要时，再让本地模型参与。",
    heroCta: "查看发布页",
    heroSecondary: "先看隐私边界",
    releaseNote: "1.0 正在开发中；只有通过签名与干净设备验收的安装包才会公开。",
    previewKicker: "今日 · 第 12 天",
    previewGoal: "四周内完成第一个独立项目",
    previewNext: "唯一推荐下一步",
    previewAction: "用 25 分钟写出项目的最小可运行范围",
    previewTime: "25 分钟",
    previewEnergy: "低精力可做",
    previewRule: "本地规则建议 · 无需下载模型",
    previewDone: "完成",
    previewReview: "今晚复盘",
    noteOllama: "模型可选",
    noteOllamaBody: "规则路径始终可用",
    noteLocal: "数据在本地",
    noteLocalBody: "无需账号",
    promiseAccount: "无账号，无云同步",
    promiseOffline: "默认离线也能完成闭环",
    promiseBackup: "备份加密，恢复前先自检",
    promiseOpen: "MIT 开源，无遥测",
    howEyebrow: "A SMALLER LOOP",
    howTitle: "不是再建一个待办箱，<br>而是让每次选择有下文。",
    howBody: "Q-One 把宏大的目标收束成今天能完成的一小步，再用真实记录修正下一次建议。",
    stepGoal: "写清目标",
    stepGoalBody: "先说怎样算完成。目标不必漂亮，验收口径必须清楚。",
    stepAction: "接下下一步",
    stepActionBody: "规则推荐优先，离线可用；采纳后只生成行动，不替你执行。",
    stepFeedback: "登记真实反馈",
    stepFeedbackBody: "区分做了什么、结果如何、哪些仍然未知。",
    stepReview: "留下可复用的复盘",
    stepReviewBody: "不美化过去，不把模型建议当成事实。",
    privacyEyebrow: "YOUR DATA STAYS YOURS",
    privacyTitle: "默认不联网，<br>也不替你上传人生。",
    privacyBody:
      "工作数据库只保存在本机，由操作系统权限保护；可携带备份使用 AES-256-GCM 加密。云端模型和遥测都不是完成目标的必要条件。",
    privacyLink: "在 GitHub 检查实现 →",
    privacyLocalTitle: "本地工作区",
    privacyLocalBody: "目标与记录默认写在本机 SQLite，不要求注册或登录。",
    privacyBackupTitle: "加密备份",
    privacyBackupBody: "恢复密钥与自动备份密钥分离，篡改包会在写入前失败。",
    privacyModelTitle: "模型可控",
    privacyModelBody: "本地模型按需下载并校验；失败时自动回退规则推荐。",
    privacyCloudTitle: "云端需要确认",
    privacyCloudBody: "只有你主动配置并确认内容后，才会向外部服务发起请求。",
    downloadEyebrow: "RELEASE CHANNELS",
    downloadTitle: "稳定版与 Beta<br>分开抵达。",
    downloadBody:
      "下载页只链接 GitHub Releases。每个公开安装包都必须通过系统签名、校验清单和对应平台的干净安装记录。",
    stableTitle: "稳定版",
    stableBody: "面向日常使用；只接收稳定更新通道和签名清单。",
    stableCta: "查看最新发布",
    betaTitle: "公开测试",
    betaBody: "先行验证新功能；问题会分级，数据恢复失败视为发布阻断。",
    betaCta: "浏览全部发布",
    downloadFootnote:
      "Q-One 不会用下载量代替质量验收。若任一平台未签名或仍有 P0/P1 问题，1.0.0 会延期。",
    faqEyebrow: "BEFORE YOU START",
    faqTitle: "几个直白的问题。",
    faqNoModelQ: "没有下载模型，还能用吗？",
    faqNoModelA: "可以。目标、行动、反馈、备份和恢复都能由本地规则完成。",
    faqAccountQ: "需要账号或订阅吗？",
    faqAccountA: "不需要。项目保持 MIT、免费、无账号、无云同步。",
    faqEncryptQ: "工作数据库是加密的吗？",
    faqEncryptA:
      "不是实时数据库加密。工作库依赖操作系统文件权限；备份容器才单独加密。建议开启系统全盘加密。",
    faqLinuxQ: "Linux 如何更新？",
    faqLinuxA: "AppImage 支持签名更新；deb 使用手动更新，并在应用内提示下载位置。",
    footerLine: "本地优先的个人决策工作台。MIT License.",
    footerSource: "源代码",
    footerReleases: "发布记录",
    footerSecurity: "安全说明",
  },
  en: {
    skip: "Skip to main content",
    navHow: "How it works",
    navPrivacy: "Privacy",
    navDownload: "Download",
    heroTitle: "Turn decisions<br><em>into today.</em>",
    heroBody:
      "Goals, the next step, real feedback, and review live in one quiet workspace. Q-One starts with offline rule-based recommendations, then adds a local model only when you need it.",
    heroCta: "View releases",
    heroSecondary: "Read the privacy boundary",
    releaseNote:
      "1.0 is in development. An installer is published only after signing and clean-machine acceptance.",
    previewKicker: "TODAY · DAY 12",
    previewGoal: "Ship a first independent project in four weeks",
    previewNext: "THE ONE NEXT STEP",
    previewAction: "Spend 25 minutes writing the smallest runnable project scope",
    previewTime: "25 MIN",
    previewEnergy: "LOW ENERGY",
    previewRule: "Local rule recommendation · No model download",
    previewDone: "DONE",
    previewReview: "REVIEW TONIGHT",
    noteOllama: "Model optional",
    noteOllamaBody: "Rules always work",
    noteLocal: "Data stays local",
    noteLocalBody: "No account",
    promiseAccount: "No account or cloud sync",
    promiseOffline: "The full loop works offline",
    promiseBackup: "Encrypted backup with preflight checks",
    promiseOpen: "MIT open source, no telemetry",
    howEyebrow: "A SMALLER LOOP",
    howTitle: "Not another inbox of tasks.<br>A decision with a next chapter.",
    howBody:
      "Q-One reduces a large goal to one step you can finish today, then uses real records to improve the next recommendation.",
    stepGoal: "Define the finish line",
    stepGoalBody: "Say what completion means. The goal can be modest; the acceptance criterion cannot be vague.",
    stepAction: "Take the next step",
    stepActionBody: "Rule-based recommendations work offline. Accepting one creates an action; it never executes it for you.",
    stepFeedback: "Record real feedback",
    stepFeedbackBody: "Separate what happened, what resulted, and what remains unknown.",
    stepReview: "Leave a reusable review",
    stepReviewBody: "Do not flatter the past or treat a model's suggestion as fact.",
    privacyEyebrow: "YOUR DATA STAYS YOURS",
    privacyTitle: "Offline by default.<br>Your life is not uploaded.",
    privacyBody:
      "The working database stays on your device under operating-system permissions. Portable backups use AES-256-GCM. Cloud models and telemetry are never required to complete a goal.",
    privacyLink: "Inspect the implementation on GitHub →",
    privacyLocalTitle: "Local workspace",
    privacyLocalBody: "Goals and records default to local SQLite. No registration or login is required.",
    privacyBackupTitle: "Encrypted backup",
    privacyBackupBody: "Recovery and unattended-backup keys are separate; tampered containers fail before any write.",
    privacyModelTitle: "Controlled models",
    privacyModelBody: "Local models download on demand and are verified. Failures fall back to rules.",
    privacyCloudTitle: "Cloud needs consent",
    privacyCloudBody: "An external request happens only after you configure a provider and confirm what will be sent.",
    downloadEyebrow: "RELEASE CHANNELS",
    downloadTitle: "Stable and Beta<br>arrive separately.",
    downloadBody:
      "Downloads link only to GitHub Releases. Every public installer must pass system signing, a checksum manifest, and clean-install records for its platform.",
    stableTitle: "Stable",
    stableBody: "For everyday use; accepts only the stable update channel and signed manifests.",
    stableCta: "View latest release",
    betaTitle: "Public Beta",
    betaBody: "Preview new features. Issues are triaged, and any restore failure blocks release.",
    betaCta: "Browse all releases",
    downloadFootnote:
      "Q-One never substitutes downloads for quality acceptance. If any platform is unsigned or has an open P0/P1, 1.0.0 waits.",
    faqEyebrow: "BEFORE YOU START",
    faqTitle: "A few direct questions.",
    faqNoModelQ: "Does Q-One work without a model download?",
    faqNoModelA: "Yes. Goals, actions, feedback, backup, and restore all work with local rules.",
    faqAccountQ: "Is an account or subscription required?",
    faqAccountA: "No. The project remains MIT-licensed, free, accountless, and without cloud sync.",
    faqEncryptQ: "Is the working database encrypted?",
    faqEncryptA:
      "There is no live database encryption. The working database relies on operating-system permissions; only portable backups are encrypted. Full-disk encryption is recommended.",
    faqLinuxQ: "How do Linux updates work?",
    faqLinuxA: "AppImage supports signed updates. deb uses manual updates and the app shows where to download them.",
    footerLine: "A local-first personal decision workspace. MIT License.",
    footerSource: "Source",
    footerReleases: "Releases",
    footerSecurity: "Security",
  },
};

let language = "zh";

function applyLanguage(next) {
  language = next;
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  for (const node of document.querySelectorAll("[data-i18n]")) {
    const value = translations[language][node.dataset.i18n];
    if (value) node.textContent = value;
  }
  for (const node of document.querySelectorAll("[data-i18n-html]")) {
    const value = translations[language][node.dataset.i18nHtml];
    if (value) node.innerHTML = value;
  }
  toggle.textContent = language === "zh" ? "EN" : "中文";
  toggle.setAttribute(
    "aria-label",
    language === "zh" ? "Switch to English" : "切换到简体中文",
  );
}

if (typeof document !== "undefined") {
  const toggle = document.querySelector("#language-toggle");
  toggle?.addEventListener("click", () => {
    applyLanguage(language === "zh" ? "en" : "zh");
  });
  const preferred =
    typeof navigator === "undefined" ? "zh" : navigator.language.toLowerCase();
  applyLanguage(preferred.startsWith("zh") ? "zh" : "en");
}
