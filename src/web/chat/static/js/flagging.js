/**
 * Attach the flag button to a bot message.
 */
export function attachFlagButton(botActionsElement, payloadProvider) {
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

    btn.addEventListener('click', () => {
        // Hide flag button
        btn.style.display = 'none';
        
        // Show feedback form
        const reasonContainer = createFeedbackForm(botActionsElement, payloadProvider);
        botActionsElement.appendChild(reasonContainer);
    });
}

function createFeedbackForm(container, payloadProvider) {
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

    reasonContainer.appendChild(promptText);
    reasonContainer.appendChild(reasonInput);
    reasonContainer.appendChild(submitBtn);

    submitBtn.addEventListener('click', async () => {
        const reasonText = reasonInput.value.trim();
        reasonInput.disabled = true;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending...';

        const payload = payloadProvider(reasonText);

        try {
            // Mock submission for now, or replace with real endpoint
            // const res = await fetch('/api/flag', { method: 'POST', body: JSON.stringify(payload) ... });
            console.log('[DEBUG] Flag Payload:', payload);
            await new Promise(r => setTimeout(r, 500)); // Simulate network

            reasonContainer.innerHTML = 'Feedback submitted. Thank you!';
        } catch (err) {
            console.warn('Flagging failed', err);
            reasonContainer.innerHTML = 'Submission failed. Saved locally (check console).';
        }
    });

    return reasonContainer;
}

export function buildFlagPayload(chatHistory, userText, botText, reason) {
    return {
        timestamp: new Date().toISOString(),
        path: window.location.pathname,
        userText,
        botText,
        flagReason: reason,
        chatHistorySnapshot: chatHistory.slice(-5), // Last 5 messages
        ua: navigator.userAgent
    };
}

