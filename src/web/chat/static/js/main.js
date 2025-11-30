import { autoResize, appendMessage, updateBotMessage, finalizeMessage } from './ui.js';
import { streamChat } from './api.js';
import { generateUUID } from './utils.js';

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const stopButton = document.getElementById('stop-button');
    
    // Session Management
    let sessionId = localStorage.getItem('polaris_session_id');
    if (!sessionId) {
        sessionId = generateUUID();
        localStorage.setItem('polaris_session_id', sessionId);
    }
    console.log('[DEBUG] Session ID:', sessionId);

    let chatHistory = [];
    let controller = null;

    // Initialize input
    messageInput.addEventListener('input', () => autoResize(messageInput));

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!messageInput.disabled) chatForm.requestSubmit();
        }
    });

    stopButton.addEventListener('click', () => {
        if (controller) {
            controller.abort();
            controller = null;
            stopButton.disabled = true;
            messageInput.disabled = false;
            messageInput.focus();
            appendMessage('bot', '_(Generation stopped by user)_');
        }
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        // 1. Setup UI state
        messageInput.value = '';
        messageInput.style.height = 'auto';
        messageInput.disabled = true;
        stopButton.disabled = false;

        const welcome = document.querySelector('.welcome-container');
        if (welcome) welcome.remove();

        // 2. Add User Message
        appendMessage('user', message);
        // Note: We only store local history for UI convenience or flagging; 
        // the backend now maintains the canonical history.
        chatHistory.push({ role: 'user', content: message });

        // 3. Prepare Bot Message
        const { contentDiv, actionsDiv } = appendMessage('bot', '');
        let botText = '';

        // 4. Stream Response
        controller = new AbortController();
        
        try {
            // Updated: Send session_id and message only
            const stream = await streamChat(sessionId, message, controller.signal);

            for await (const chunk of stream) {
                botText += chunk;
                updateBotMessage(contentDiv, botText);
            }

            chatHistory.push({ role: 'assistant', content: botText });
            finalizeMessage(contentDiv, actionsDiv, botText, chatHistory, message);

        } catch (err) {
            if (err.name === 'AbortError') {
                console.log('Request aborted');
            } else {
                console.error('Chat Error:', err);
                contentDiv.innerHTML += `<br><br><em style="color: #ff6b6b">Error: ${err.message}</em>`;
            }
        } finally {
            controller = null;
            stopButton.disabled = true;
            messageInput.disabled = false;
            messageInput.focus();
        }
    });
});
