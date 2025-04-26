let typingInterval;
let typingEl;
let latencies = [];
let statsEl;

async function sendMessage() {
  const input   = document.getElementById("user-input");
  const message = input.value.trim();
  if (!message) return;

  appendMessage(message, "user");
  input.value    = "";
  input.disabled = true;

  showTypingIndicator();

  const startTime = performance.now();

  try {
    const res = await fetch("/chat", {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ message })
    });
    if (!res.ok) throw new Error("Network response was not ok");
    const data = await res.json();

    const endTime = performance.now();
    recordLatency(endTime - startTime);

    hideTypingIndicator();
    appendMessage(data.reply || "Hmm … I couldn’t generate a reply.", "bot");
  } catch (err) {
    const endTime = performance.now();
    recordLatency(endTime - startTime);

    hideTypingIndicator();
    appendMessage("Sorry, I couldn’t reach the server.", "bot");
    console.error(err);
  } finally {
    input.disabled = false;
    input.focus();
  }
}

function recordLatency(latency) {
  latencies.push(latency);
  const avg = latencies.reduce((sum, t) => sum + t, 0) / latencies.length;
  if (statsEl) {
    statsEl.textContent = 
      `Response time: ${latency.toFixed(0)} ms (avg: ${avg.toFixed(0)} ms)`;
  }
}

function showTypingIndicator() {
  const chatWin = document.getElementById("chat-window");
  typingEl = document.createElement("div");
  typingEl.classList.add("chat-message", "bot", "typing");
  typingEl.textContent = "Typing";
  chatWin.appendChild(typingEl);
  chatWin.scrollTop = chatWin.scrollHeight;

  let dotCount = 0;
  typingInterval = setInterval(() => {
    dotCount = (dotCount + 1) % 4;
    typingEl.textContent = "Typing" + ".".repeat(dotCount);
    chatWin.scrollTop = chatWin.scrollHeight;
  }, 500);
}

function hideTypingIndicator() {
  clearInterval(typingInterval);
  if (typingEl) {
    typingEl.remove();
    typingEl = null;
  }
}

function appendMessage(text, sender) {
  const chatWin   = document.getElementById("chat-window");
  const messageEl = document.createElement("div");
  messageEl.classList.add("chat-message", sender);
  messageEl.textContent = text;
  chatWin.appendChild(messageEl);
  chatWin.scrollTop = chatWin.scrollHeight;
}

function checkEnter(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

const WELCOME = "Hi there! I'm CarList Assistant—your guide to finding and buying cars. How can I help you today?";

window.addEventListener("DOMContentLoaded", () => {
  // Insert a stats bar above the chat window
  statsEl = document.createElement("div");
  statsEl.id = "latency-stats";
  statsEl.style.cssText = "font-size:0.9em; color:#666; margin:8px 0;";
  const chatWin = document.getElementById("chat-window");
  chatWin.parentNode.insertBefore(statsEl, chatWin);

  // Show the welcome message
  appendMessage(WELCOME, "bot");
  document.getElementById("user-input").focus();
});
