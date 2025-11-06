// Conversation Management State
const STORAGE_KEY = "chatbot-conversation-id";
let conversationId = window.localStorage.getItem(STORAGE_KEY);
let conversations = [];
let currentConversation = null;

// DOM Elements
const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const messageTemplate = document.getElementById("message-template");
const conversationItemTemplate = document.getElementById("conversation-item-template");
const conversationsList = document.getElementById("conversations-list");
const conversationTitle = document.getElementById("conversation-title");
const newConversationBtn = document.getElementById("new-conversation-btn");
const editTitleBtn = document.getElementById("edit-title-btn");
const exportBtn = document.getElementById("export-btn");
const shareBtn = document.getElementById("share-btn");
const deleteBtn = document.getElementById("delete-btn");
const conversationSearch = document.getElementById("conversation-search");
const exportModal = document.getElementById("export-modal");
const shareModal = document.getElementById("share-modal");

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
  await loadConversations();
  if (conversationId) {
    await switchConversation(conversationId);
  } else {
    await createNewConversation();
  }
});

// Load all conversations
async function loadConversations() {
  try {
    const response = await fetch("/api/conversations");
    if (response.ok) {
      const data = await response.json();
      conversations = data.conversations || [];
      renderConversationsList(conversations);
    }
  } catch (error) {
    console.error("Failed to load conversations:", error);
  }
}

// Render conversations list
function renderConversationsList(conversationsToRender) {
  conversationsList.innerHTML = "";
  conversationsToRender.forEach((conv) => {
    const clone = conversationItemTemplate.content.cloneNode(true);
    const item = clone.querySelector(".conversation-item");
    item.dataset.conversationId = conv.conversation_id;
    item.querySelector(".conversation-item-title").textContent = conv.title;
    item.querySelector(".conversation-item-preview").textContent =
      conv.preview || "No messages yet";
    item.querySelector(".conversation-item-meta").textContent = formatDate(conv.updated_at);

    if (conv.conversation_id === conversationId) {
      item.classList.add("active");
    }

    item.addEventListener("click", () => switchConversation(conv.conversation_id));
    conversationsList.appendChild(clone);
  });
}

// Create new conversation
async function createNewConversation() {
  try {
    const response = await fetch("/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: null }),
    });

    if (response.ok) {
      const data = await response.json();
      conversationId = data.conversation_id;
      currentConversation = data;
      window.localStorage.setItem(STORAGE_KEY, conversationId);
      conversationTitle.textContent = data.title;
      chatWindow.innerHTML = "";
      await loadConversations();
    }
  } catch (error) {
    console.error("Failed to create conversation:", error);
  }
}

// Switch to a conversation
async function switchConversation(id) {
  try {
    const response = await fetch(`/api/conversations/${id}`);
    if (response.ok) {
      currentConversation = await response.json();
      conversationId = id;
      window.localStorage.setItem(STORAGE_KEY, conversationId);
      conversationTitle.textContent = currentConversation.title;
      chatWindow.innerHTML = "";
      await loadConversations();
      // TODO: Load and display messages for this conversation
    }
  } catch (error) {
    console.error("Failed to switch conversation:", error);
  }
}

// Rename conversation
async function renameConversation(newTitle) {
  if (!conversationId || !newTitle.trim()) return;

  try {
    const response = await fetch(`/api/conversations/${conversationId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: newTitle.trim() }),
    });

    if (response.ok) {
      const data = await response.json();
      currentConversation = data;
      conversationTitle.textContent = data.title;
      await loadConversations();
    }
  } catch (error) {
    console.error("Failed to rename conversation:", error);
  }
}

// Delete conversation
async function deleteConversation() {
  if (!conversationId) return;
  if (!confirm("Are you sure you want to delete this conversation?")) return;

  try {
    const response = await fetch(`/api/conversations/${conversationId}`, {
      method: "DELETE",
    });

    if (response.ok || response.status === 204) {
      conversationId = null;
      window.localStorage.removeItem(STORAGE_KEY);
      await loadConversations();
      await createNewConversation();
    }
  } catch (error) {
    console.error("Failed to delete conversation:", error);
  }
}

// Export conversation
async function exportConversation(format) {
  if (!conversationId) return;

  try {
    const response = await fetch(`/api/conversations/${conversationId}/export?format=${format}`);
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `conversation_${conversationId.substring(0, 8)}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      exportModal.style.display = "none";
    }
  } catch (error) {
    console.error("Failed to export conversation:", error);
    alert("Failed to export conversation");
  }
}

// Share conversation
async function generateShareLink() {
  if (!conversationId) return;

  try {
    const response = await fetch(`/api/conversations/${conversationId}/share`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expires_in_days: 7 }),
    });

    if (response.ok) {
      const data = await response.json();
      const shareLinkInput = document.getElementById("share-link-input");
      const shareLinkContainer = document.getElementById("share-link-container");
      const fullUrl = `${window.location.origin}${data.share_url}`;
      shareLinkInput.value = fullUrl;
      shareLinkContainer.style.display = "block";
    }
  } catch (error) {
    console.error("Failed to generate share link:", error);
    alert("Failed to generate share link");
  }
}

// Search conversations
async function searchConversations(query) {
  if (!query.trim()) {
    renderConversationsList(conversations);
    return;
  }

  try {
    const response = await fetch(`/api/conversations/search?query=${encodeURIComponent(query)}&limit=20`);
    if (response.ok) {
      const data = await response.json();
      renderConversationsList(data.conversations);
    }
  } catch (error) {
    console.error("Failed to search conversations:", error);
  }
}

// Message handling
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

const formatDate = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

// Event Listeners
newConversationBtn.addEventListener("click", createNewConversation);

editTitleBtn.addEventListener("click", () => {
  const isEditable = conversationTitle.contentEditable === "true";
  if (isEditable) {
    conversationTitle.contentEditable = "false";
    renameConversation(conversationTitle.textContent);
    editTitleBtn.textContent = "✏️";
  } else {
    conversationTitle.contentEditable = "true";
    conversationTitle.focus();
    editTitleBtn.textContent = "💾";
  }
});

conversationTitle.addEventListener("blur", () => {
  if (conversationTitle.contentEditable === "true") {
    conversationTitle.contentEditable = "false";
    renameConversation(conversationTitle.textContent);
    editTitleBtn.textContent = "✏️";
  }
});

conversationTitle.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && conversationTitle.contentEditable === "true") {
    e.preventDefault();
    conversationTitle.blur();
  }
});

exportBtn.addEventListener("click", () => {
  exportModal.style.display = "flex";
});

shareBtn.addEventListener("click", () => {
  shareModal.style.display = "flex";
});

deleteBtn.addEventListener("click", deleteConversation);

conversationSearch.addEventListener("input", (e) => {
  searchConversations(e.target.value);
});

// Export modal handlers
document.querySelectorAll('[data-format]').forEach((btn) => {
  btn.addEventListener("click", (e) => {
    const format = e.target.dataset.format;
    exportConversation(format);
  });
});

document.getElementById("close-export-modal").addEventListener("click", () => {
  exportModal.style.display = "none";
});

document.getElementById("generate-share-link").addEventListener("click", generateShareLink);

document.getElementById("copy-share-link").addEventListener("click", () => {
  const shareLinkInput = document.getElementById("share-link-input");
  shareLinkInput.select();
  document.execCommand("copy");
  alert("Link copied to clipboard!");
});

document.getElementById("close-share-modal").addEventListener("click", () => {
  shareModal.style.display = "none";
});

// Close modals when clicking outside
[exportModal, shareModal].forEach((modal) => {
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.style.display = "none";
    }
  });
});

// Chat form submission
chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  if (!conversationId) {
    await createNewConversation();
  }

  appendMessage("user", message);
  chatInput.value = "";
  setLoadingState(true);

  try {
    const response = await fetch("/api/chat", {
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
    await loadConversations(); // Refresh list to update message counts
  } catch (error) {
    console.error(error);
    appendMessage("assistant", `Something went wrong: ${error.message || error}`);
  } finally {
    setLoadingState(false);
    chatInput.focus();
  }
});
