/**
 * LegalTax AI - Interactive Client Application
 * Modeled after NUTECH AI interface aesthetic with low-latency streaming simulation,
 * clean output (no distracting line-by-line inline bracket citations),
 * verified end-of-response statutory PDF links, and native browser Web Speech API.
 */

// Application State
let currentLanguage = "English";
let attachedNoticeFile = null;
let isGenerating = false;
let activeAbortController = null;
let speechRecognition = null;
let isRecordingVoice = false;
let currentUtterance = null;
let lastTaxResult = null;

// 2x2 Benchmark Prompts matching Reference Image Format
const PROMPT_LIBRARY = {
  English: [
    {
      title: "What are the requirements for company name reservation?",
      query: "What are the requirements for reservation of a company name under Companies Regulations 2024?"
    },
    {
      title: "What is the minimum tax on turnover for companies?",
      query: "What is the minimum tax on turnover for companies under Section 113 of Income Tax Ordinance 2001?"
    },
    {
      title: "📅 What is the Section 127 FBR appeal deadline for notice received today?",
      query: "I received an FBR assessment order under Section 122 today. What is the statutory limitation deadline to file an appeal before Commissioner (Appeals) under Section 127, and what is the procedure?"
    },
    {
      title: "What is the salary tax liability on 48 Lakhs annual package?",
      query: "Calculate tax on annual salary of 48 Lakhs under Finance Act 2024."
    }
  ],
  "Roman Urdu": [
    {
      title: "Company ka naam reserve karwane ka legal tareeqa kya hai?",
      query: "Company ka naam reserve karwane ke kya rules aur regulatory procedure hain?"
    },
    {
      title: "Minimum turnover tax kin companies par laagu hota hai?",
      query: "Section 113 ke tehat minimum turnover tax kin companies par lagta hai aur iska rate kya hai?"
    },
    {
      title: "📅 FBR Section 127 notice ke khilaf appeal ki aakhri tareekh kab hai?",
      query: "Mujhe aaj FBR assessment notice mila hai. Section 127 ke tehat Commissioner Appeals ke pas appeal karne ki aakhri date aur deadline kya hai?"
    },
    {
      title: "48 Lakh salana salary par tax calculation kitna hoga?",
      query: "48 Lakhs salana salary par tax calculate karein."
    }
  ],
  "Urdu (اردو)": [
    {
      title: "کمپنی کا نام محفوظ کرنے کے لیے کیا طریقہ کار ہے؟",
      query: "کمپنیز ریگولیشنز 2024 کے تحت کمپنی کا نام محفوظ کرنے کی کیا شرائط ہیں؟"
    },
    {
      title: "سیکشن 113 کے تحت کم از کم ٹرن اوور ٹیکس کی شرائط؟",
      query: "کم سے کم ٹرن اوور ٹیکس کن شرائط پر لاگو ہوتا ہے؟"
    },
    {
      title: "📅 ایف بی آر نوٹس کے خلاف سیکشن 127 اپیل کی آخری تاریخ؟",
      query: "مجھے آج ایف بی آر کا اسسمنٹ آرڈر ملا ہے۔ سیکشن 127 کے تحت کمشنر اپیلز کے پاس اپیل دائر کرنے کی قانونی مدت اور آخری تاریخ کیا ہے؟"
    },
    {
      title: "48 لاکھ سالانہ تنخواہ پر ٹیکس کٹوتی کا حساب؟",
      query: "48 لاکھ سالانہ تنخواہ پر ٹیکس کا حساب لگائیں۔"
    }
  ]
};

// DOM Elements
const sidebar = document.getElementById("sidebar");
const mobileMenuBtn = document.getElementById("mobileMenuBtn");
const languageSelect = document.getElementById("languageSelect");
const themeToggleCheckbox = document.getElementById("themeToggleCheckbox");
const newChatBtn = document.getElementById("newChatBtn");
const heroContainer = document.getElementById("heroContainer");
const heroPromptGrid = document.getElementById("heroPromptGrid");
const chatStream = document.getElementById("chatStream");
const chatScrollArea = document.getElementById("chatScrollArea");
const queryPillForm = document.getElementById("queryPillForm");
const userQueryInput = document.getElementById("userQueryInput");
const noticeFileInput = document.getElementById("noticeFileInput");
const attachmentPreviewPill = document.getElementById("attachmentPreviewPill");
const attachedThumbImg = document.getElementById("attachedThumbImg");
const attachedFileNameTxt = document.getElementById("attachedFileNameTxt");
const removeAttBtn = document.getElementById("removeAttBtn");
const voiceMicBtn = document.getElementById("voiceMicBtn");
const speechRecordingBanner = document.getElementById("speechRecordingBanner");
const stopGenerationBtn = document.getElementById("stopGenerationBtn");
const sendQueryBtn = document.getElementById("sendQueryBtn");

// Tab Elements
const tabQnaBtn = document.getElementById("tabQnaBtn");
const tabTaxBtn = document.getElementById("tabTaxBtn");
const tabQna = document.getElementById("tabQna");
const tabTax = document.getElementById("tabTax");

// Tax Studio Elements
const taxStudioForm = document.getElementById("taxStudioForm");
const taxpayerNameInput = document.getElementById("taxpayerName");
const entityCategorySelect = document.getElementById("entityCategory");
const taxYearSelect = document.getElementById("taxYear");
const grossRevenueInput = document.getElementById("grossRevenue");
const grossRevenueHint = document.getElementById("grossRevenueHint");
const deductionsInput = document.getElementById("deductionsInput");
const advanceTaxInput = document.getElementById("advanceTaxInput");
const taxResultsBox = document.getElementById("taxResultsBox");
const kpiGross = document.getElementById("kpiGross");
const kpiCategory = document.getElementById("kpiCategory");
const kpiBase = document.getElementById("kpiBase");
const kpiSlab = document.getElementById("kpiSlab");
const kpiSuper = document.getElementById("kpiSuper");
const kpiSuperRate = document.getElementById("kpiSuperRate");
const kpiAdvance = document.getElementById("kpiAdvance");
const kpiNet = document.getElementById("kpiNet");
const kpiEffective = document.getElementById("kpiEffective");
const memoContent = document.getElementById("memoContent");
const btnDownloadOfficialPdf = document.getElementById("btnDownloadOfficialPdf");

// ==============================================================================
// INITIALIZATION & THEME SETUP
// ==============================================================================
document.addEventListener("DOMContentLoaded", () => {
  initLucide();
  initTheme();
  initSpeechRecognition();
  updatePromptsForLanguage(currentLanguage);
});

function initLucide() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function initTheme() {
  const savedTheme = localStorage.getItem("legaltax_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  themeToggleCheckbox.checked = savedTheme === "light";
}

themeToggleCheckbox.addEventListener("change", () => {
  const next = themeToggleCheckbox.checked ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("legaltax_theme", next);
});

if (mobileMenuBtn) {
  mobileMenuBtn.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });
}

// ==============================================================================
// TAB SWITCHING LOGIC
// ==============================================================================
tabQnaBtn.addEventListener("click", () => switchTab("tabQna"));
tabTaxBtn.addEventListener("click", () => switchTab("tabTax"));

function switchTab(targetId) {
  if (targetId === "tabQna") {
    tabQnaBtn.classList.add("active");
    tabTaxBtn.classList.remove("active");
    tabQna.classList.add("active");
    tabTax.classList.remove("active");
  } else {
    tabTaxBtn.classList.add("active");
    tabQnaBtn.classList.remove("active");
    tabTax.classList.add("active");
    tabQna.classList.remove("active");
  }
  initLucide();
}

// ==============================================================================
// LANGUAGE SWITCHER & NEW CONVERSATION (WINDOW RESET)
// ==============================================================================
languageSelect.addEventListener("change", (e) => {
  currentLanguage = e.target.value;
  resetConversation();
  updatePromptsForLanguage(currentLanguage);
});

newChatBtn.addEventListener("click", () => {
  resetConversation();
});

// Keyboard Shortcut: Ctrl + N for New Conversation
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "n") {
    e.preventDefault();
    resetConversation();
  }
});

function resetConversation() {
  stopSpeech();
  abortGeneration();

  chatStream.innerHTML = "";
  heroContainer.style.display = "block";
  attachedNoticeFile = null;
  attachmentPreviewPill.style.display = "none";
  userQueryInput.value = "";
  initLucide();
}

function updatePromptsForLanguage(lang) {
  const prompts = PROMPT_LIBRARY[lang] || PROMPT_LIBRARY["English"];
  heroPromptGrid.innerHTML = "";

  prompts.forEach((item) => {
    const card = document.createElement("div");
    card.className = "hero-prompt-card";
    card.innerHTML = `
      <div class="hpc-left">
        <i data-lucide="search"></i>
        <span>${item.title}</span>
      </div>
      <i data-lucide="arrow-up-right" class="hpc-arrow"></i>
    `;
    card.addEventListener("click", () => {
      submitQuery(item.query);
    });
    heroPromptGrid.appendChild(card);
  });

  initLucide();
}

// ==============================================================================
// NOTICE FILE ATTACHMENT
// ==============================================================================
noticeFileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) {
    attachedNoticeFile = file;
    attachedFileNameTxt.textContent = file.name;

    const reader = new FileReader();
    reader.onload = (event) => {
      attachedThumbImg.src = event.target.result;
      attachmentPreviewPill.style.display = "flex";
    };
    reader.readAsDataURL(file);
  }
});

removeAttBtn.addEventListener("click", () => {
  attachedNoticeFile = null;
  attachmentPreviewPill.style.display = "none";
  noticeFileInput.value = "";
});

// ==============================================================================
// CHAT SUBMISSION & STREAMING SIMULATION
// ==============================================================================
queryPillForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = userQueryInput.value.trim();
  if (!text && !attachedNoticeFile) return;

  submitQuery(text);
});

function submitQuery(text) {
  if (isGenerating) return;

  // Hide 2x2 Hero Prompt Grid
  heroContainer.style.display = "none";

  // Append User Message Bubble
  appendUserBubble(text, attachedNoticeFile);

  // Prepare Payload
  const formData = new FormData();
  formData.append("query", text);
  formData.append("language", currentLanguage);
  if (attachedNoticeFile) {
    formData.append("notice_image", attachedNoticeFile);
  }

  // Clear input fields
  userQueryInput.value = "";
  attachedNoticeFile = null;
  attachmentPreviewPill.style.display = "none";
  noticeFileInput.value = "";

  // Execute Assistant Query
  executeAssistantQuery(formData);
}

function appendUserBubble(text, file) {
  const row = document.createElement("div");
  row.className = "msg-wrapper user";

  let imgTag = "";
  if (file) {
    imgTag = `<div style="font-size: 0.78rem; color: #60a5fa; margin-bottom: 6px;">📸 Attached Notice: ${file.name}</div>`;
  }

  row.innerHTML = `
    <div class="msg-body-container">
      <div class="msg-content-card">
        ${imgTag}
        <div>${escapeHtml(text || "(Analyzing attached notice document...)")}</div>
      </div>
    </div>
    <div class="msg-avatar user-av">👤</div>
  `;

  chatStream.appendChild(row);
  scrollToBottom();
}

async function executeAssistantQuery(formData) {
  isGenerating = true;
  toggleGeneratingUi(true);

  activeAbortController = new AbortController();

  // Assistant Bubble Container (Matching Reference Image)
  const assistantRow = document.createElement("div");
  assistantRow.className = "msg-wrapper assistant";

  assistantRow.innerHTML = `
    <div class="msg-avatar assistant-av">
      <i data-lucide="scale"></i>
    </div>
    <div class="msg-body-container">
      <div class="msg-author-tag">
        LEGAL AI <span>Legal Assistant</span>
      </div>
      <div class="msg-content-card">
        <div class="loading-state">
          <div class="pulsing-wave">
            <span class="wave-dot"></span>
            <span class="wave-dot"></span>
            <span class="wave-dot"></span>
          </div>
          <span class="loading-hint-text">Researching statutory provisions & generating response...</span>
        </div>
        <div class="answer-text" style="display: none;"></div>
        <div class="sources-box-slot" style="display: none;"></div>
      </div>
      <div class="msg-action-controls" style="display: none;">
        <button class="btn-msg-action btn-copy-act" title="Copy answer">
          <i data-lucide="copy"></i> <span>Copy</span>
        </button>
        <button class="btn-msg-action btn-listen-act" title="Listen to response (Text-to-Speech)">
          <i data-lucide="volume-2"></i> <span>Listen</span>
        </button>
      </div>
    </div>
  `;

  chatStream.appendChild(assistantRow);
  scrollToBottom();
  initLucide();

  const loadingState = assistantRow.querySelector(".loading-state");
  const answerText = assistantRow.querySelector(".answer-text");
  const sourcesBoxSlot = assistantRow.querySelector(".sources-box-slot");
  const actionControls = assistantRow.querySelector(".msg-action-controls");
  const copyBtn = assistantRow.querySelector(".btn-copy-act");
  const listenBtn = assistantRow.querySelector(".btn-listen-act");
  const cardBody = assistantRow.querySelector(".msg-content-card");

  try {
    let accumulatedText = "";
    let pendingCitations = [];
    let streamSuccess = false;

    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        body: formData,
        signal: activeAbortController.signal,
      });

      if (response.ok && response.body) {
        streamSuccess = true;
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        let currentEvent = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop();

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const rawData = line.slice(6).trim();
              if (!rawData) continue;
              try {
                const parsed = JSON.parse(rawData);

                if (currentEvent === "meta") {
                  // Prepend notice summary if available
                  if (parsed.notice_summary) {
                    const noticeDiv = document.createElement("div");
                    noticeDiv.style.cssText = "background: rgba(16, 185, 129, 0.08); border-left: 4px solid #10b981; padding: 8px 12px; border-radius: 4px; font-size: 0.84rem; color: #a7f3d0; margin-bottom: 12px;";
                    noticeDiv.innerHTML = `<b>📑 Extracted Notice Details:</b><br>${escapeHtml(parsed.notice_summary)}`;
                    cardBody.insertBefore(noticeDiv, loadingState);
                  }

                  // Prepend tax card if calculation was performed
                  if (parsed.calculation_result) {
                    const taxCardDiv = document.createElement("div");
                    taxCardDiv.innerHTML = formatTaxCardHtml(parsed.calculation_result);
                    cardBody.insertBefore(taxCardDiv, loadingState);
                  }

                  // Prepend compliance calendar deadlines if detected
                  if (parsed.calendar_events && parsed.calendar_events.length > 0) {
                    const calCardDiv = document.createElement("div");
                    calCardDiv.innerHTML = formatCalendarDeadlineHtml(parsed.calendar_events);
                    cardBody.insertBefore(calCardDiv, loadingState);
                  }

                  // Prepend official government portal link if detected
                  if (parsed.portal_info) {
                    const portalDiv = document.createElement("div");
                    portalDiv.innerHTML = formatOfficialPortalHtml(parsed.portal_info);
                    cardBody.insertBefore(portalDiv, loadingState);

                    if (parsed.portal_info.auto_open && parsed.portal_info.url) {
                      setTimeout(() => {
                        window.open(parsed.portal_info.url, "_blank");
                      }, 500);
                    }
                  }

                  // Store verified citations for rendering at the bottom after answer text is streamed
                  if (parsed.citations && parsed.citations.length > 0) {
                    pendingCitations = parsed.citations;
                  }

                  initLucide();
                  scrollToBottom();
                } else if (currentEvent === "token") {
                  if (parsed.text) {
                    accumulatedText += parsed.text;
                    if (accumulatedText.trim().length > 0) {
                      loadingState.style.display = "none";
                      answerText.style.display = "block";
                      try {
                        answerText.innerHTML = marked.parse(accumulatedText);
                      } catch (mErr) {
                        answerText.innerText = accumulatedText;
                      }
                      scrollToBottom();
                    }
                  }
                } else if (currentEvent === "done") {
                  loadingState.style.display = "none";
                  answerText.style.display = "block";
                  // Render verified statutory sources at the very bottom after answer text
                  if (pendingCitations && pendingCitations.length > 0) {
                    sourcesBoxSlot.style.display = "block";
                    sourcesBoxSlot.className = "verified-sources-box";
                    let citHtml = `
                      <div class="vs-header">
                        <i data-lucide="book-open"></i>
                        <span>Verified Statutory Sources (${pendingCitations.length})</span>
                      </div>
                      <div class="source-chips-row">
                    `;
                    pendingCitations.forEach((cit) => {
                      citHtml += `
                        <span class="source-page-link" title="Statutory Reference: ${cit.section} (Page ${cit.page})">
                          🏛️ ${cit.filename} — ${cit.section} (Page ${cit.page})
                        </span>
                      `;
                    });
                    citHtml += `</div>`;
                    sourcesBoxSlot.innerHTML = citHtml;
                  }
                  actionControls.style.display = "flex";
                  initLucide();
                  scrollToBottom();
                }
              } catch (e) {
                console.warn("SSE parse warning", e);
              }
            }
          }
        }
      }
    } catch (streamErr) {
      if (streamErr.name === "AbortError") throw streamErr;
      console.warn("Stream error, falling back to standard /api/chat", streamErr);
      streamSuccess = false;
    }

    // Fallback to standard /api/chat if streaming was not supported
    if (!streamSuccess) {
      const response = await fetch("/api/chat", {
        method: "POST",
        body: formData,
        signal: activeAbortController.signal,
      });

      if (!response.ok) {
        throw new Error(`Server returned status: ${response.status}`);
      }

      const data = await response.json();
      loadingState.style.display = "none";
      answerText.style.display = "block";

      if (data.notice_summary) {
        const noticeDiv = document.createElement("div");
        noticeDiv.style.cssText = "background: rgba(16, 185, 129, 0.08); border-left: 4px solid #10b981; padding: 8px 12px; border-radius: 4px; font-size: 0.84rem; color: #a7f3d0; margin-bottom: 12px;";
        noticeDiv.innerHTML = `<b>📑 Extracted Notice Details:</b><br>${escapeHtml(data.notice_summary)}`;
        cardBody.insertBefore(noticeDiv, answerText);
      }

      if (data.calculation_result) {
        const taxCardDiv = document.createElement("div");
        taxCardDiv.innerHTML = formatTaxCardHtml(data.calculation_result);
        cardBody.insertBefore(taxCardDiv, answerText);
      }

      if (data.calendar_events && data.calendar_events.length > 0) {
        const calCardDiv = document.createElement("div");
        calCardDiv.innerHTML = formatCalendarDeadlineHtml(data.calendar_events);
        cardBody.insertBefore(calCardDiv, answerText);
      }

      if (data.portal_info) {
        const portalDiv = document.createElement("div");
        portalDiv.innerHTML = formatOfficialPortalHtml(data.portal_info);
        cardBody.insertBefore(portalDiv, answerText);

        if (data.portal_info.auto_open && data.portal_info.url) {
          setTimeout(() => {
            window.open(data.portal_info.url, "_blank");
          }, 500);
        }
      }

      accumulatedText = data.answer || "";
      answerText.innerHTML = marked.parse(accumulatedText);

      if (data.citations && data.citations.length > 0) {
        sourcesBoxSlot.style.display = "block";
        sourcesBoxSlot.className = "verified-sources-box";
        let citHtml = `
          <div class="vs-header">
            <i data-lucide="book-open"></i>
            <span>Verified Statutory Sources (${data.citations.length})</span>
          </div>
          <div class="source-chips-row">
        `;
        data.citations.forEach((cit) => {
          citHtml += `
            <span class="source-page-link" title="Statutory Reference: ${cit.section} (Page ${cit.page})">
              🏛️ ${cit.filename} — ${cit.section} (Page ${cit.page})
            </span>
          `;
        });
        citHtml += `</div>`;
        sourcesBoxSlot.innerHTML = citHtml;
      }
      actionControls.style.display = "flex";
      initLucide();
    }

    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(accumulatedText);
      copyBtn.innerHTML = `<i data-lucide="check"></i> <span>Copied</span>`;
      initLucide();
      setTimeout(() => {
        copyBtn.innerHTML = `<i data-lucide="copy"></i> <span>Copy</span>`;
        initLucide();
      }, 2000);
    });

    listenBtn.addEventListener("click", () => {
      playSpeech(accumulatedText, listenBtn);
    });

  } catch (err) {
    loadingState.style.display = "none";
    answerText.style.display = "block";
    if (err.name === "AbortError") {
      answerText.innerHTML = `<span style="color: #ef4444; font-size: 0.85rem;">Generation paused by user.</span>`;
    } else {
      answerText.innerHTML = `<span style="color: #ef4444; font-size: 0.85rem;">Error: ${err.message}</span>`;
    }
  } finally {
    isGenerating = false;
    toggleGeneratingUi(false);
    activeAbortController = null;
    scrollToBottom();
  }
}

function formatTaxCardHtml(calcRes) {
  const fmt = calcRes.formatted || {};
  const hasSuper = calcRes.super_tax_4c > 0;
  const superBadge = hasSuper
    ? `<span style="background: #ef4444; color: #fff; font-size: 0.72rem; padding: 2px 7px; border-radius: 10px; font-weight: 700;">⚠️ Section 4C Super Tax Applied</span>`
    : "";

  return `
    <div class="chat-tax-card">
      <div class="chat-tax-header">
        <span class="chat-tax-title">🧮 Statutory Tax Computation (${calcRes.tax_year || '2024-2025'})</span>
        ${superBadge}
      </div>
      <div class="chat-tax-grid">
        <div><span class="chat-tax-label">Category:</span> <b style="color: var(--accent-blue);">${calcRes.category}</b></div>
        <div><span class="chat-tax-label">Taxable Income:</span> <b>${fmt.annual_income || '-'}</b></div>
        <div><span class="chat-tax-label">Base Income Tax:</span> <b style="color: var(--accent-amber);">${fmt.base_tax || '-'}</b></div>
        <div><span class="chat-tax-label">Super Tax (4C):</span> <b style="color: ${hasSuper ? 'var(--accent-red)' : 'var(--text-muted)'};">${fmt.super_tax_4c || 'PKR 0'}</b></div>
        <div><span class="chat-tax-label">Total Annual Tax:</span> <b style="color: var(--accent-red);">${fmt.total_annual_tax || '-'}</b></div>
        <div><span class="chat-tax-label">Effective Rate:</span> <b style="color: var(--accent-blue);">${fmt.effective_tax_rate || '-'}</b></div>
      </div>
    </div>
  `;
}

function formatCalendarDeadlineHtml(events) {
  if (!events || events.length === 0) return "";

  let html = `<div class="calendar-deadline-container">`;
  events.forEach((ev) => {
    const daysBadge = ev.days_left !== undefined
      ? (ev.days_left >= 0 ? `${ev.days_left} Days Remaining` : `${Math.abs(ev.days_left)} Days Passed`)
      : `Due: ${ev.display_date}`;

    const gcalUrl = ev.google_calendar_url || "#";

    html += `
      <div class="calendar-deadline-card">
        <div class="cal-header-row">
          <div class="cal-tag">
            <i data-lucide="calendar"></i>
            <span>Statutory Compliance Deadline Alert</span>
          </div>
          <span class="cal-badge-days">⏳ ${escapeHtml(daysBadge)}</span>
        </div>
        <div class="cal-title">${escapeHtml(ev.title)}</div>
        <div class="cal-meta">
          <div><b>Statutory Law:</b> ${escapeHtml(ev.law || 'Pakistani Law')}</div>
          <div><b>Compliance Deadline:</b> <span class="cal-date-highlight">📅 ${escapeHtml(ev.display_date)}</span></div>
          <div>${escapeHtml(ev.description || '')}</div>
        </div>
        <div class="cal-actions-row">
          <a href="${gcalUrl}" target="_blank" rel="noopener noreferrer" class="btn-cal-action btn-cal-gcal" title="Sync this statutory deadline to Google Calendar with 1-click">
            <i data-lucide="calendar-plus"></i>
            <span>Add to Google Calendar</span>
          </a>
        </div>
      </div>
    `;
  });
  html += `</div>`;
  return html;
}

function formatOfficialPortalHtml(portal) {
  if (!portal) return "";

  let stepsHtml = "";
  if (portal.steps && portal.steps.length > 0) {
    stepsHtml = `<div class="portal-steps-list">` +
      portal.steps.map(s => `<div>👉 ${escapeHtml(s)}</div>`).join("") +
      `</div>`;
  }

  return `
    <div class="official-portal-card">
      <div class="portal-header-row">
        <div class="portal-tag">
          <i data-lucide="shield-check"></i>
          <span>Official Verified Portal</span>
        </div>
        <span class="portal-badge-verified">🏛️ ${escapeHtml(portal.authority || 'Government Authority')}</span>
      </div>
      <div class="portal-title">${escapeHtml(portal.name)}</div>
      <div class="portal-meta">
        <div><b>Governing Statute:</b> ${escapeHtml(portal.law || 'Statutory Law')}</div>
        <div style="margin-top: 4px;">${escapeHtml(portal.description || '')}</div>
        ${stepsHtml}
      </div>
      <div style="margin-top: 10px;">
        <a href="${portal.url}" target="_blank" rel="noopener noreferrer" class="btn-portal-open" title="Open official government portal in new tab">
          <i data-lucide="external-link"></i>
          <span>🚀 Open Official Portal in Browser (${escapeHtml(portal.domain)}) ↗</span>
        </a>
      </div>
    </div>
  `;
}

// Stop generation
stopGenerationBtn.addEventListener("click", () => {
  abortGeneration();
});

function abortGeneration() {
  if (activeAbortController) {
    activeAbortController.abort();
  }
  isGenerating = false;
  toggleGeneratingUi(false);
}

function toggleGeneratingUi(generating) {
  if (generating) {
    sendQueryBtn.style.display = "none";
    stopGenerationBtn.style.display = "flex";
  } else {
    sendQueryBtn.style.display = "flex";
    stopGenerationBtn.style.display = "none";
  }
}

function scrollToBottom() {
  chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ==============================================================================
// VOICE INPUT (STT)
// ==============================================================================
function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceMicBtn.style.display = "none";
    return;
  }

  speechRecognition = new SpeechRecognition();
  speechRecognition.continuous = false;
  speechRecognition.interimResults = false;

  speechRecognition.onstart = () => {
    isRecordingVoice = true;
    voiceMicBtn.classList.add("recording");
    speechRecordingBanner.style.display = "flex";
  };

  speechRecognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    userQueryInput.value = userQueryInput.value ? `${userQueryInput.value} ${transcript}` : transcript;
  };

  speechRecognition.onerror = () => {
    stopVoiceRecording();
  };

  speechRecognition.onend = () => {
    stopVoiceRecording();
  };

  voiceMicBtn.addEventListener("click", () => {
    if (isRecordingVoice) {
      speechRecognition.stop();
    } else {
      speechRecognition.lang = currentLanguage === "Urdu (اردو)" ? "ur-PK" : "en-US";
      speechRecognition.start();
    }
  });
}

function stopVoiceRecording() {
  isRecordingVoice = false;
  voiceMicBtn.classList.remove("recording");
  speechRecordingBanner.style.display = "none";
}

// ==============================================================================
// VOICE OUTPUT (TTS READ ALOUD)
// ==============================================================================
function playSpeech(text, btn) {
  if (!("speechSynthesis" in window)) {
    alert("Speech Synthesis is not supported in this browser.");
    return;
  }

  if (window.speechSynthesis.speaking) {
    stopSpeech();
    btn.classList.remove("playing");
    btn.innerHTML = `<i data-lucide="volume-2"></i> <span>Listen</span>`;
    initLucide();
    return;
  }

  const cleanText = text
    .replace(/[#*`_~]/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/🔗/g, "")
    .replace(/📊/g, "");

  currentUtterance = new SpeechSynthesisUtterance(cleanText);
  currentUtterance.rate = 1.0;
  currentUtterance.lang = currentLanguage === "Urdu (اردو)" ? "ur-PK" : "en-US";

  btn.classList.add("playing");
  btn.innerHTML = `<i data-lucide="volume-x"></i> <span>Stop Listening</span>`;
  initLucide();

  currentUtterance.onend = () => {
    btn.classList.remove("playing");
    btn.innerHTML = `<i data-lucide="volume-2"></i> <span>Listen</span>`;
    initLucide();
  };

  currentUtterance.onerror = () => {
    btn.classList.remove("playing");
    btn.innerHTML = `<i data-lucide="volume-2"></i> <span>Listen</span>`;
    initLucide();
  };

  window.speechSynthesis.speak(currentUtterance);
}

function stopSpeech() {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

// ==============================================================================
// TAB 2: CORPORATE & TAX ASSESSMENT STUDIO
// ==============================================================================
grossRevenueInput.addEventListener("input", (e) => {
  const val = parseFloat(e.target.value) || 0;
  if (val >= 10000000) {
    const cr = (val / 10000000).toFixed(2);
    grossRevenueHint.textContent = `PKR ${val.toLocaleString()} (${cr} Crore)`;
  } else if (val >= 100000) {
    const lk = (val / 100000).toFixed(2);
    grossRevenueHint.textContent = `PKR ${val.toLocaleString()} (${lk} Lakh)`;
  } else {
    grossRevenueHint.textContent = `PKR ${val.toLocaleString()}`;
  }
});

taxStudioForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btnComputeTax");
  btn.disabled = true;
  btn.innerHTML = `<span class="wave-dot"></span> Computing Statutory Liabilities...`;

  const payload = {
    taxpayer_name: taxpayerNameInput.value.trim() || "Corporate Client",
    category: entityCategorySelect.value,
    tax_year: taxYearSelect.value,
    gross_revenue: parseFloat(grossRevenueInput.value) || 0,
    deductions: parseFloat(deductionsInput.value) || 0,
    advance_tax: parseFloat(advanceTaxInput.value) || 0,
  };

  try {
    const res = await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Calculation API failed");

    const data = await res.json();
    lastTaxResult = data;
    renderStudioOutput(data);
  } catch (err) {
    alert("Tax computation error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="zap"></i> <span>Compute Statutory Tax & Generate Advisory</span>`;
    initLucide();
  }
});

function renderStudioOutput(data) {
  const calc = data.calculation;
  const fmt = calc.formatted;

  kpiGross.textContent = fmt.annual_income;
  kpiCategory.textContent = calc.category;

  kpiBase.textContent = fmt.base_tax;
  kpiSlab.textContent = calc.slab_description;

  kpiSuper.textContent = fmt.super_tax_4c;
  kpiSuperRate.textContent = `${calc.super_tax_rate_pct}% Tier (> 150M)`;

  kpiAdvance.textContent = `- ${fmt.advance_tax_paid}`;
  kpiNet.textContent = fmt.net_tax_payable;
  kpiEffective.textContent = fmt.effective_tax_rate;

  memoContent.innerHTML = marked.parse(data.advisory_memo);
  taxResultsBox.style.display = "block";
  initLucide();

  taxResultsBox.scrollIntoView({ behavior: "smooth" });
}

btnDownloadOfficialPdf.addEventListener("click", async () => {
  if (!lastTaxResult) return;

  btnDownloadOfficialPdf.disabled = true;
  btnDownloadOfficialPdf.innerHTML = `Generating PDF...`;

  try {
    const res = await fetch("/api/download-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        calc_data: lastTaxResult.calculation,
        advisory_memo: lastTaxResult.advisory_memo,
        taxpayer_name: lastTaxResult.taxpayer_name,
      }),
    });

    if (!res.ok) throw new Error("PDF download failed");

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Tax_Advisory_Memo_${lastTaxResult.taxpayer_name.replace(/\s+/g, "_")}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert("Error downloading PDF: " + err.message);
  } finally {
    btnDownloadOfficialPdf.disabled = false;
    btnDownloadOfficialPdf.innerHTML = `<i data-lucide="download"></i> <span>Download Official PDF Report</span>`;
    initLucide();
  }
});

// ==============================================================================
// TAB SWITCHING (Legal Q&A vs Corporate Tax Studio)
// ==============================================================================
document.querySelectorAll(".nav-tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));

    btn.classList.add("active");
    const targetId = btn.getAttribute("data-target");
    const targetPane = document.getElementById(targetId);
    if (targetPane) {
      targetPane.classList.add("active");
    }
    initLucide();
  });
});
