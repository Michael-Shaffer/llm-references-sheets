function debounce(func, delay) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const stopButton = document.getElementById('stop-button');
    let chatHistory = [];
    let currentAbortController = null;
    let isRequestInProgress = false; // New flag to track request status
    let retrievedContext = null;

    function autoResize(textarea) {
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, 120);
        textarea.style.height = newHeight + 'px';
        const wrapper = textarea.closest('.message-input-wrapper');

        if (textarea.scrollHeight > 120) {
            textarea.style.overflowY = 'auto';
        } else {
            textarea.style.overflowY = 'hidden';
        }

        if (newHeight > 30) {
            wrapper.style.alignItems = 'flex-end';
        } else {
            wrapper.style.alignItems = 'center';
        }
    }

    messageInput.addEventListener('input', () => autoResize(messageInput));

    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!isRequestInProgress) {
                chatForm.dispatchEvent(new Event('submit'));
            }
        }
    });

    chatForm.addEventListener('submit', handleFormSubmit);

    stopButton.addEventListener('click', () => {
        if (currentAbortController) {
            currentAbortController.abort();
            console.log('Chatbot generation stopped by user.');
            stopButton.disabled = true;
            addMessageToChat('Bot generation stopped.', 'bot-info');
        }
    });

    async function handleFormSubmit(e) {
        e.preventDefault();

        if (isRequestInProgress) {
            console.log('Request already in progress. Please wait.');
            return;
        }

        const messageText = messageInput.value.trim();
        if (!messageText) return;

        const welcomeContainer = document.querySelector('.welcome-container');
        if (welcomeContainer) {
            welcomeContainer.remove();
        }

        chatHistory.push({ role: 'user', content: messageText });
        addMessageToChat(escapeHTML(messageText), 'user');

        messageInput.value = '';
        autoResize(messageInput);

        messageInput.disabled = true;
        stopButton.disabled = false;
        isRequestInProgress = true;

        currentAbortController = new AbortController();

        await getBotResponse(chatHistory, currentAbortController.signal);
    }

    function addMessageToChat(text, sender) {
        const messageContainer = document.createElement('div');
        messageContainer.classList.add('message', `${sender}-message`);

        const contentDiv = document.createElement('div');
        contentDiv.classList.add(`${sender}-message-content`);
        if (text) {
            contentDiv.innerHTML = text;
        }

        const actionsDiv = document.createElement('div');
        actionsDiv.classList.add('message-actions')

        const messageBody = document.createElement('div');
        messageBody.classList.add('message-body');
        messageBody.appendChild(contentDiv);
        messageBody.appendChild(actionsDiv);

        messageContainer.appendChild(messageBody);
        chatMessages.appendChild(messageContainer);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return { content : contentDiv, actions : actionsDiv }; // (unchanged) callers rely on this
    }

    function escapeHTML(str) {
        return str.replace(/[&<>"']/g, (m) => (
            { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m]
        ));
    }

    function applyHighlighting(element) {
        element.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }

    function attachFlagButton(botContentElement, botActionsElement, payloadProvider) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'flag-btn';
        btn.title = 'Flag this response';
        btn.setAttribute('aria-label', 'Flag this response');

        btn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M6 3v18H4V3h2zm2 0h12l-2 4L22 11H8V3z"></path>
        </svg>
        `;

        botActionsElement.appendChild(btn);

        btn.addEventListener('click', async () => {
            btn.style.display = 'none';

            const reasonContainer = document.createElement('div');
            reasonContainer.className = 'flag-reason-container';

            const promptText = document.createElement('p');
            promptText.textContent = 'Please briefly explain why this response is inaccurate:';

            const reasonInput = document.createElement('textarea');
            reasonInput.className = 'flag-reason-input';
            reasonInput.rows = 3;
            reasonInput.placeholder = 'e.g., The content provided is outdated or the response misinterprets the data.';

            const submitBtn = document.createElement('button');
            submitBtn.className = 'flag-reason-submit-btn';
            submitBtn.textContent = 'Submit';

            reasonContainer.appendChild(promptText)
            reasonContainer.appendChild(reasonInput)
            reasonContainer.appendChild(submitBtn)

            botActionsElement.appendChild(reasonContainer)

            submitBtn.addEventListener('click', async () => {
                const reasonText = reasonInput.value.trim();

                reasonInput.disabled = true;
                submitBtn.disabled = true;
                submitBtn.textContent = 'Sending...';

                // The payloadProvider function is called with the reasonText
                const payload = payloadProvider(reasonText)

                try {
                    const res = await fetch(`${window.location.origin}/polaris/api/flag`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    })

                    if (!res.ok) {
                        throw new Error(`Server returned ${res.status}`)
                    }

                    reasonContainer.innerHTML = 'Feedback submitted. Thank you !';
                } catch (err) {
                    console.warn('Flagging failed, saving locally.', err);
                    reasonContainer.innerHTML = 'Submission failed. Saved locally.';

                    try {
                        const key = 'polarisFlags';
                        const existing = JSON.parse(localStorage.getItem(key) || '[]');
                        existing.push(payload);
                        localStorage.setItem(key, JSON.stringify(existing));
                    } catch (_) {}

                    try {
                        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `polaris-flag-${Date.now()}.json`;
                        a.style.display = 'none';
                        document.body.appendChild(a);
                        a.click();
                        URL.revokeObjectURL(url);
                        a.remove();
                    } catch (_) {}
                }
            });
        });
    }

    // Corrected to accept 'context' and 'reason'
    function buildFlagPayload({ userText, botText, context, reason }) {
        return {
            timestamp: new Date().toISOString(),
            path: window.location.pathname + window.location.hash,
            userText,
            botText,
            retrievedContext: context,
            flagReason: reason,
            chatHistorySnapshot: chatHistory.slice(-20), // include recent context (tune as desired)
            ua: navigator.userAgent
        };
    }

    function finalizeMessage(botContentElement, botActionsElement, lastUserMsg, botText) {
        botContentElement.innerHTML = marked.parse(botText);
        applyHighlighting(botContentElement);
        chatHistory.push({ role: 'assistant', content: botText });
        attachFlagButton(botContentElement, botActionsElement, (reason) => buildFlagPayload({
            userText: lastUserMsg,
            botText: botText,
            context: retrievedContext,
            reason: reason
        }));
    }

    async function getBotResponse(currentChatHistory, signal) {
        const { content: botContentElement, actions: botActionsElement } = addMessageToChat('', 'bot');
        let fullBotResponse = '';
        retrievedContext = null;

        const debouncedUpdate = debounce((content) => {
            botContentElement.innerHTML = marked.parse(content);
            applyHighlighting(botContentElement);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 50);

        const lastUserMsg = currentChatHistory.slice().reverse().find(msg => msg.role === 'user')?.content || '';

        try {
            const apiUrl = `${window.location.origin}/api/chat`;
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: currentChatHistory,
                    stream: true,
                }),
                signal: signal
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
                throw new Error(`Network response was not ok: ${response.status} - ${errorData.message || response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n').filter(line => line.trim() !== '');

                for (const line of lines) {
                    if (line.startsWith('data:')) {
                        const json_str = line.substring(5).trim();

                        if (json_str === '[DONE]') {
                            console.log('Stream finished by [DONE] signal.');
                            reader.releaseLock();
                            finalizeMessage(botContentElement, botActionsElement, lastUserMsg, fullBotResponse);
                            return;
                        }

                        try {
                            const data = JSON.parse(json_str);
                            if(data.type == 'retrieved_context') {
                                retrievedContext = data.data;
                                console.log('Retrieved context:', retrievedContext);
                                continue;
                            }
                            if (data.choices && data.choices.length > 0) {
                                const delta = data.choices[0].delta.content || '';
                                fullBotResponse += delta;
                                debouncedUpdate(fullBotResponse);
                            }
                        } catch (parseError) {
                            console.error('Error parsing JSON from stream:', parseError, 'Line:', json_str);
                        }
                    }
                }
            }

            // Natural end without [DONE]
            stopButton.disabled = true;
            finalizeMessage(botContentElement, botActionsElement, lastUserMsg, fullBotResponse);
        } catch (error) {
            if (error.name === 'AbortError') {
                console.warn('Fetch aborted by user.');
                if (fullBotResponse) {
                    finalizeMessage(botContentElement, botActionsElement, lastUserMsg, fullBotResponse + ' *(stopped)*');
                }
            } else {
                console.error('Error fetching bot response:', error);
                const errorMsg = fullBotResponse 
                    ? fullBotResponse + ` (Error: ${error.message})`
                    : `Sorry, an error occurred: ${error.message}`;
                const displayText = fullBotResponse 
                    ? fullBotResponse + `<br><br>Sorry, an error occurred: ${error.message}`
                    : errorMsg;
                botContentElement.innerHTML = fullBotResponse ? marked.parse(displayText) : displayText;
                applyHighlighting(botContentElement);
                chatHistory.push({ role: 'assistant', content: errorMsg });
                attachFlagButton(botContentElement, botActionsElement, (reason) => buildFlagPayload({
                    userText: lastUserMsg,
                    botText: errorMsg,
                    context: retrievedContext,
                    reason: reason
                }));
            }
            stopButton.disabled = true;
        } finally {
            currentAbortController = null;
            messageInput.disabled = false;
            isRequestInProgress = false;
            messageInput.focus();
        }
    }

    messageInput.focus();
});