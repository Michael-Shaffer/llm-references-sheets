document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const stopButton = document.getElementById('stop-button');
    
    let chatHistory = [];
    let controller = null;

    // Auto-resize textarea
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Handle Enter key
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!messageInput.disabled) chatForm.requestSubmit();
        }
    });

    // Handle Stop button
    stopButton.addEventListener('click', () => {
        if (controller) {
            controller.abort();
            controller = null;
            stopButton.disabled = true;
            messageInput.disabled = false;
            messageInput.focus();
            appendMessage('System', 'Generation stopped by user.');
        }
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        // 1. Setup UI
        messageInput.value = '';
        messageInput.style.height = 'auto';
        messageInput.disabled = true;
        stopButton.disabled = false;

        // Remove welcome message if present
        const welcome = document.querySelector('.welcome-container');
        if (welcome) welcome.remove();

        // 2. Add User Message
        appendMessage('user', message);
        chatHistory.push({ role: 'user', content: message });

        // 3. Create Bot Message Placeholder
        const botContentDiv = appendMessage('bot', '');
        let botText = '';

        // 4. Send Request
        controller = new AbortController();
        
        try {
            console.log('[DEBUG] Sending request to /api/chat');
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages: chatHistory }),
                signal: controller.signal
            });

            if (!response.ok) throw new Error(`Server Error: ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.content) {
                                botText += data.content;
                                botContentDiv.innerHTML = marked.parse(botText);
                                hljs.highlightAll();
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            }
                        } catch (e) {
                            console.error('Error parsing chunk:', e);
                        }
                    }
                }
            }

            chatHistory.push({ role: 'assistant', content: botText });

        } catch (err) {
            if (err.name === 'AbortError') {
                console.log('Request aborted');
            } else {
                console.error('Chat Error:', err);
                botContentDiv.innerHTML += `<br><em style="color:red">Error: ${err.message}</em>`;
            }
        } finally {
            controller = null;
            stopButton.disabled = true;
            messageInput.disabled = false;
            messageInput.focus();
        }
    });

    function appendMessage(role, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = `${role}-message-content`;
        contentDiv.innerHTML = role === 'user' ? escapeHTML(text) : marked.parse(text);
        
        msgDiv.appendChild(contentDiv);
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return contentDiv;
    }

    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag]));
    }
});

