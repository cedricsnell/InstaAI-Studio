// InstaAI Studio - Web Application JavaScript

// Global state
let auth = {
    username: null,
    password: null
};

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupEventListeners();
    checkLoginStatus();
}

function setupEventListeners() {
    // Login form
    document.getElementById('login-form').addEventListener('submit', handleLogin);

    // Logout button
    document.getElementById('logout-btn').addEventListener('click', handleLogout);

    // Tab navigation
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // File upload
    const fileInput = document.getElementById('file-input');
    const uploadArea = document.getElementById('upload-area');

    fileInput.addEventListener('change', handleFileSelect);

    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // Schedule form
    document.getElementById('schedule-form').addEventListener('submit', handleScheduleSubmit);
}

function checkLoginStatus() {
    // Check if credentials are stored
    const stored = sessionStorage.getItem('auth');
    if (stored) {
        auth = JSON.parse(stored);
        showDashboard();
        loadDashboardData();
    }
}

async function handleLogin(e) {
    e.preventDefault();

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    auth = { username, password };

    try {
        // Test credentials by calling health check
        const response = await apiCall('/api/health', 'GET');

        if (response.status === 'healthy') {
            sessionStorage.setItem('auth', JSON.stringify(auth));
            document.getElementById('username').textContent = username;
            showDashboard();
            loadDashboardData();
        }
    } catch (error) {
        alert('Login failed: ' + error.message);
        auth = { username: null, password: null };
    }
}

function handleLogout() {
    auth = { username: null, password: null };
    sessionStorage.removeItem('auth');
    showLogin();
}

function showLogin() {
    document.getElementById('login-screen').classList.add('active');
    document.getElementById('dashboard-screen').classList.remove('active');
}

function showDashboard() {
    document.getElementById('login-screen').classList.remove('active');
    document.getElementById('dashboard-screen').classList.add('active');
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load data for specific tabs
    if (tabName === 'manage') {
        refreshFiles();
    } else if (tabName === 'schedule') {
        loadScheduleFiles();
        refreshScheduled();
    } else if (tabName === 'account') {
        refreshAccountInfo();
        loadConfigStatus();
    }
}

function loadDashboardData() {
    refreshFiles();
    loadConfigStatus();
}

// File Upload Functions
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        uploadFile(file);
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.target.classList.add('dragover');
}

function handleDragLeave(e) {
    e.target.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.target.classList.remove('dragover');

    const file = e.dataTransfer.files[0];
    if (file) {
        uploadFile(file);
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const statusDiv = document.getElementById('upload-status');
    statusDiv.innerHTML = '<p>Uploading...</p>';

    try {
        const response = await apiCall('/api/upload', 'POST', formData);

        if (response.success) {
            statusDiv.innerHTML = `
                <div class="status-message success">
                    ✓ File uploaded successfully: ${file.name} (${formatBytes(response.size)})
                </div>
            `;
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="status-message error">
                ✗ Upload failed: ${error.message}
            </div>
        `;
    }
}

// Commands Functions
function addCommand() {
    const commandsList = document.getElementById('commands-list');
    const newInput = document.createElement('div');
    newInput.className = 'command-input';
    newInput.innerHTML = `
        <input type="text" placeholder='e.g., "Add jump cuts"' class="command-field">
        <button class="btn-icon" onclick="removeCommand(this)">−</button>
    `;
    commandsList.appendChild(newInput);
}

function removeCommand(button) {
    button.parentElement.remove();
}

function addQuickCommand(command) {
    const commandsList = document.getElementById('commands-list');
    const lastInput = commandsList.querySelector('.command-input:last-child input');

    if (lastInput.value === '') {
        lastInput.value = command;
    } else {
        addCommand();
        const newInput = commandsList.querySelector('.command-input:last-child input');
        newInput.value = command;
    }
}

// Create Content
async function createContent() {
    // Get commands
    const commandInputs = document.querySelectorAll('.command-field');
    const commands = Array.from(commandInputs)
        .map(input => input.value.trim())
        .filter(cmd => cmd !== '');

    if (commands.length === 0) {
        alert('Please add at least one command');
        return;
    }

    // Get content type
    const contentType = document.querySelector('input[name="content-type"]:checked').value;

    const createBtn = document.getElementById('create-btn');
    const statusDiv = document.getElementById('create-status');

    createBtn.disabled = true;
    showLoading();
    statusDiv.innerHTML = '<div class="status-message info">Creating content... This may take a few minutes.</div>';

    try {
        const response = await apiCall('/api/create', 'POST', {
            commands: commands,
            content_type: contentType
        });

        if (response.success) {
            statusDiv.innerHTML = `
                <div class="status-message success">
                    ✓ Content created successfully!<br>
                    Output: ${response.output_filename}<br>
                    <button class="btn-secondary" onclick="switchTab('manage')">View Files</button>
                </div>
            `;
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="status-message error">
                ✗ Failed to create content: ${error.message}
            </div>
        `;
    } finally {
        createBtn.disabled = false;
        hideLoading();
    }
}

// Files Management
async function refreshFiles() {
    try {
        const response = await apiCall('/api/files', 'GET');

        if (response.success) {
            displayFiles('output-files', response.outputs);
            displayFiles('upload-files', response.uploads);
        }
    } catch (error) {
        console.error('Failed to load files:', error);
    }
}

function displayFiles(containerId, files) {
    const container = document.getElementById(containerId);

    if (files.length === 0) {
        container.innerHTML = '<p class="empty-state">No files yet.</p>';
        return;
    }

    container.innerHTML = files.map(file => `
        <div class="file-card">
            <h4>${file.filename}</h4>
            <p>Size: ${formatBytes(file.size)}</p>
            <p>Created: ${formatDate(file.created)}</p>
            <div class="file-actions">
                <button class="btn-secondary" onclick="downloadFile('${file.filename}')">Download</button>
                <button class="btn-danger" onclick="deleteFile('${file.filename}')">Delete</button>
            </div>
        </div>
    `).join('');
}

async function downloadFile(filename) {
    window.open(`/api/download/${filename}`, '_blank');
}

async function deleteFile(filename) {
    if (!confirm(`Delete ${filename}?`)) return;

    try {
        const response = await apiCall(`/api/files/${filename}`, 'DELETE');

        if (response.success) {
            refreshFiles();
        }
    } catch (error) {
        alert('Failed to delete file: ' + error.message);
    }
}

// Scheduling Functions
async function loadScheduleFiles() {
    try {
        const response = await apiCall('/api/files', 'GET');

        if (response.success) {
            const select = document.getElementById('schedule-file');
            select.innerHTML = '<option value="">Choose a file...</option>';

            response.outputs.forEach(file => {
                const option = document.createElement('option');
                option.value = file.filename;
                option.textContent = file.filename;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load files:', error);
    }
}

async function handleScheduleSubmit(e) {
    e.preventDefault();

    const filename = document.getElementById('schedule-file').value;
    const postType = document.getElementById('schedule-type').value;
    const time = document.getElementById('schedule-time').value;
    const caption = document.getElementById('schedule-caption').value;
    const hashtags = document.getElementById('schedule-hashtags').value
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag !== '');

    showLoading();

    try {
        const response = await apiCall('/api/post', 'POST', {
            media_filename: filename,
            post_type: postType,
            caption: caption,
            hashtags: hashtags,
            scheduled_time: time
        });

        if (response.success) {
            alert(response.message);
            document.getElementById('schedule-form').reset();
            refreshScheduled();
        }
    } catch (error) {
        alert('Failed to schedule post: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function refreshScheduled() {
    try {
        const response = await apiCall('/api/scheduled?status=scheduled', 'GET');

        const container = document.getElementById('scheduled-posts');

        if (!response.posts || response.posts.length === 0) {
            container.innerHTML = '<p class="empty-state">No scheduled posts.</p>';
            return;
        }

        container.innerHTML = response.posts.map(post => `
            <div class="scheduled-post">
                <h4>${post.post_type.toUpperCase()}: ${post.media_path}</h4>
                <p>Scheduled: ${formatDate(post.scheduled_time)}</p>
                <p>Caption: ${post.caption || 'No caption'}</p>
                <div class="post-actions">
                    <button class="btn-danger" onclick="cancelScheduled('${post.job_id}')">Cancel</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load scheduled posts:', error);
    }
}

async function cancelScheduled(jobId) {
    if (!confirm('Cancel this scheduled post?')) return;

    try {
        const response = await apiCall(`/api/scheduled/${jobId}`, 'DELETE');

        if (response.success) {
            refreshScheduled();
        }
    } catch (error) {
        alert('Failed to cancel: ' + error.message);
    }
}

// Account Functions
async function refreshAccountInfo() {
    const container = document.getElementById('account-info');
    container.innerHTML = '<p>Loading...</p>';

    try {
        const response = await apiCall('/api/account', 'GET');

        if (response.success) {
            const account = response.account;
            container.innerHTML = `
                <p><strong>Username:</strong> @${account.username}</p>
                <p><strong>Full Name:</strong> ${account.full_name}</p>
                <p><strong>Followers:</strong> ${account.followers.toLocaleString()}</p>
                <p><strong>Following:</strong> ${account.following.toLocaleString()}</p>
                <p><strong>Posts:</strong> ${account.posts.toLocaleString()}</p>
                <p><strong>Business Account:</strong> ${account.is_business ? 'Yes' : 'No'}</p>
                <p><strong>Verified:</strong> ${account.is_verified ? 'Yes ✓' : 'No'}</p>
            `;
        }
    } catch (error) {
        container.innerHTML = `<p class="status-message error">Failed to load account info: ${error.message}</p>`;
    }
}

async function loadConfigStatus() {
    const container = document.getElementById('config-status');
    container.innerHTML = '<p>Loading...</p>';

    try {
        const response = await apiCall('/api/config', 'GET');

        container.innerHTML = `
            <p><strong>AI Configured:</strong> ${response.ai_configured ? '✓ Yes' : '✗ No'}</p>
            <p><strong>Instagram Configured:</strong> ${response.instagram_configured ? '✓ Yes' : '✗ No'}</p>
            <p><strong>Scheduler Enabled:</strong> ${response.scheduler_enabled ? '✓ Yes' : '✗ No'}</p>
            <p><strong>Max Video Duration:</strong> ${response.max_video_duration}s</p>
        `;
    } catch (error) {
        container.innerHTML = `<p class="status-message error">Failed to load config</p>`;
    }
}

// Loading Overlay
function showLoading() {
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}

// API Call Helper
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method: method,
        headers: {
            'Authorization': 'Basic ' + btoa(auth.username + ':' + auth.password)
        }
    };

    if (body) {
        if (body instanceof FormData) {
            options.body = body;
        } else {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
    }

    const response = await fetch(endpoint, options);

    if (response.status === 401) {
        handleLogout();
        throw new Error('Authentication failed');
    }

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Request failed');
    }

    return await response.json();
}

// Utility Functions
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}
