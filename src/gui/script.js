function sendMessage() {
  const input = document.getElementById("user-input");
  const message = input.value.trim();
  if (message === "") return;

  appendMessage(message, "user");

  // Simulated bot response
  setTimeout(() => {
    const botReply = getBotResponse(message);
    appendMessage(botReply, "bot");
  }, 500);

  input.value = "";
}

function appendMessage(text, sender) {
  const chatWindow = document.getElementById("chat-window");
  const messageEl = document.createElement("div");
  messageEl.classList.add("chat-message", sender);
  messageEl.textContent = text;
  chatWindow.appendChild(messageEl);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function getBotResponse(userMessage) {
  // Basic responses, customize as needed
  const msg = userMessage.toLowerCase();
  if (msg.includes("hello")) return "testt";
  if (msg.includes("how are you")) return "I'm just code, but I'm doing fine!";
  if (msg.includes("bye")) return "testt";
  return "testt testt";
}

function checkEnter(event) {
  if (event.key === "Enter") {
    sendMessage();
  }
}
