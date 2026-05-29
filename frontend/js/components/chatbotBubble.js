import { apiPost } from "../api.js";
import { state } from "../state.js";

const FAQS = [
    "¿Cuáles son los 10 siniestros con mayor riesgo?",
    "Genera un resumen ejecutivo de los casos críticos",
    "¿Qué proveedores concentran más alertas?",
    "¿Por qué SIN-1 fue marcado con alto riesgo?",
];

function appendMsg(container, role, text) {
    const item = document.createElement("div");
    item.className = `chat-msg ${role}`;
    item.textContent = text;
    container.appendChild(item);
    container.scrollTop = container.scrollHeight;
}

async function ask(question) {
    const body = { question, profile: state.currentProfile || "demo_jurado" };
    const res = await apiPost("/agent/query", body);
    return res?.answer || "No pude responder en este momento.";
}

export function initChatbotBubble() {
    const root = document.getElementById("chatbot-bubble-root");
    if (!root) return;

    root.innerHTML = `
        <button id="chatbot-toggle" class="chatbot-toggle" aria-label="Abrir chat" title="Asistente Miraclex IA">
            <img class="chatbot-logo-btn" src="/logo/logo.svg" onerror="this.onerror=null;this.src='/logo/logo.png'" alt="Miraclex" width="36" height="36">
        </button>
        <div id="chatbot-panel" class="chatbot-panel" style="display:none;">
            <div class="chatbot-head" style="display:flex;align-items:center;gap:10px;">
                <img class="chatbot-logo-head" src="/logo/logo.svg" onerror="this.onerror=null;this.src='/logo/logo.png'" alt="Miraclex" width="28" height="28" style="border-radius:6px;">
                <span>Asistente Miraclex IA</span>
            </div>
            <div class="chatbot-faqs" id="chatbot-faqs"></div>
            <div class="chatbot-body" id="chatbot-body"></div>
            <div class="chatbot-input-wrap">
                <input id="chatbot-input" class="chatbot-input" placeholder="Pregunta por un siniestro (ej: SIN-3)" />
                <button id="chatbot-send" class="btn btn-primary btn-sm">Enviar</button>
            </div>
        </div>
    `;

    const toggle = document.getElementById("chatbot-toggle");
    const panel = document.getElementById("chatbot-panel");
    const faqs = document.getElementById("chatbot-faqs");
    const body = document.getElementById("chatbot-body");
    const input = document.getElementById("chatbot-input");
    const send = document.getElementById("chatbot-send");

    FAQS.forEach((q) => {
        const b = document.createElement("button");
        b.className = "chatbot-faq-btn";
        b.textContent = q;
        b.onclick = async () => {
            appendMsg(body, "user", q);
            appendMsg(body, "bot", "Analizando...");
            const last = body.lastElementChild;
            const ans = await ask(q);
            last.textContent = ans;
        };
        faqs.appendChild(b);
    });

    toggle.addEventListener("click", () => {
        if (panel.classList.contains("active")) {
            panel.classList.remove("active");
            panel.classList.add("closing");
            setTimeout(() => {
                panel.style.display = "none";
                panel.classList.remove("closing");
            }, 250);
        } else {
            panel.style.display = "flex";
            panel.classList.remove("closing");
            panel.classList.add("active");
            setTimeout(() => input?.focus(), 350);
        }
    });

    send.addEventListener("click", async () => {
        const q = (input.value || "").trim();
        if (!q) return;
        input.value = "";
        appendMsg(body, "user", q);
        appendMsg(body, "bot", "Analizando...");
        const last = body.lastElementChild;
        const ans = await ask(q);
        last.textContent = ans;
    });

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") send.click();
    });
}
