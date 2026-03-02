const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const videoFeed = document.getElementById('video-feed');
const videoPlaceholder = document.getElementById('video-placeholder');
const hudBox = document.getElementById('ar-hud');
const hudText = document.getElementById('hud-text');

let pollingInterval = null;
// Use the same origin the page was served from (works for both localhost and ngrok)
const BACKEND_URL = window.location.origin;

// Jutsu sound — served by Flask from the project root
const jutsuAudio = new Audio(`${BACKEND_URL}/naurtoi.m4a`);
jutsuAudio.volume = 0.85;
let jutsuWasActive = false;

// Wrapper that adds the ngrok browser-warning bypass header (harmless on localhost)
async function apiFetch(path, options = {}) {
    const headers = { 'ngrok-skip-browser-warning': '1', ...(options.headers || {}) };
    return fetch(`${BACKEND_URL}${path}`, { ...options, headers });
}

startBtn.addEventListener('click', async () => {
    try {
        startBtn.disabled = true;
        startBtn.textContent = 'Starting...';

        const response = await apiFetch('/api/start', { method: 'POST' });
        if (!response.ok) throw new Error('API call failed');

        // Wait up to 3 seconds to confirm the engine actually started (camera opened)
        let confirmed = false;
        for (let i = 0; i < 6; i++) {
            await new Promise(r => setTimeout(r, 500));
            const statusRes = await apiFetch('/api/status');
            const data = await statusRes.json();
            if (data.running) { confirmed = true; break; }
        }

        if (!confirmed) {
            // Camera failed to open — reset UI
            startBtn.disabled = false;
            startBtn.textContent = 'Start Camera';
            alert('Could not open camera. Make sure no other app is using it, then try again.');
            return;
        }

        // Engine is running — update UI
        startBtn.textContent = 'Start Camera';
        stopBtn.disabled = false;

        // Show video stream
        videoPlaceholder.style.display = 'none';
        videoFeed.style.display = 'block';
        videoFeed.src = `${BACKEND_URL}/video_feed?t=${new Date().getTime()}`;

        // Start polling for Jutsu status
        startPolling();
    } catch (err) {
        console.error("Failed to start engine:", err);
        startBtn.disabled = false;
        startBtn.textContent = 'Start Camera';
        alert("Could not connect to the Python AR Engine. Is app.py running?");
    }
});

stopBtn.addEventListener('click', async () => {
    try {
        await apiFetch('/api/stop', { method: 'POST' });

        // Update UI
        startBtn.disabled = false;
        stopBtn.disabled = true;

        // Hide stream
        videoFeed.src = "";
        videoFeed.style.display = 'none';
        videoPlaceholder.style.display = 'block';
        hudBox.style.display = 'none';

        // Stop polling
        stopPolling();
        clearActiveCards();

    } catch (err) {
        console.error("Failed to stop engine:", err);
    }
});

function startPolling() {
    if (pollingInterval) return;

    // Poll the status endpoint every 200ms
    pollingInterval = setInterval(async () => {
        try {
            const response = await apiFetch('/api/status');
            const data = await response.json();

            updateHUD(data);
            updateLibraryCards(data.current_jutsu, data.status_text);

        } catch (err) {
            console.error("Polling error:", err);
        }
    }, 200);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

function updateHUD(data) {
    const isActive = data.status_text && data.status_text.includes("ACTIVE");

    // Play sound once when jutsu first becomes ACTIVE
    if (isActive && !jutsuWasActive) {
        jutsuAudio.currentTime = 0;
        jutsuAudio.play().catch(e => console.warn('Audio play blocked:', e));
        jutsuWasActive = true;
    } else if (!isActive && jutsuWasActive) {
        // Jutsu ended — stop audio
        jutsuAudio.pause();
        jutsuAudio.currentTime = 0;
        jutsuWasActive = false;
    }

    if (!data.status_text || data.status_text === "Ready") {
        hudBox.style.display = 'none';
        return;
    }

    hudBox.style.display = 'block';
    hudText.innerText = data.status_text;

    // Reset classes
    hudBox.className = "hud-box";

    if (data.status_text.includes("FOCUSING")) {
        hudBox.classList.add("hud-focusing");
    } else if (isActive) {
        hudBox.classList.add("hud-active");
    }
}

function updateLibraryCards(currentJutsu, statusText) {
    clearActiveCards();

    // current_jutsu comes from backend as e.g., 'shadow_clone', 'rasengan'
    if (currentJutsu) {
        const cardId = `card-${currentJutsu}`;
        const card = document.getElementById(cardId);

        if (card) {
            card.classList.add('active');

            // Add a little pulse animation if it's actively casting
            if (statusText && statusText.includes("ACTIVE")) {
                card.style.transform = "translateX(-15px) scale(1.05)";
                card.style.boxShadow = "0 0 20px rgba(255, 51, 102, 0.5)";
            } else {
                card.style.transform = "";
                card.style.boxShadow = "";
            }
        }
    }
}

function clearActiveCards() {
    const cards = document.querySelectorAll('.jutsu-card');
    cards.forEach(card => {
        card.classList.remove('active');
        card.style.transform = "";
        card.style.boxShadow = "";
    });
}
