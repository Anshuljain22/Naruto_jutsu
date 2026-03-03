// Generate a unique session ID for this visitor so each person gets
// their own independent gesture + effect state on the backend.
const SESSION_ID = crypto.randomUUID();

// If hosting frontend on Vercel and backend elsewhere, change this to your backend URL:
const BACKEND_URL = 'https://goldie22-jutsu-backend.hf.space';

const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const canvas = document.getElementById('video-canvas');
const ctx = canvas.getContext('2d');
const videoPlaceholder = document.getElementById('video-placeholder');
const hudBox = document.getElementById('ar-hud');
const hudText = document.getElementById('hud-text');

// Jutsu sound
const jutsuAudio = new Audio(`${BACKEND_URL}/naurtoi.m4a`);
jutsuAudio.volume = 0.85;
let jutsuWasActive = false;

// Internal state
let videoStream = null;   // MediaStream from getUserMedia
let videoEl = null;   // hidden <video> element driving the capture loop
let captureActive = false;  // controls the frame-sending loop
let pollingInterval = null;

// Helper: adds ngrok bypass header + session ID to every request
function apiFetch(path, options = {}) {
    const headers = {
        'ngrok-skip-browser-warning': '1',
        'X-Session-ID': SESSION_ID,
        ...(options.headers || {}),
    };
    return fetch(`${BACKEND_URL}${path}`, { ...options, headers });
}

// ---------------------------------------------------------------------------
// Start button — request user's webcam, start capture loop
// ---------------------------------------------------------------------------
startBtn.addEventListener('click', async () => {
    try {
        startBtn.disabled = true;
        startBtn.textContent = 'Starting...';

        // Ask for webcam access
        videoStream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
            audio: false,
        });

        // Create hidden video element to draw from
        videoEl = document.createElement('video');
        videoEl.srcObject = videoStream;
        videoEl.playsInline = true;
        await videoEl.play();

        // Size canvas to match video
        canvas.width = videoEl.videoWidth || 1280;
        canvas.height = videoEl.videoHeight || 720;

        // Show canvas, hide placeholder
        videoPlaceholder.style.display = 'none';
        canvas.style.display = 'block';

        startBtn.textContent = 'Start Camera';
        stopBtn.disabled = false;

        // Start sending frames to backend
        captureActive = true;
        captureLoop();

        // Start polling for jutsu status (HUD + cards)
        startPolling();

    } catch (err) {
        console.error('Failed to start camera:', err);
        startBtn.disabled = false;
        startBtn.textContent = 'Start Camera';
        if (err.name === 'NotAllowedError') {
            alert('Camera permission denied. Please allow camera access and try again.');
        } else {
            alert('Could not access your camera: ' + err.message);
        }
    }
});

// ---------------------------------------------------------------------------
// Stop button
// ---------------------------------------------------------------------------
stopBtn.addEventListener('click', () => {
    captureActive = false;
    stopPolling();

    if (videoStream) {
        videoStream.getTracks().forEach(t => t.stop());
        videoStream = null;
    }

    canvas.style.display = 'none';
    videoPlaceholder.style.display = 'flex';
    hudBox.style.display = 'none';
    clearActiveCards();

    startBtn.disabled = false;
    stopBtn.disabled = true;

    // Reset canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
});

// ---------------------------------------------------------------------------
// Frame capture loop — draw video → canvas → send to backend → display result
// ---------------------------------------------------------------------------
let _lastFrameTime = performance.now();
let _fps = 0;
// Separate off-screen canvas for capturing raw frames to send to server
const captureCanvas = document.createElement('canvas');
const captureCtx = captureCanvas.getContext('2d');

async function captureLoop() {
    if (!captureActive || !videoEl) return;

    // FPS counter (drawn over whatever is currently on the visible canvas)
    const now = performance.now();
    _fps = Math.round(1000 / (now - _lastFrameTime));
    _lastFrameTime = now;
    ctx.fillStyle = 'rgba(0,0,0,0.45)';
    ctx.fillRect(8, 8, 90, 22);
    ctx.fillStyle = '#00ff88';
    ctx.font = '13px monospace';
    ctx.fillText(`${_fps} fps ↑`, 12, 24);

    // Draw webcam onto offscreen canvas for sending to server
    captureCanvas.width = canvas.width;
    captureCanvas.height = canvas.height;
    captureCtx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

    captureCanvas.toBlob(async (blob) => {
        if (!blob) {
            // Canvas wasn't ready — try again next frame
            if (captureActive) setTimeout(captureLoop, 100);
            return;
        }
        if (!captureActive) return;

        try {
            const resp = await fetch(`${BACKEND_URL}/api/process_frame`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'image/jpeg',
                    'ngrok-skip-browser-warning': '1',
                    'X-Session-ID': SESSION_ID,
                },
                body: await blob.arrayBuffer(),
            });

            if (resp.ok) {
                const processedBlob = await resp.blob();
                const url = URL.createObjectURL(processedBlob);
                const img = new Image();
                img.onload = () => {
                    if (captureActive) {
                        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    }
                    URL.revokeObjectURL(url);
                    if (captureActive) requestAnimationFrame(captureLoop);
                };
                img.onerror = () => {
                    URL.revokeObjectURL(url);
                    if (captureActive) requestAnimationFrame(captureLoop);
                };
                img.src = url;
            } else {
                console.warn('process_frame returned', resp.status);
                if (captureActive) requestAnimationFrame(captureLoop);
            }
        } catch (e) {
            console.warn('Frame send error:', e);
            if (captureActive) setTimeout(captureLoop, 200);
        }
    }, 'image/jpeg', 0.75);
}
// ---------------------------------------------------------------------------
// Status polling (HUD + card highlights)
// ---------------------------------------------------------------------------
function startPolling() {
    if (pollingInterval) return;
    pollingInterval = setInterval(async () => {
        try {
            const resp = await apiFetch('/api/status');
            const data = await resp.json();
            updateHUD(data);
            updateLibraryCards(data.current_jutsu, data.status_text);
        } catch (e) { /* ignore */ }
    }, 200);
}

function stopPolling() {
    if (pollingInterval) { clearInterval(pollingInterval); pollingInterval = null; }
}

function updateHUD(data) {
    const isActive = data.status_text && data.status_text.includes('ACTIVE');

    if (isActive && !jutsuWasActive) {
        jutsuAudio.currentTime = 0;
        jutsuAudio.play().catch(e => console.warn('Audio blocked:', e));
        jutsuWasActive = true;
    } else if (!isActive && jutsuWasActive) {
        jutsuAudio.pause();
        jutsuAudio.currentTime = 0;
        jutsuWasActive = false;
    }

    if (!data.status_text || data.status_text === 'Ready') {
        hudBox.style.display = 'none';
        return;
    }
    hudBox.style.display = 'block';
    hudText.innerText = data.status_text;
    hudBox.className = 'hud-box';
    if (data.status_text.includes('FOCUSING')) {
        hudBox.classList.add('hud-focusing');
    } else if (isActive) {
        hudBox.classList.add('hud-active');
    }
}

function updateLibraryCards(currentJutsu, statusText) {
    clearActiveCards();
    if (!currentJutsu) return;
    const card = document.getElementById(`card-${currentJutsu}`);
    if (!card) return;
    card.classList.add('active');
    if (statusText && statusText.includes('ACTIVE')) {
        card.style.transform = 'translateX(-15px) scale(1.05)';
        card.style.boxShadow = '0 0 20px rgba(255, 51, 102, 0.5)';
    }
}

function clearActiveCards() {
    document.querySelectorAll('.jutsu-card').forEach(card => {
        card.classList.remove('active');
        card.style.transform = '';
        card.style.boxShadow = '';
    });
}
