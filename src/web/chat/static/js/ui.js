import { escapeHTML } from './utils.js';
import { attachFlagButton, buildFlagPayload } from './flagging.js';

const chatMessages = document.getElementById('chat-messages');

/**
 * Append a message to the chat window.
 * Returns { contentDiv, actionsDiv }
 */
export function appendMessage(role, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = `${role}-message-content`;
    
    // Initial content
    if (role === 'user') {
        contentDiv.innerHTML = escapeHTML(text);
    } else {
        contentDiv.innerHTML = marked.parse(text);
    }
    
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'message-actions';

    const msgBody = document.createElement('div');
    msgBody.style.width = '100%';
    msgBody.appendChild(contentDiv);
    msgBody.appendChild(actionsDiv);

    msgDiv.appendChild(msgBody);
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
    
    return { contentDiv, actionsDiv };
}

export function updateBotMessage(contentDiv, text) {
    contentDiv.innerHTML = marked.parse(text);
    applyHighlighting(contentDiv);
    scrollToBottom();
}

export function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

export function applyHighlighting(element) {
    element.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
}

export function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight) + 'px';
}

/**
 * Finalize a bot message (add flag button, etc.)
 */
export function finalizeMessage(contentDiv, actionsDiv, text, chatHistory, lastUserMsg) {
    updateBotMessage(contentDiv, text);
    
    // Attach flag button
    attachFlagButton(actionsDiv, (reason) => 
        buildFlagPayload(chatHistory, lastUserMsg, text, reason)
    );
}

