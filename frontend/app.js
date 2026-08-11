const API_BASE = (window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1'))
    ? window.location.origin
    : 'https://vybesync-backend-a7yi.onrender.com';

// Session & Platform State
let token = localStorage.getItem('auth_token') || null;
let currentUser = null;
let songsLibrary = [];
let softDeletedSongs = [];
let activeSong = null;
let originalAudio = new Audio();
let instrumentalAudio = new Audio();
let isPlaying = false;
let updateInterval = null;
let animationFrameId = null;

// View Mode Preference
let libraryViewMode = localStorage.getItem('lib_view_mode') || 'grid'; // 'grid' or 'list'
let currentLibTab = 'all'; // 'all', 'playlists', 'tags', 'trash'
let defaultLyricFontSize = parseInt(localStorage.getItem('lyric_font_size')) || 18;

// Looping & Playback state
let isLoopEnabled = false;
let currentPitchSemitones = 0;

function setPitchTranspose(semitones) {
    currentPitchSemitones = semitones;
    const pitchRatio = Math.pow(2, semitones / 12);
    const baseSpeed = parseFloat(document.getElementById('vol-speed').value) || 1.0;
    
    instrumentalAudio.preservesPitch = false;
    originalAudio.preservesPitch = false;
    instrumentalAudio.playbackRate = baseSpeed * pitchRatio;
    originalAudio.playbackRate = baseSpeed * pitchRatio;

    const el = document.getElementById('val-pitch');
    if (el) {
        el.innerText = (semitones > 0 ? `+${semitones}` : `${semitones}`) + ' semitones';
    }

    document.querySelectorAll('.pitch-btn').forEach(btn => {
        if (parseInt(btn.dataset.semi) === semitones) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Dom selectors for main Views
const screens = document.querySelectorAll('.screen');
const navItems = document.querySelectorAll('.nav-item');

// DOM Element Selectors
const songInput = document.getElementById('song-input');
const cassetteTape = document.getElementById('cassette-tape');
const processingOverlay = document.getElementById('processing-overlay');
const progressFill = document.getElementById('progress-fill');
const loadingStatus = document.getElementById('loading-status');
const ejectedCd = document.getElementById('ejected-cd');
const ejectedCdTitle = document.getElementById('ejected-cd-title');
const ejectedCdArtist = document.getElementById('ejected-cd-artist');
const cdEjectTray = document.getElementById('cd-eject-tray');

// Audio visualizer properties
const canvas = document.getElementById('waveform-canvas');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
    if (canvas) {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = 60;
    }
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// Toast notifier helper
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = '<i class="fa-solid fa-circle-info"></i>';
    if (type === 'success') icon = '<i class="fa-solid fa-circle-check"></i>';
    if (type === 'error') icon = '<i class="fa-solid fa-circle-exclamation"></i>';
    if (type === 'process') icon = '<i class="fa-solid fa-arrows-spin fa-spin"></i>';

    toast.innerHTML = `${icon} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.transform = 'translateX(120%)';
        toast.style.opacity = '0';
        toast.style.transition = 'all 0.5s ease';
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

// Initial Platform Hook
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    setupAuthListeners();
    setupEventListeners();
    setupVisualizer();
    setupKeyboardShortcuts();
    checkSession();
});

// Theme Prefs
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.body.className = savedTheme + '-theme';
}

function toggleTheme() {
    if (document.body.classList.contains('dark-theme')) {
        document.body.className = 'light-theme';
        localStorage.setItem('theme', 'light');
        showToast('Scandinavian Light theme enabled', 'success');
    } else {
        document.body.className = 'dark-theme';
        localStorage.setItem('theme', 'dark');
        showToast('Cozy Dark theme enabled', 'success');
    }
}

// Navigation Screen switching
function navigateToView(viewId) {
    // Stop playback if entering other views from player
    if (viewId !== 'player') {
        stopPlayback();
    }

    screens.forEach(s => s.classList.remove('active'));
    navItems.forEach(n => n.classList.remove('active'));

    const screenTarget = document.getElementById(`${viewId}-view`);
    if (screenTarget) screenTarget.classList.add('active');

    const navTarget = document.querySelector(`.nav-item[data-view="${viewId}"]`);
    if (navTarget) navTarget.classList.add('active');

    // Load specific view data
    if (viewId === 'dashboard') {
        loadDashboardStats();
    } else if (viewId === 'library') {
        loadLibrary();
    } else if (viewId === 'stats') {
        renderStatsPage();
    }
}

// Authentication flow
function setupAuthListeners() {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    document.getElementById('to-register').addEventListener('click', () => {
        loginForm.classList.remove('active');
        registerForm.classList.add('active');
    });

    document.getElementById('to-login').addEventListener('click', () => {
        registerForm.classList.remove('active');
        loginForm.classList.add('active');
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        showToast('Authenticating with studio...', 'process');
        try {
            const res = await fetch(`${API_BASE}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok) {
                showToast('Authentication successful!', 'success');
                setSession(data.token, data.user);
            } else {
                showToast(data.message || 'Login failed.', 'error');
            }
        } catch (err) {
            showToast('Connection failed: ' + err.message, 'error');
        }
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('register-name').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;

        showToast('Creating profile...', 'process');
        try {
            const res = await fetch(`${API_BASE}/api/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password })
            });
            const data = await res.json();
            if (res.ok) {
                showToast('Profile created successfully!', 'success');
                setSession(data.token, data.user);
            } else {
                showToast(data.message || 'Registration failed.', 'error');
            }
        } catch (err) {
            showToast('Connection failed: ' + err.message, 'error');
        }
    });

    document.getElementById('logout-btn').addEventListener('click', clearSession);
    document.getElementById('theme-toggle-btn').addEventListener('click', toggleTheme);
}

async function checkSession() {
    if (!token) {
        showAuthScreen();
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/auth/profile`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            currentUser = await res.json();
            showAppInterface();
            navigateToView('dashboard');
        } else {
            clearSession();
        }
    } catch (err) {
        clearSession();
    }
}

function setSession(authToken, user) {
    token = authToken;
    currentUser = user;
    localStorage.setItem('auth_token', authToken);
    showAppInterface();
    navigateToView('dashboard');
}

function clearSession() {
    token = null;
    currentUser = null;
    songsLibrary = [];
    localStorage.removeItem('auth_token');
    stopPlayback();
    showAuthScreen();
}

function showAuthScreen() {
    document.getElementById('app-interface').style.display = 'none';
    document.getElementById('auth-screen').classList.add('active');
}

function showAppInterface() {
    document.getElementById('auth-screen').classList.remove('active');
    document.getElementById('app-interface').style.display = 'flex';
    if (currentUser) {
        document.getElementById('user-display-name').innerText = currentUser.name;
        document.getElementById('avatar-circle').innerText = currentUser.name.charAt(0).toUpperCase();
        document.getElementById('dash-greeting').innerText = `Welcome back, ${currentUser.name}!`;
    }
}

// Sidebar links click
navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const view = item.getAttribute('data-view');
        navigateToView(view);
    });
});

// Event Listeners for Player Control
function setupEventListeners() {
    const eCd = document.getElementById('ejected-cd');
    eCd.addEventListener('click', () => {
        eCd.style.transition = 'all 1.2s cubic-bezier(0.25, 1, 0.5, 1)';
        eCd.style.transform = 'scale(4) rotate(720deg) translateY(-20px)';
        eCd.style.opacity = '0';
        
        setTimeout(() => {
            loadSongIntoPlayer(activeSong);
            navigateToView('player');
            document.getElementById('cd-eject-tray').classList.remove('active');
            eCd.style.transform = '';
            eCd.style.opacity = '';
        }, 1100);
    });

    document.getElementById('generate-btn').addEventListener('click', startGeneration);
    document.getElementById('player-back-btn').addEventListener('click', () => {
        stopPlayback();
        navigateToView('library');
    });

    // Mixer tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            e.target.classList.add('active');
            document.getElementById(`tab-${e.target.dataset.tab}`).classList.add('active');
        });
    });

    // Mix sliders
    const volInst = document.getElementById('vol-instrumental');
    const volVoc = document.getElementById('vol-vocals');
    const volSpeed = document.getElementById('vol-speed');
    const btnLoop = document.getElementById('btn-loop-toggle');

    volInst.addEventListener('input', (e) => {
        instrumentalAudio.volume = e.target.value;
        document.getElementById('val-instrumental').innerText = Math.round(e.target.value * 100) + '%';
    });

    volVoc.addEventListener('input', (e) => {
        originalAudio.volume = e.target.value;
        document.getElementById('val-vocals').innerText = Math.round(e.target.value * 100) + '%';
    });

    volSpeed.addEventListener('input', (e) => {
        const speed = parseFloat(e.target.value);
        const pitchRatio = Math.pow(2, currentPitchSemitones / 12);
        instrumentalAudio.preservesPitch = false;
        originalAudio.preservesPitch = false;
        instrumentalAudio.playbackRate = speed * pitchRatio;
        originalAudio.playbackRate = speed * pitchRatio;
        document.getElementById('val-speed').innerText = speed.toFixed(1) + 'x';
    });

    document.querySelectorAll('.pitch-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const semitones = parseInt(e.target.dataset.semi);
            setPitchTranspose(semitones);
        });
    });

    btnLoop.addEventListener('click', () => {
        isLoopEnabled = !isLoopEnabled;
        instrumentalAudio.loop = isLoopEnabled;
        originalAudio.loop = isLoopEnabled;

        if (isLoopEnabled) {
            btnLoop.innerText = 'DISABLE LOOP';
            btnLoop.classList.add('neon-btn');
            document.getElementById('val-loop').innerText = 'ENABLED';
            showToast('Looping current track enabled', 'success');
        } else {
            btnLoop.innerText = 'ENABLE LOOP';
            btnLoop.classList.remove('neon-btn');
            document.getElementById('val-loop').innerText = 'OFF';
            showToast('Looping disabled', 'info');
        }
    });

    // Transport buttons
    document.getElementById('btn-play').addEventListener('click', togglePlayback);
    document.getElementById('btn-restart').addEventListener('click', restartPlayback);
    document.getElementById('btn-mute').addEventListener('click', toggleMute);
    document.getElementById('btn-favourite').addEventListener('click', toggleFavourite);
    document.getElementById('btn-pin').addEventListener('click', togglePin);
    document.getElementById('btn-download').addEventListener('click', downloadInstrumental);
    document.getElementById('btn-delete').addEventListener('click', sendDeleteRequest);

    // Audio progress seek
    const progressSlider = document.getElementById('playback-progress');
    progressSlider.addEventListener('input', (e) => {
        const val = e.target.value;
        if (instrumentalAudio.duration) {
            const time = (val / 100) * instrumentalAudio.duration;
            instrumentalAudio.currentTime = time;
            originalAudio.currentTime = time;
        }
    });

    // Library page event attachments
    document.getElementById('library-search-input').addEventListener('input', renderLibraryView);
    document.getElementById('toggle-view-btn').addEventListener('click', () => {
        libraryViewMode = libraryViewMode === 'grid' ? 'list' : 'grid';
        localStorage.setItem('lib_view_mode', libraryViewMode);
        document.getElementById('toggle-view-btn').innerHTML = libraryViewMode === 'grid' ? '<i class="fa-solid fa-table-cells"></i>' : '<i class="fa-solid fa-list"></i>';
        renderLibraryView();
    });

    // Library Tabs
    document.querySelectorAll('.lib-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.lib-tab').forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            currentLibTab = e.target.dataset.libtab;
            renderLibraryView();
        });
    });

    // Lyric settings size controls
    const scrollBox = document.getElementById('lyrics-scroll-box');
    document.getElementById('lyric-zoom-in').addEventListener('click', () => {
        defaultLyricFontSize = Math.min(defaultLyricFontSize + 2, 32);
        localStorage.setItem('lyric_font_size', defaultLyricFontSize);
        scrollBox.style.fontSize = defaultLyricFontSize + 'px';
    });

    document.getElementById('lyric-zoom-out').addEventListener('click', () => {
        defaultLyricFontSize = Math.max(defaultLyricFontSize - 2, 12);
        localStorage.setItem('lyric_font_size', defaultLyricFontSize);
        scrollBox.style.fontSize = defaultLyricFontSize + 'px';
    });

    document.getElementById('lyric-fullscreen').addEventListener('click', toggleFullscreenKaraoke);

    // Sizing change inside Settings panel
    const sizeSelect = document.getElementById('settings-lyric-size');
    sizeSelect.value = defaultLyricFontSize + 'px';
    sizeSelect.addEventListener('change', (e) => {
        defaultLyricFontSize = parseInt(e.target.value);
        localStorage.setItem('lyric_font_size', defaultLyricFontSize);
        showToast('Lyric display font size updated', 'success');
    });
}

// Dashboard statistics loader
async function loadDashboardStats() {
    try {
        const res = await fetch(`${API_BASE}/api/songs`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            songsLibrary = await res.json();
            
            // Total created count
            document.getElementById('stat-created-count').innerText = songsLibrary.length;
            
            // Playcount count sum
            const playSum = songsLibrary.reduce((acc, song) => acc + (song.play_count || 0), 0);
            document.getElementById('stat-plays-count').innerText = playSum;

            // Mock storage percentage
            const sizeInMb = songsLibrary.length * 12.5; // Estimating 12.5MB per split
            const storagePct = Math.min(Math.round((sizeInMb / 500) * 100), 100); // 500MB free ceiling
            document.getElementById('stat-storage-pct').innerText = `${storagePct}%`;

            // Continue listening - load first song if available
            const continueBox = document.getElementById('continue-listening-widget');
            continueBox.innerHTML = '';
            if (songsLibrary.length > 0) {
                const latest = songsLibrary[0];
                continueBox.innerHTML = `
                    <div class="cd-item" onclick="loadSongIntoPlayer(${JSON.stringify(latest).replace(/"/g, '&quot;')}); navigateToView('player');">
                        <div class="cd-item-art"><i class="fa-solid fa-compact-disc"></i></div>
                        <div class="cd-item-details">
                            <h4>${latest.title}</h4>
                            <p>${latest.artist || 'Unknown'}</p>
                        </div>
                        <i class="fa-solid fa-play" style="color: var(--primary); margin-left: 12px;"></i>
                    </div>
                `;
            } else {
                continueBox.innerHTML = `<div class="empty-state">No songs created yet. Go to Studio Deck!</div>`;
            }

            // Render Recent Grid (limit 4)
            const recentGrid = document.getElementById('recent-grid');
            recentGrid.innerHTML = '';
            const recentLimit = songsLibrary.slice(0, 4);
            if (recentLimit.length > 0) {
                recentLimit.forEach(song => {
                    const card = document.createElement('div');
                    card.className = 'library-card';
                    card.innerHTML = `
                        <div class="library-card-art" style="background-image: ${song.cover_image ? `url(${API_BASE}${song.cover_image})` : 'none'}">
                            ${!song.cover_image ? '<i class="fa-solid fa-music"></i>' : ''}
                            ${song.pinned ? '<i class="fa-solid fa-thumbtack card-pin-indicator"></i>' : ''}
                        </div>
                        <div class="library-card-details">
                            <h4>${song.title}</h4>
                            <p>${song.artist || 'Unknown'}</p>
                        </div>
                    `;
                    card.addEventListener('click', () => {
                        loadSongIntoPlayer(song);
                        navigateToView('player');
                    });
                    recentGrid.appendChild(card);
                });
            } else {
                recentGrid.innerHTML = `<div class="empty-state">Your creations will appear here.</div>`;
            }
        }
    } catch (err) {
        console.error(err);
    }
}

// Fetch all tracks
async function loadLibrary() {
    try {
        // Fetch non-deleted tracks
        const res = await fetch(`${API_BASE}/api/songs`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            songsLibrary = await res.json();
        }

        // Fetch soft-deleted tracks
        const trashRes = await fetch(`${API_BASE}/api/songs?deleted=true`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (trashRes.ok) {
            softDeletedSongs = await trashRes.json();
        }

        renderLibraryView();
    } catch (err) {
        showToast('Failed to load library: ' + err.message, 'error');
    }
}

// Redraw library layout
function renderLibraryView() {
    const grid = document.getElementById('library-grid-container');
    grid.innerHTML = '';

    if (libraryViewMode === 'grid') {
        grid.className = 'library-grid';
    } else {
        grid.className = 'library-grid list-mode';
    }

    const searchQuery = document.getElementById('library-search-input').value.toLowerCase();
    
    // Choose active collection array
    let tracks = [];
    if (currentLibTab === 'trash') {
        tracks = softDeletedSongs;
    } else {
        tracks = songsLibrary;
    }

    // Filter by query
    let filtered = tracks.filter(song => {
        const tags = (song.tags || '').toLowerCase();
        const playlist = (song.playlist || '').toLowerCase();
        return song.title.toLowerCase().includes(searchQuery) ||
               (song.artist || '').toLowerCase().includes(searchQuery) ||
               tags.includes(searchQuery) ||
               playlist.includes(searchQuery);
    });

    if (filtered.length === 0) {
        grid.innerHTML = `<div class="empty-state">No songs found in this section.</div>`;
        return;
    }

    filtered.forEach(song => {
        const card = document.createElement('div');
        card.className = 'library-card';
        
        let coverStyle = song.cover_image ? `style="background-image: url(${API_BASE}${song.cover_image})"` : '';
        
        let pinIcon = song.pinned ? '<i class="fa-solid fa-thumbtack card-pin-indicator"></i>' : '';
        
        let actionButtons = '';
        if (currentLibTab === 'trash') {
            actionButtons = `
                <button class="card-action-btn" title="Restore song" onclick="event.stopPropagation(); restoreSong(${song.id})">
                    <i class="fa-solid fa-trash-arrow-up"></i> Restore
                </button>
                <button class="card-action-btn" title="Purge song permanently" style="color: #e25858;" onclick="event.stopPropagation(); purgeSong(${song.id})">
                    <i class="fa-solid fa-ban"></i> Purge
                </button>
            `;
        } else {
            actionButtons = `
                <button class="card-action-btn ${song.favourite ? 'fav-active' : ''}" onclick="event.stopPropagation(); toggleCardFavourite(${song.id})">
                    <i class="fa-solid fa-heart"></i>
                </button>
                <button class="card-action-btn" onclick="event.stopPropagation(); toggleCardPin(${song.id})">
                    <i class="fa-solid fa-thumbtack"></i>
                </button>
                <button class="card-action-btn" onclick="event.stopPropagation(); moveToTrash(${song.id})">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            `;
        }

        card.innerHTML = `
            <div class="library-card-art" ${coverStyle}>
                ${!song.cover_image ? '<i class="fa-solid fa-music"></i>' : ''}
                ${pinIcon}
            </div>
            <div class="library-card-details">
                <h4>${song.title}</h4>
                <p>${song.artist || 'Unknown'}</p>
            </div>
            <div class="card-actions">
                ${actionButtons}
            </div>
        `;
        
        if (currentLibTab !== 'trash') {
            card.addEventListener('click', () => {
                loadSongIntoPlayer(song);
                navigateToView('player');
            });
        }

        grid.appendChild(card);
    });
}

// Fast operations inside cards
async function toggleCardFavourite(id) {
    try {
        const res = await fetch(`${API_BASE}/api/songs/${id}/favourite`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            loadLibrary();
            showToast('Favorite status updated!', 'success');
        }
    } catch (e) {
        console.error(e);
    }
}

async function toggleCardPin(id) {
    try {
        const res = await fetch(`${API_BASE}/api/songs/${id}/pin`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            loadLibrary();
            showToast('Pin status updated!', 'success');
        }
    } catch (e) {
        console.error(e);
    }
}

async function moveToTrash(id) {
    try {
        const res = await fetch(`${API_BASE}/api/songs/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            loadLibrary();
            showToast('Song moved to Recycle Bin.', 'success');
        }
    } catch (e) {
        console.error(e);
    }
}

async function restoreSong(id) {
    try {
        const res = await fetch(`${API_BASE}/api/songs/${id}/restore`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            loadLibrary();
            showToast('Song restored successfully.', 'success');
        }
    } catch (e) {
        console.error(e);
    }
}

async function purgeSong(id) {
    if (!confirm('This action cannot be undone. Purge song permanently?')) return;
    try {
        const res = await fetch(`${API_BASE}/api/songs/${id}/purge`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            loadLibrary();
            showToast('Song purged permanently.', 'success');
        }
    } catch (e) {
        console.error(e);
    }
}

// Generate execution
async function startGeneration() {
    const inputVal = songInput.value.trim();
    const playlistVal = document.getElementById('song-playlist-input').value.trim();
    const tagsVal = document.getElementById('song-tags-input').value.trim();
    
    if (!inputVal) return;

    cassetteTape.classList.add('inserted');
    showToast('Starting stem separation processor...', 'process');

    setTimeout(async () => {
        processingOverlay.classList.add('active');
        cassetteTape.classList.add('spinning');
        
        let progress = 0;
        const progressTimer = setInterval(() => {
            if (progress < 90) {
                progress += Math.random() * 8;
                progressFill.style.width = Math.min(progress, 90) + '%';
            }
        }, 800);

        try {
            const response = await fetch(`${API_BASE}/api/process`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ 
                    query: inputVal,
                    playlist: playlistVal || null,
                    tags: tagsVal || null
                })
            });
            const data = await response.json();
            
            clearInterval(progressTimer);
            progressFill.style.width = '100%';
            
            if (response.ok) {
                loadingStatus.innerText = 'SUCCESS!';
                activeSong = data;
                showToast('Karaoke created successfully!', 'success');

                setTimeout(() => {
                    processingOverlay.classList.remove('active');
                    cassetteTape.classList.remove('spinning', 'inserted');
                    songInput.value = '';
                    document.getElementById('song-playlist-input').value = '';
                    document.getElementById('song-tags-input').value = '';
                    progressFill.style.width = '0%';
                    loadingStatus.innerText = 'SEPARATING VOCALS...';

                    document.getElementById('ejected-cd-title').innerText = data.title;
                    document.getElementById('ejected-cd-artist').innerText = data.artist || 'AI Studio';
                    cdEjectTray.classList.add('active');
                }, 1000);
            } else {
                showToast('Separation failed: ' + (data.message || 'Error'), 'error');
                resetGeneratorState();
            }
        } catch (err) {
            clearInterval(progressTimer);
            if (err.message && (err.message.includes('fetch') || err.message.includes('Network'))) {
                showToast('Server connecting... If Render backend is sleeping or paused, please click Manual Deploy on Render.', 'error');
            } else {
                showToast('Network error: ' + err.message, 'error');
            }
            resetGeneratorState();
        }
    }, 1200);
}

function resetGeneratorState() {
    processingOverlay.classList.remove('active');
    cassetteTape.classList.remove('spinning', 'inserted');
    progressFill.style.width = '0%';
}

// Load track into Player
function loadSongIntoPlayer(song) {
    stopPlayback();
    activeSong = song;

    // Send analytics play request
    incrementPlayCount(song.id);

    document.getElementById('player-cd-title').innerText = song.title;
    document.getElementById('player-cd-artist').innerText = song.artist || 'Unknown';
    document.getElementById('player-meta-title').innerText = song.title;
    document.getElementById('player-meta-artist').innerText = song.artist || 'Unknown';
    document.getElementById('player-meta-key').innerHTML = `<i class="fa-solid fa-music"></i> Key: ${song.pitch || 'Unknown'}`;
    document.getElementById('player-meta-source').innerHTML = `<i class="fa-solid fa-satellite"></i> ${song.source || 'Scraper'}`;
    document.getElementById('player-meta-playlist').innerHTML = `<i class="fa-solid fa-folder-open"></i> Playlist: ${song.playlist || 'Default'}`;

    // Bios
    document.getElementById('bio-singer-title').innerText = `${song.artist || 'Artist'} Biography`;
    document.getElementById('bio-singer-text').innerText = song.singer_bio || 'Biography details loaded on demand.';
    document.getElementById('bio-composer-title').innerText = `Composer: ${song.composer || 'Unknown'}`;
    document.getElementById('bio-composer-text').innerText = song.composer_bio || 'Details of orchestration not available.';

    originalAudio.src = `${API_BASE}${song.audio_file_url}`;
    instrumentalAudio.src = `${API_BASE}${song.karaoke_file_url}`;

    // Font Sizing
    document.getElementById('lyrics-scroll-box').style.fontSize = defaultLyricFontSize + 'px';

    const cdArt = document.getElementById('player-artwork');
    if (song.cover_image) {
        cdArt.style.backgroundImage = `url(${API_BASE}${song.cover_image})`;
        document.querySelector('.cd-art-label').style.display = 'none';
    } else {
        cdArt.style.backgroundImage = 'none';
        document.querySelector('.cd-art-label').style.display = 'flex';
    }

    updateHeartState();
    updatePinState();

    const lyricsBox = document.getElementById('lyrics-scroll-box');
    lyricsBox.innerHTML = '';
    
    if (song.lyrics) {
        const lines = song.lyrics.split('\n');
        lines.forEach((line) => {
            if (line.trim()) {
                const el = document.createElement('p');
                el.className = 'lyrics-line';
                el.innerText = line.trim();
                lyricsBox.appendChild(el);
            }
        });
    } else {
        lyricsBox.innerHTML = '<p class="no-lyrics">No lyrics found for this song.</p>';
    }

    // Default mixer ranges
    document.getElementById('vol-instrumental').value = 1;
    document.getElementById('vol-vocals').value = 0;
    document.getElementById('vol-speed').value = 1.0;
    document.getElementById('val-instrumental').innerText = '100%';
    document.getElementById('val-vocals').innerText = '0%';
    document.getElementById('val-speed').innerText = '1.0x';
    
    instrumentalAudio.volume = 1;
    originalAudio.volume = 0;
    setPitchTranspose(0);

    document.getElementById('playback-progress').value = 0;
}

// Analytics track
async function incrementPlayCount(id) {
    try {
        fetch(`${API_BASE}/api/songs/${id}/play`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
    } catch (e) {
        console.error(e);
    }
}

function togglePlayback() {
    const playBtn = document.getElementById('btn-play');
    const spinCd = document.getElementById('player-cd');
    
    if (isPlaying) {
        originalAudio.pause();
        instrumentalAudio.pause();
        playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
        spinCd.classList.remove('playing');
        isPlaying = false;
        clearInterval(updateInterval);
    } else {
        originalAudio.play();
        instrumentalAudio.play();
        playBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
        spinCd.classList.add('playing');
        isPlaying = true;
        
        updateInterval = setInterval(updateProgress, 250);
    }
}

function updateProgress() {
    if (!instrumentalAudio.duration) return;
    
    const curr = instrumentalAudio.currentTime;
    const dur = instrumentalAudio.duration;
    
    const percent = (curr / dur) * 100;
    document.getElementById('playback-progress').value = percent;

    document.getElementById('current-time').innerText = formatTime(curr);
    document.getElementById('total-time').innerText = formatTime(dur);

    // Sync scrolling lyrics
    const lines = document.querySelectorAll('.lyrics-line');
    if (lines.length > 0) {
        const activeIndex = Math.floor((curr / dur) * lines.length);
        lines.forEach((line, idx) => {
            if (idx === activeIndex) {
                line.classList.add('active');
                line.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                line.classList.remove('active');
            }
        });
    }

    if (curr >= dur) {
        if (isLoopEnabled) {
            restartPlayback();
        } else {
            stopPlayback();
        }
    }
}

function formatTime(secs) {
    const min = Math.floor(secs / 60);
    const sec = Math.floor(secs % 60);
    return `${min < 10 ? '0' : ''}${min}:${sec < 10 ? '0' : ''}${sec}`;
}

function stopPlayback() {
    originalAudio.pause();
    instrumentalAudio.pause();
    isPlaying = false;
    document.getElementById('btn-play').innerHTML = '<i class="fa-solid fa-play"></i>';
    document.getElementById('player-cd').classList.remove('playing');
    clearInterval(updateInterval);
}

function restartPlayback() {
    originalAudio.currentTime = 0;
    instrumentalAudio.currentTime = 0;
    updateProgress();
    if (!isPlaying) {
        togglePlayback();
    }
}

function toggleMute() {
    const muteBtn = document.getElementById('btn-mute');
    const isMuted = originalAudio.muted;
    
    originalAudio.muted = !isMuted;
    instrumentalAudio.muted = !isMuted;
    
    if (!isMuted) {
        muteBtn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
    } else {
        muteBtn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
    }
}

function downloadInstrumental() {
    if (!activeSong) return;
    window.open(`${API_BASE}${activeSong.karaoke_file_url}?download=true`);
}

async function toggleFavourite() {
    if (!activeSong) return;
    try {
        const res = await fetch(`${API_BASE}/api/songs/${activeSong.id}/favourite`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const updated = await res.json();
            activeSong.favourite = updated.favourite;
            updateHeartState();
            showToast('Favorite status updated!', 'success');
        }
    } catch (err) {
        console.error(err);
    }
}

function updateHeartState() {
    const heart = document.getElementById('btn-favourite');
    if (activeSong && activeSong.favourite) {
        heart.innerHTML = '<i class="fa-solid fa-heart"></i>';
        heart.classList.add('favourite-active');
    } else {
        heart.innerHTML = '<i class="fa-regular fa-heart"></i>';
        heart.classList.remove('favourite-active');
    }
}

async function togglePin() {
    if (!activeSong) return;
    try {
        const res = await fetch(`${API_BASE}/api/songs/${activeSong.id}/pin`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const updated = await res.json();
            activeSong.pinned = updated.pinned;
            updatePinState();
            showToast('Pin status updated!', 'success');
        }
    } catch (e) {
        console.error(e);
    }
}

function updatePinState() {
    const pin = document.getElementById('btn-pin');
    if (activeSong && activeSong.pinned) {
        pin.innerHTML = '<i class="fa-solid fa-thumbtack"></i>';
        pin.style.color = 'var(--primary)';
        pin.style.borderColor = 'var(--primary)';
    } else {
        pin.innerHTML = '<i class="fa-solid fa-thumbtack"></i>';
        pin.style.color = '';
        pin.style.borderColor = '';
    }
}

async function sendDeleteRequest() {
    if (!activeSong) return;
    if (!confirm('Move current song to Recycle Bin?')) return;
    
    try {
        const res = await fetch(`${API_BASE}/api/songs/${activeSong.id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            stopPlayback();
            navigateToView('library');
            showToast('Song moved to Recycle Bin.', 'success');
        }
    } catch (err) {
        console.error(err);
    }
}

// Fullscreen mode handler
function toggleFullscreenKaraoke() {
    const fullscreenDiv = document.createElement('div');
    fullscreenDiv.className = 'fullscreen-karaoke';
    fullscreenDiv.innerHTML = `
        <div class="fullscreen-close"><i class="fa-solid fa-xmark"></i></div>
        <div class="lyrics-container" style="font-size: 26px; line-height: 2.5; max-height: 80%; width: 80%;">
            ${document.getElementById('lyrics-scroll-box').innerHTML}
        </div>
    `;

    document.body.appendChild(fullscreenDiv);

    fullscreenDiv.querySelector('.fullscreen-close').addEventListener('click', () => {
        fullscreenDiv.remove();
    });
}

// Keyboard play/pause
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Only trigger space play/pause if not typing in inputs
        if (e.code === 'Space' && document.activeElement.tagName !== 'INPUT') {
            e.preventDefault();
            if (activeSong) {
                togglePlayback();
            }
        }
    });
}

// Statistics calculation
function renderStatsPage() {
    document.getElementById('stats-page-total').innerText = songsLibrary.length;
    
    let maxPlays = -1;
    let popularSong = 'No history yet';
    
    songsLibrary.forEach(song => {
        if ((song.play_count || 0) > maxPlays) {
            maxPlays = song.play_count;
            popularSong = `${song.title} (${song.play_count} plays)`;
        }
    });

    document.getElementById('stats-page-mostplayed').innerText = popularSong;
}

// Canvas spectrum animator
function setupVisualizer() {
    function draw() {
        animationFrameId = requestAnimationFrame(draw);
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        const barsCount = 64;
        const spacing = 4;
        const barWidth = (canvas.width - (barsCount * spacing)) / barsCount;
        
        const computedStyle = getComputedStyle(document.body);
        const colorStart = computedStyle.getPropertyValue('--primary').trim() || '#8B6A4E';
        const colorEnd = computedStyle.getPropertyValue('--secondary').trim() || '#324A5F';
        
        for (let i = 0; i < barsCount; i++) {
            let value = 4;
            
            if (isPlaying) {
                const timeFactor = Date.now() * 0.005;
                const volumeFactor = instrumentalAudio.volume + originalAudio.volume;
                value = Math.abs(Math.sin(i * 0.15 + timeFactor) * Math.cos(i * 0.05 + timeFactor)) * 30 * volumeFactor;
                value = Math.max(value, 4);
            }
            
            const gradient = ctx.createLinearGradient(0, canvas.height, 0, 0);
            gradient.addColorStop(0, colorStart);
            gradient.addColorStop(1, colorEnd);
            
            ctx.fillStyle = gradient;
            ctx.fillRect(i * (barWidth + spacing), canvas.height - value, barWidth, value);
        }
    }
    draw();
}
