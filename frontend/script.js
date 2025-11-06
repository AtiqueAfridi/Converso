const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const messageTemplate = document.getElementById("message-template");

const STORAGE_KEY = "chatbot-conversation-id";

let conversationId = window.localStorage.getItem(STORAGE_KEY);
if (!conversationId) {
  conversationId = crypto.randomUUID();
  window.localStorage.setItem(STORAGE_KEY, conversationId);
}

const appendMessage = (role, content, reasoningSteps = []) => {
  const clone = messageTemplate.content.cloneNode(true);
  const messageElement = clone.querySelector(".message");
  messageElement.classList.add(`message-${role}`);
  clone.querySelector(".message-role").textContent = role === "user" ? "You" : "GPT-5";
  clone.querySelector(".message-content").innerHTML = formatContent(content, reasoningSteps);
  chatWindow.appendChild(clone);
  chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: "smooth" });
};

const formatContent = (content, reasoningSteps) => {
  const reasoningHtml = reasoningSteps.length
    ? `<details><summary>Reasoning trace</summary><ol>${reasoningSteps
        .map((step) => `<li>${sanitize(step)}</li>`)
        .join("")}</ol></details>`
    : "";
  return `<p>${sanitize(content)}</p>${reasoningHtml}`;
};

const sanitize = (value) => {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
};

const setLoadingState = (isLoading) => {
  chatInput.disabled = isLoading;
  chatForm.querySelector("button").disabled = isLoading;
  if (isLoading) {
    chatForm.querySelector("button").textContent = "Sending...";
  } else {
    chatForm.querySelector("button").textContent = "Send";
  }
};

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  appendMessage("user", message);
  chatInput.value = "";
  setLoadingState(true);

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message, conversation_id: conversationId }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Request failed");
    }

    const data = await response.json();
    conversationId = data.conversation_id;
    window.localStorage.setItem(STORAGE_KEY, conversationId);
    appendMessage("assistant", data.response, data.reasoning_steps || []);
  } catch (error) {
    console.error(error);
    appendMessage("assistant", `Something went wrong: ${error.message || error}`);
  } finally {
    setLoadingState(false);
    chatInput.focus();
  }
});
