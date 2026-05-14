/* ========================================
   PuppyCLI — Frontend Application Logic
   ======================================== */

// --- i18n ---
const i18n = {
    _lang: 'en',
    _data: {
        'new-chat':       { zh: '新建对话', en: 'New Chat' },
        'settings':       { zh: '设置', en: 'Settings' },
        'theme':          { zh: '切换主题', en: 'Toggle Theme' },
        'docs':           { zh: '文档', en: 'Docs' },
        'lang':           { zh: '切换语言', en: 'Language' },
        'send':           { zh: '发送', en: 'Send' },
        'conversations':  { zh: '对话列表', en: 'Conversations' },
        'placeholder':    { zh: '输入消息... (Enter 发送, Shift+Enter 换行)', en: 'Type a message... (Enter to send, Shift+Enter for new line)' },
        'settings-title': { zh: '设置', en: 'Settings' },
        'api-key':        { zh: 'API 密钥', en: 'API Key' },
        'model':          { zh: '模型', en: 'Model' },
        'base-url':       { zh: '接口地址', en: 'Base URL' },
        'python-env':     { zh: 'Python 环境路径', en: 'Python Env Path' },
        'data-dir':       { zh: '数据目录', en: 'Data Directory' },
        'save':           { zh: '保存', en: 'Save' },
        'cancel':         { zh: '取消', en: 'Cancel' },
        'rename':         { zh: '重命名', en: 'Rename' },
        'delete':         { zh: '删除', en: 'Delete' },
        'delete-confirm': { zh: '确定要删除这个对话吗？此操作不可撤销。', en: 'Delete this conversation? This cannot be undone.' },
        'toggle-sidebar': { zh: '折叠/展开侧栏', en: 'Toggle Sidebar' },
    },

    t(key) {
        const entry = this._data[key];
        return entry ? (entry[this._lang] || entry.en) : key;
    },

    init() {
        const saved = localStorage.getItem('puppycli-lang');
        if (saved === 'zh' || saved === 'en') {
            this._lang = saved;
        } else {
            this._lang = navigator.language.startsWith('zh') ? 'zh' : 'en';
        }
        this.apply();
    },

    toggle() {
        this._lang = this._lang === 'zh' ? 'en' : 'zh';
        localStorage.setItem('puppycli-lang', this._lang);
        this.apply();
    },

    set(lang) {
        if (lang === 'zh' || lang === 'en') {
            this._lang = lang;
            localStorage.setItem('puppycli-lang', this._lang);
            this.apply();
        }
    },

    apply() {
        // text content
        document.querySelectorAll('[data-i18n]').forEach(el => {
            el.textContent = this.t(el.getAttribute('data-i18n'));
        });
        // title attributes
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            el.title = this.t(el.getAttribute('data-i18n-title'));
        });
        // placeholder attributes
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            el.placeholder = this.t(el.getAttribute('data-i18n-placeholder'));
        });
        // Update HTML lang attr
        document.documentElement.lang = this._lang;
    }
};

const ICON_SUN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>';
const ICON_MOON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>';

// --- State ---
const state = {
    currentSessionId: null,
    ws: null,
    isStreaming: false,
    _lastUserMessage: '',  // for /retry command
};

// --- DOM Elements ---
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const elements = {
    messages: $('#messages'),
    userInput: $('#user-input'),
    btnNewChat: $('#btn-new-chat'),
    btnTheme: $('#btn-theme'),
    btnLang: $('#btn-lang'),
    btnSettings: $('#btn-settings'),
    btnSidebarToggle: $('#btn-sidebar-toggle'),
    btnDocs: $('#btn-docs'),
    sessionList: $('#session-list'),
    settingsModal: $('#settings-modal'),
    btnSettingsSave: $('#btn-settings-save'),
    btnSettingsClose: $('#btn-settings-close'),
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    i18n.init();
    initSidebar();
    loadTheme();
    loadSessions();
    setupEventListeners();
    showEmptyState();
});

// --- Sidebar Toggle ---
function initSidebar() {
    if (localStorage.getItem('puppycli-sidebar') === 'collapsed') {
        $('#app').classList.add('sidebar-collapsed');
    }
}

function toggleSidebar() {
    const app = $('#app');
    app.classList.toggle('sidebar-collapsed');
    const collapsed = app.classList.contains('sidebar-collapsed');
    localStorage.setItem('puppycli-sidebar', collapsed ? 'collapsed' : 'expanded');
}

// --- Theme ---
function loadTheme() {
    const theme = localStorage.getItem('puppycli-theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    elements.btnTheme.innerHTML = theme === 'dark' ? ICON_SUN : ICON_MOON;
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('puppycli-theme', next);
    elements.btnTheme.innerHTML = next === 'dark' ? ICON_SUN : ICON_MOON;
}

// --- Slash Command Autocomplete ---
const SLASH_COMMANDS = [
    { cmd: '/help',     descZh: '显示帮助',         descEn: 'Show help' },
    { cmd: '/clear',    descZh: '清除对话',         descEn: 'Clear conversation' },
    { cmd: '/new',      descZh: '新建对话',         descEn: 'New conversation' },
    { cmd: '/theme',    descZh: '切换主题',         descEn: 'Switch theme' },
    { cmd: '/lang',     descZh: '切换语言',         descEn: 'Switch language' },
    { cmd: '/settings', descZh: '打开设置',         descEn: 'Open settings' },
    { cmd: '/export',   descZh: '导出对话',         descEn: 'Export conversation' },
    { cmd: '/retry',    descZh: '重新生成',         descEn: 'Regenerate response' },
    { cmd: '/model',    descZh: '切换模型',         descEn: 'Switch model' },
    { cmd: '/skill',    descZh: '管理技能',         descEn: 'Manage skills' },
    { cmd: '/search',   descZh: '搜索技能',         descEn: 'Search skills' },
    { cmd: '/kb',       descZh: '知识库管理',       descEn: 'Knowledge base' },
    { cmd: '/pdf',      descZh: '处理 PDF',         descEn: 'Process PDF' },
    { cmd: '/docs',     descZh: '打开文档',         descEn: 'Open docs' },
];

let _suggIndex = -1;
const $sugg = () => $('#slash-suggestions');

function updateSuggestions() {
    const val = elements.userInput.value;
    if (!val.startsWith('/') || val.includes(' ')) {
        hideSuggestions();
        return;
    }
    const query = val.slice(1).toLowerCase();
    const matches = SLASH_COMMANDS.filter(s => s.cmd.slice(1).startsWith(query));
    if (matches.length === 0 || (matches.length === 1 && matches[0].cmd === val)) {
        hideSuggestions();
        return;
    }
    const isZh = i18n._lang === 'zh';
    $sugg().innerHTML = matches.map((s, i) =>
        `<div class="slash-item" data-index="${i}"><span class="slash-cmd">${s.cmd}</span><span class="slash-desc">${isZh ? s.descZh : s.descEn}</span></div>`
    ).join('');
    $sugg().classList.remove('hidden');
    _suggIndex = -1;
    $sugg().querySelectorAll('.slash-item').forEach(el => {
        el.addEventListener('mousedown', (e) => {
            e.preventDefault();
            const cmd = matches[parseInt(el.dataset.index)].cmd;
            elements.userInput.value = cmd + ' ';
            hideSuggestions();
            elements.userInput.focus();
        });
    });
}

function hideSuggestions() {
    $sugg().classList.add('hidden');
    $sugg().innerHTML = '';
    _suggIndex = -1;
}

// --- Local Message Persistence ---
async function ensureSession() {
    if (state.currentSessionId) return;
    try {
        const resp = await fetch('/api/sessions', { method: 'POST' });
        const data = await resp.json();
        state.currentSessionId = data.session_id;
        loadSessions();
    } catch (e) {
        console.error('Failed to create session:', e);
    }
}

async function saveLocalMessage(role, content) {
    if (!state.currentSessionId || !content) return;
    try {
        await fetch(`/api/sessions/${state.currentSessionId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role, content }),
        });
    } catch (e) {
        console.error('Failed to save message:', e);
    }
}

function navigateSuggestions(dir) {
    const items = $sugg().querySelectorAll('.slash-item');
    if (items.length === 0) return;
    items.forEach(el => el.classList.remove('active'));
    _suggIndex = Math.max(0, Math.min(items.length - 1, _suggIndex + dir));
    items[_suggIndex].classList.add('active');
    items[_suggIndex].scrollIntoView({ block: 'nearest' });
}

function selectSuggestion() {
    const items = $sugg().querySelectorAll('.slash-item');
    if (items.length === 0 || _suggIndex < 0) return false;
    const cmd = items[_suggIndex].querySelector('.slash-cmd').textContent;
    elements.userInput.value = cmd + ' ';
    hideSuggestions();
    return true;
}

// --- Event Listeners ---
function setupEventListeners() {
    elements.userInput.addEventListener('keydown', (e) => {
        // Handle suggestion navigation first
        if (!$sugg().classList.contains('hidden')) {
            if (e.key === 'ArrowDown') { e.preventDefault(); navigateSuggestions(1); return; }
            if (e.key === 'ArrowUp')   { e.preventDefault(); navigateSuggestions(-1); return; }
            if (e.key === 'Enter' && !e.shiftKey) {
                if (selectSuggestion()) { e.preventDefault(); return; }
            }
            if (e.key === 'Escape') { e.preventDefault(); hideSuggestions(); return; }
            if (e.key === 'Tab') { e.preventDefault(); selectSuggestion(); return; }
        }
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    elements.userInput.addEventListener('input', () => {
        autoResizeTextarea();
        updateSuggestions();
    });
    elements.btnNewChat.addEventListener('click', newChat);
    elements.btnTheme.addEventListener('click', toggleTheme);
    elements.btnLang.addEventListener('click', () => i18n.toggle());
    elements.btnSidebarToggle.addEventListener('click', toggleSidebar);
    elements.btnSettings.addEventListener('click', openSettings);
    elements.btnSettingsClose.addEventListener('click', closeSettings);
    elements.btnSettingsSave.addEventListener('click', saveSettings);
    if (elements.btnDocs) {
        elements.btnDocs.addEventListener('click', () => window.open('/help/', '_blank'));
    }
}

// --- WebSocket ---
function connectWebSocket() {
    if (state.ws && state.ws.readyState === WebSocket.OPEN) return;

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/chat`;
    state.ws = new WebSocket(wsUrl);

    state.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWSMessage(data);
    };

    state.ws.onclose = () => {
        state.ws = null;
    };

    state.ws.onerror = (err) => {
        console.error('WebSocket error:', err);
    };
}

function handleWSMessage(data) {
    switch (data.type) {
        case 'session_id':
            state.currentSessionId = data.session_id;
            break;
        case 'token':
            appendToken(data.content);
            break;
        case 'done':
            finishStreaming();
            loadSessions();
            break;
        case 'error':
            showError(data.message);
            break;
        case 'confirm_tool':
            showConfirmCard(data.confirm_id, data.command, data.reason);
            break;
    }
}

function sendMessage() {
    const content = elements.userInput.value.trim();
    hideSuggestions();
    if (!content || state.isStreaming) return;

    // Bang commands — execute PowerShell
    if (content.startsWith('!')) {
        execPowerShell(content.slice(1).trim());
        elements.userInput.value = '';
        elements.userInput.style.height = 'auto';
        return;
    }

    // Slash commands — handle locally, don't send to AI
    if (content.startsWith('/')) {
        handleSlashCommand(content);
        elements.userInput.value = '';
        elements.userInput.style.height = 'auto';
        return;
    }

    state._lastUserMessage = content;

    connectWebSocket();

    const send = () => {
        if (state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({
                type: 'message',
                content: content,
                session_id: state.currentSessionId,
            }));
            elements.userInput.value = '';
            elements.userInput.style.height = 'auto';

            removeEmptyState();
            appendMessage('user', content);
            createStreamingBubble();
            state.isStreaming = true;
        } else if (state.ws.readyState === WebSocket.CONNECTING) {
            setTimeout(send, 50);
        }
    };
    send();
}

// --- Slash Commands ---
function handleSlashCommand(input) {
    const parts = input.split(/\s+/);
    const cmd = parts[0].toLowerCase();
    const arg = parts.slice(1).join(' ');

    // Save command as user message (fire and forget)
    ensureSession().then(() => saveLocalMessage('user', input));

    switch (cmd) {
        case '/help':
            cmdHelp();
            break;
        case '/clear':
            cmdClear();
            break;
        case '/new':
            cmdNew();
            break;
        case '/theme':
            cmdTheme(arg);
            break;
        case '/lang':
            cmdLang(arg);
            break;
        case '/settings':
            cmdSettings();
            break;
        case '/export':
            cmdExport();
            break;
        case '/retry':
            cmdRetry();
            break;
        case '/model':
            cmdModel(arg);
            break;
        case '/skill':
            cmdSkill(arg);
            break;
        case '/search':
            cmdSkillSearch(arg);
            break;
        case '/kb':
            cmdKnowledge(arg);
            break;
        case '/pdf':
            cmdPdf(arg);
            break;
        case '/docs':
            window.open('/help/', '_blank');
            showSystemMessage(i18n._lang === 'zh'
                ? '文档已在新标签页中打开。'
                : 'Documentation opened in a new tab.');
            break;
        default:
            showSystemMessage(i18n._lang === 'zh'
                ? `未知命令: ${cmd}。输入 /help 查看可用命令。`
                : `Unknown command: ${cmd}. Type /help for available commands.`);
    }
}

function showSystemMessage(text) {
    removeEmptyState();
    saveLocalMessage('assistant', text);
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.style.fontStyle = 'italic';
    div.style.color = 'var(--text-secondary)';
    div.innerHTML = renderMarkdown(text);
    elements.messages.appendChild(div);
    scrollToBottom();
}

function cmdHelp() {
    const isZh = i18n._lang === 'zh';
    showSystemMessage(isZh
        ? `**可用命令**

| 命令 | 说明 |
|---------|-------------|
| \`/help\` | 显示此帮助信息 |
| \`/clear\` | 清除当前对话 |
| \`/new\` | 创建新对话 |
| \`/theme dark\\|light\` | 切换颜色主题 |
| \`/lang zh\\|en\` | 切换界面语言 |
| \`/settings\` | 打开设置面板 |
| \`/export\` | 导出对话为 Markdown |
| \`/retry\` | 重新生成上一次回复 |
| \`/model <name>\` | 快速切换 AI 模型 |
| \`/skill list\` | 列出已安装的技能 |
| \`/skill install <source>\` | 安装技能（路径、GitHub、URL） |
| \`/skill remove <name>\` | 移除技能 |
| \`/search <query>\` | 在 agentskills.io 上搜索技能 |
| \`!<command>\` | 执行 PowerShell 命令（例如 \`!Get-Date\`） |
| \`/kb list\` | 列出知识库条目 |
| \`/kb add <title>\\|<content>\` | 添加知识库条目 |
| \`/kb search <query>\` | 搜索知识库 |
| \`/kb delete <id>\` | 删除知识库条目 |
| \`/pdf <path>\` | 处理 PDF 文件并加入知识库 |
| \`/docs\` | 在新标签页中打开文档 |`
        : `**Available Commands**

| Command | Description |
|---------|-------------|
| \`/help\` | Show this help message |
| \`/clear\` | Clear current conversation |
| \`/new\` | Start a new conversation |
| \`/theme dark\\|light\` | Switch color theme |
| \`/lang zh\\|en\` | Switch interface language |
| \`/settings\` | Open settings panel |
| \`/export\` | Export conversation as Markdown |
| \`/retry\` | Regenerate last AI response |
| \`/model <name>\` | Quick-switch AI model |
| \`/skill list\` | List installed skills |
| \`/skill install <source>\` | Install a skill (path, GitHub, URL) |
| \`/skill remove <name>\` | Remove a skill |
| \`/search <query>\` | Search skills on agentskills.io |
| \`!<command>\` | Execute a PowerShell command (e.g., \`!Get-Date\`) |
| \`/kb list\` | List knowledge base entries |
| \`/kb add <title>\\|<content>\` | Add to knowledge base |
| \`/kb search <query>\` | Search knowledge base |
| \`/kb delete <id>\` | Delete a knowledge entry |
| \`/pdf <path>\` | Process PDF file → knowledge base |
| \`/docs\` | Open documentation in new tab |`);
}

function cmdClear() {
    elements.messages.innerHTML = '';
    showEmptyState();
}

function cmdNew() {
    newChat();
}

function cmdTheme(arg) {
    const theme = arg.toLowerCase();
    const isZh = i18n._lang === 'zh';
    if (theme === 'dark' || theme === 'light') {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('puppycli-theme', theme);
        elements.btnTheme.innerHTML = theme === 'dark' ? ICON_SUN : ICON_MOON;
        showSystemMessage(isZh
            ? `主题已切换至 **${theme === 'dark' ? '深色' : '浅色'}** 模式。`
            : `Theme switched to **${theme}** mode.`);
    } else {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        showSystemMessage(isZh
            ? `当前主题: **${current}**。用法: \`/theme dark\` 或 \`/theme light\``
            : `Current theme: **${current}**. Usage: \`/theme dark\` or \`/theme light\``);
    }
}

function cmdLang(arg) {
    const lang = arg.toLowerCase();
    const isZh = i18n._lang === 'zh';
    if (lang === 'zh' || lang === 'en') {
        i18n.set(lang);
        showSystemMessage(isZh
            ? `语言已切换为 **${lang === 'zh' ? '中文' : 'English'}**。`
            : `Language switched to **${lang === 'zh' ? '中文' : 'English'}**.`);
    } else if (!lang) {
        showSystemMessage(isZh
            ? `当前语言: **${i18n._lang === 'zh' ? '中文' : 'English'}**。用法: \`/lang zh\` 或 \`/lang en\``
            : `Current language: **${i18n._lang === 'zh' ? '中文' : 'English'}**. Usage: \`/lang zh\` or \`/lang en\``);
    } else {
        showSystemMessage(isZh
            ? `不支持的语言: **${lang}**。请使用 \`/lang zh\` 或 \`/lang en\``
            : `Unsupported language: **${lang}**. Use \`/lang zh\` or \`/lang en\``);
    }
}

function cmdSettings() {
    openSettings();
}

function cmdExport() {
    const isZh = i18n._lang === 'zh';
    const messages = elements.messages.querySelectorAll('.message');
    if (messages.length === 0) {
        showSystemMessage(isZh ? '没有可导出的内容。' : 'Nothing to export.');
        return;
    }

    let md = `# PuppyCLI Conversation\n\n`;
    md += `_Exported at ${new Date().toLocaleString()}_\n\n---\n\n`;

    messages.forEach(msg => {
        if (msg.classList.contains('user')) {
            md += `**You:**\n${msg.textContent}\n\n`;
        } else if (msg.classList.contains('assistant') && !msg.style.fontStyle) {
            const raw = msg.dataset.rawText || msg.textContent;
            md += `**PuppyCLI:**\n${raw}\n\n`;
        }
    });

    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `puppycli-export-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
    showSystemMessage(isZh
        ? '对话已导出为 Markdown 文件。'
        : 'Conversation exported as Markdown file.');
}

function cmdRetry() {
    const isZh = i18n._lang === 'zh';
    if (state.isStreaming) return;
    if (!state._lastUserMessage) {
        showSystemMessage(isZh
            ? '没有可重试的消息。请先发送一条消息。'
            : 'Nothing to retry. Send a message first.');
        return;
    }

    // Remove last assistant bubble if present
    const msgs = elements.messages.querySelectorAll('.message.assistant');
    if (msgs.length > 0) {
        const lastAssistant = msgs[msgs.length - 1];
        if (!lastAssistant.style.fontStyle) {
            lastAssistant.remove();
        }
    }

    connectWebSocket();

    const send = () => {
        if (state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({
                type: 'message',
                content: state._lastUserMessage,
                session_id: state.currentSessionId,
            }));
            createStreamingBubble();
            state.isStreaming = true;
        } else if (state.ws.readyState === WebSocket.CONNECTING) {
            setTimeout(send, 50);
        }
    };
    send();
}

function cmdModel(arg) {
    const isZh = i18n._lang === 'zh';
    const model = arg.trim();
    if (!model) {
        showSystemMessage(isZh
            ? '用法: `/model <name>`。例如: `/model deepseek-chat`'
            : 'Usage: `/model <name>`. Example: `/model deepseek-chat`');
        return;
    }
    fetch('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
    })
        .then(r => r.json())
        .then(() => {
            showSystemMessage(isZh
                ? `模型已切换至 **${model}**（下一条消息生效）。`
                : `Model switched to **${model}** (next message will use it).`);
        })
        .catch(() => {
            showSystemMessage(isZh
                ? '模型切换失败，请检查设置。'
                : 'Failed to switch model. Check settings.');
        });
}

async function cmdSkill(arg) {
    const isZh = i18n._lang === 'zh';
    const parts = arg.split(/\s+/);
    const action = parts[0]?.toLowerCase();
    const target = parts.slice(1).join(' ');

    if (!action || action === 'list') {
        try {
            const resp = await fetch('/api/skills');
            const skills = await resp.json();
            if (skills.length === 0) {
                showSystemMessage(isZh
                    ? '没有已安装的技能。使用 `/skill install <source>` 安装，或 `/search <query>` 搜索技能。'
                    : 'No skills installed. Use `/skill install <source>` to install one, or `/search <query>` to find skills.');
                return;
            }
            let md = isZh
                ? '**已安装技能**\n\n| 名称 | 描述 | 位置 |\n|------|-------------|----------|\n'
                : '**Installed Skills**\n\n| Name | Description | Location |\n|------|-------------|----------|\n';
            skills.forEach(s => {
                md += `| \`${s.name}\` | ${s.description.slice(0, 80)} | ${s.location} |\n`;
            });
            md += isZh
                ? '\n使用 `/skill remove <name>` 移除技能。'
                : '\nUse `/skill remove <name>` to remove a skill.';
            showSystemMessage(md);
        } catch (e) {
            showSystemMessage((isZh ? '获取技能列表失败: ' : 'Failed to list skills: ') + e.message);
        }
    } else if (action === 'install') {
        if (!target) {
            showSystemMessage(isZh
                ? '用法: `/skill install <github repo | URL | 本地路径>`。例如: `/skill install anthropics/skills`'
                : 'Usage: `/skill install <github repo | URL | local path>`. Example: `/skill install anthropics/skills`');
            return;
        }
        showSystemMessage(isZh ? `正在从 **${target}** 安装技能...` : `Installing skill from **${target}**...`);
        try {
            const resp = await fetch('/api/skills/install', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: target }),
            });
            if (resp.ok) {
                const data = await resp.json();
                showSystemMessage(isZh
                    ? `技能 **${data.skill.name}** 安装成功！输入 /skill list 查看所有技能。`
                    : `Skill **${data.skill.name}** installed successfully! Type /skill list to see all skills.`);
            } else {
                const err = await resp.json();
                showSystemMessage((isZh ? '安装失败: ' : 'Install failed: ') + (err.detail || resp.statusText));
            }
        } catch (e) {
            showSystemMessage((isZh ? '安装技能失败: ' : 'Failed to install skill: ') + e.message);
        }
    } else if (action === 'remove') {
        if (!target) {
            showSystemMessage(isZh
                ? '用法: `/skill remove <name>`。使用 `/skill list` 查看已安装技能。'
                : 'Usage: `/skill remove <name>`. Use `/skill list` to see installed skills.');
            return;
        }
        try {
            const resp = await fetch(`/api/skills/${target}`, { method: 'DELETE' });
            if (resp.ok) {
                showSystemMessage(isZh ? `技能 **${target}** 已移除。` : `Skill **${target}** removed.`);
            } else {
                const err = await resp.json();
                showSystemMessage((isZh ? '移除失败: ' : 'Remove failed: ') + (err.detail || resp.statusText));
            }
        } catch (e) {
            showSystemMessage((isZh ? '移除技能失败: ' : 'Failed to remove skill: ') + e.message);
        }
    } else {
        showSystemMessage(isZh
            ? `未知的技能操作: **${action}**。请使用 \`/skill list\`、\`/skill install\` 或 \`/skill remove\`。`
            : `Unknown skill action: **${action}**. Use \`/skill list\`, \`/skill install\`, or \`/skill remove\`.`);
    }
}

async function cmdSkillSearch(query) {
    const isZh = i18n._lang === 'zh';
    if (!query.trim()) {
        showSystemMessage(isZh
            ? '用法: `/search <query>`。例如: `/search pdf processing`'
            : 'Usage: `/search <query>`. Example: `/search pdf processing`');
        return;
    }
    showSystemMessage(isZh
        ? `正在 agentskills.io 上搜索 **${query}**...`
        : `Searching for **${query}** on agentskills.io...`);
    try {
        const resp = await fetch(`/api/skills/search?q=${encodeURIComponent(query)}&limit=10`);
        const results = await resp.json();
        if (results.length === 0) {
            showSystemMessage(isZh
                ? `未找到与 **${query}** 相关的技能。请尝试其他关键词。`
                : `No skills found for **${query}**. Try a different keyword.`);
            return;
        }
        let md = isZh
            ? `**搜索 "${query}" 的结果**\n\n| 名称 | 描述 | 来源 |\n|------|-------------|--------|\n`
            : `**Search Results for "${query}"**\n\n| Name | Description | Source |\n|------|-------------|--------|\n`;
        results.forEach(r => {
            const desc = (r.description || '').slice(0, 60);
            const src = r.source ? `[repo](${r.source})` : '-';
            md += `| \`${r.name}\` | ${desc} | ${src} |\n`;
        });
        md += isZh
            ? `\n安装: \`/skill install <source>\` (例如 \`/skill install ${results[0].source || results[0].name}\`)`
            : `\nTo install: \`/skill install <source>\` (e.g., \`/skill install ${results[0].source || results[0].name}\`)`;
        showSystemMessage(md);
    } catch (e) {
        showSystemMessage((isZh ? '搜索失败: ' : 'Search failed: ') + e.message);
    }
}

async function execPowerShell(command) {
    const isZh = i18n._lang === 'zh';
    if (!command) return;

    await ensureSession();
    saveLocalMessage('user', '!' + command);

    removeEmptyState();
    appendMessage('user', '!' + command);

    const resultDiv = document.createElement('div');
    resultDiv.className = 'message assistant';
    resultDiv.innerHTML = renderMarkdown(
        (isZh ? '运行中: `' : 'Running: `') + escapeHtml(command) + '`...');
    elements.messages.appendChild(resultDiv);
    scrollToBottom();

    try {
        const resp = await fetch('/api/powershell', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command }),
        });
        const data = await resp.json();

        let output = '';
        if (data.stdout) {
            output += '```\n' + data.stdout + '\n```';
        }
        if (data.stderr) {
            output += '\n\n**Stderr:**\n```\n' + data.stderr + '\n```';
        }
        if (data.returncode !== 0 && !data.stderr && !data.stdout) {
            output += '\n_Exit code: ' + data.returncode + '_';
        }
        if (!output.trim()) {
            const noOutput = isZh ? '(无输出)' : '(no output)';
            output = '_' + noOutput + '_';
            saveLocalMessage('assistant', noOutput);
        } else {
            saveLocalMessage('assistant', output);
        }

        resultDiv.innerHTML = renderMarkdown(output);
    } catch (e) {
        const errMsg = (isZh ? '错误: ' : 'Error: ') + e.message;
        saveLocalMessage('assistant', errMsg);
        resultDiv.innerHTML = renderMarkdown('**' + errMsg + '**');
    }
    scrollToBottom();
}

async function cmdKnowledge(arg) {
    const isZh = i18n._lang === 'zh';
    const parts = arg.split(/\s+/);
    const action = parts[0]?.toLowerCase();
    const rest = parts.slice(1).join(' ');

    if (!action || action === 'list') {
        try {
            const resp = await fetch('/api/kb');
            const entries = await resp.json();
            if (entries.length === 0) {
                showSystemMessage(isZh
                    ? '知识库为空。使用 `/kb add <title>|<content>` 添加条目。'
                    : 'Knowledge base is empty. Use `/kb add <title>|<content>` to add entries.');
                return;
            }
            let md = isZh
                ? `**知识库** (${entries.length} 条)\n\n| ID | 标题 | 标签 | 预览 |\n|----|-------|------|---------|\n`
                : `**Knowledge Base** (${entries.length} entries)\n\n| ID | Title | Tags | Preview |\n|----|-------|------|---------|\n`;
            entries.forEach(e => {
                md += `| \`${e.id}\` | ${e.title} | ${(e.tags||[]).join(', ')} | ${(e.preview||'').slice(0, 50)} |\n`;
            });
            md += isZh
                ? '\n使用 `/kb search <query>` 搜索，`/kb delete <id>` 删除。'
                : '\nUse `/kb search <query>` to search, `/kb delete <id>` to remove.';
            showSystemMessage(md);
        } catch (e) {
            showSystemMessage((isZh ? '失败: ' : 'Failed: ') + e.message);
        }
    } else if (action === 'add') {
        const pipeIdx = rest.indexOf('|');
        if (pipeIdx < 0) {
            showSystemMessage(isZh
                ? '用法: `/kb add <title>|<content>`。使用竖线 `|` 分隔标题和内容。'
                : 'Usage: `/kb add <title>|<content>`. Use pipe `|` to separate title and content.');
            return;
        }
        const title = rest.slice(0, pipeIdx).trim();
        const content = rest.slice(pipeIdx + 1).trim();
        if (!title || !content) {
            showSystemMessage(isZh ? '标题和内容均为必填。' : 'Both title and content are required.');
            return;
        }
        try {
            const resp = await fetch('/api/kb', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, content }),
            });
            if (resp.ok) {
                const data = await resp.json();
                showSystemMessage(isZh
                    ? `知识条目 **${data.entry.id}** 已添加: _${title}_`
                    : `Knowledge entry **${data.entry.id}** added: _${title}_`);
            } else {
                const err = await resp.json();
                showSystemMessage((isZh ? '失败: ' : 'Failed: ') + err.detail);
            }
        } catch (e) {
            showSystemMessage((isZh ? '失败: ' : 'Failed: ') + e.message);
        }
    } else if (action === 'search') {
        if (!rest) {
            showSystemMessage(isZh ? '用法: `/kb search <query>`' : 'Usage: `/kb search <query>`');
            return;
        }
        try {
            const resp = await fetch(`/api/kb/search?q=${encodeURIComponent(rest)}`);
            const results = await resp.json();
            if (results.length === 0) {
                showSystemMessage(isZh
                    ? `未找到与 **${rest}** 相关的内容。`
                    : `Nothing found for **${rest}**.`);
                return;
            }
            let md = (isZh ? `**搜索: "${rest}"**\n\n` : `**Search: "${rest}"**\n\n`);
            results.forEach(r => {
                md += `### ${r.title}\n\`${r.id}\` | tags: ${(r.tags||[]).join(', ')}\n\n${r.content}\n\n---\n`;
            });
            showSystemMessage(md);
        } catch (e) {
            showSystemMessage((isZh ? '搜索失败: ' : 'Search failed: ') + e.message);
        }
    } else if (action === 'delete') {
        const entryId = rest.trim();
        if (!entryId) {
            showSystemMessage(isZh ? '用法: `/kb delete <id>`' : 'Usage: `/kb delete <id>`');
            return;
        }
        try {
            const resp = await fetch(`/api/kb/${entryId}`, { method: 'DELETE' });
            if (resp.ok) {
                showSystemMessage(isZh ? `条目 **${entryId}** 已删除。` : `Entry **${entryId}** deleted.`);
            } else {
                showSystemMessage(isZh ? '删除失败: 条目未找到。' : 'Delete failed: entry not found.');
            }
        } catch (e) {
            showSystemMessage((isZh ? '失败: ' : 'Failed: ') + e.message);
        }
    } else {
        showSystemMessage(isZh
            ? `未知的知识库操作: **${action}**。请使用 \`/kb list\`、\`/kb add\`、\`/kb search\` 或 \`/kb delete\`。`
            : `Unknown kb action: **${action}**. Use \`/kb list\`, \`/kb add\`, \`/kb search\`, or \`/kb delete\`.`);
    }
}

async function cmdPdf(path) {
    const isZh = i18n._lang === 'zh';
    if (!path.trim()) {
        showSystemMessage(isZh
            ? '用法: `/pdf <file_path>`。例如: `/pdf C:\\Users\\me\\doc.pdf`'
            : 'Usage: `/pdf <file_path>`. Example: `/pdf C:\\Users\\me\\doc.pdf`');
        return;
    }
    showSystemMessage(isZh ? `正在处理 PDF: **${path}**...` : `Processing PDF: **${path}**...`);
    try {
        const resp = await fetch('/api/pdf/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: path }),
        });
        if (resp.ok) {
            const data = await resp.json();
            showSystemMessage(
                (isZh
                    ? `PDF 处理成功 (${data.mode} 模式)。\n\n**知识条目:** \`${data.kb_entry_id}\`\n**文件:** ${data.filename}\n\n**预览:**\n${data.preview}...\n\n使用 \`/kb search\` 在知识库中查找。`
                    : `PDF processed successfully (${data.mode} mode).\n\n**KB Entry:** \`${data.kb_entry_id}\`\n**File:** ${data.filename}\n\n**Preview:**\n${data.preview}...\n\nUse \`/kb search\` to find it in your knowledge base.`)
            );
        } else {
            const err = await resp.json();
            showSystemMessage((isZh ? 'PDF 处理失败: ' : 'PDF processing failed: ') + err.detail);
        }
    } catch (e) {
        showSystemMessage((isZh ? 'PDF 处理失败: ' : 'PDF processing failed: ') + e.message);
    }
}

// --- Messages ---
function appendMessage(role, content) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    if (role === 'assistant') {
        div.innerHTML = renderMarkdown(content);
    } else {
        div.textContent = content;
    }
    elements.messages.appendChild(div);
    scrollToBottom();
    return div;
}

let _streamingBubble = null;

function createStreamingBubble() {
    _streamingBubble = document.createElement('div');
    _streamingBubble.className = 'message assistant streaming';
    elements.messages.appendChild(_streamingBubble);
    scrollToBottom();
}

function appendToken(token) {
    if (!_streamingBubble) {
        createStreamingBubble();
    }
    const currentText = _streamingBubble.dataset.rawText || '';
    const newText = currentText + token;
    _streamingBubble.dataset.rawText = newText;
    _streamingBubble.innerHTML = renderMarkdown(newText);
    scrollToBottom();
}

function finishStreaming() {
    if (_streamingBubble) {
        _streamingBubble.classList.remove('streaming');
        _streamingBubble = null;
    }
    state.isStreaming = false;
    elements.userInput.focus();
}

function showError(message) {
    const isZh = i18n._lang === 'zh';
    finishStreaming();
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.style.color = '#e03131';
    div.textContent = (isZh ? '错误: ' : 'Error: ') + message;
    elements.messages.appendChild(div);
    scrollToBottom();
    state.isStreaming = false;
}

// --- Confirm Card ---
function showConfirmCard(confirmId, command, reason) {
    finishStreaming();
    state.isStreaming = true;  // keep input disabled while waiting

    const isZh = i18n._lang === 'zh';
    const card = document.createElement('div');
    card.className = 'confirm-card';
    card.id = 'confirm-' + confirmId;
    card.innerHTML =
        `<div class="confirm-card-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span>${isZh ? 'Agent 想要修改本地文件' : 'Agent wants to modify local files'}</span>
        </div>
        <div class="confirm-card-body">
            <div class="confirm-card-cmd"><code>${escapeHtml(command)}</code></div>
            <div class="confirm-card-reason">${escapeHtml(reason)}</div>
        </div>
        <div class="confirm-card-actions">
            <button class="confirm-card-allow" id="confirm-allow-${confirmId}">${isZh ? '✓ 允许执行' : '✓ Allow'}</button>
            <button class="confirm-card-deny" id="confirm-deny-${confirmId}">${isZh ? '✗ 拒绝' : '✗ Deny'}</button>
        </div>`;

    removeEmptyState();
    elements.messages.appendChild(card);
    scrollToBottom();

    function respond(allowed) {
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({
                type: 'confirm_response',
                confirm_id: confirmId,
                allowed: allowed,
            }));
        }
        const resultText = allowed
            ? (isZh ? '✓ 已允许执行' : '✓ Execution allowed')
            : (isZh ? '✗ 已拒绝' : '✗ Execution denied');
        card.innerHTML = `<div class="confirm-card-result">${resultText}</div>`;
        card.classList.add('confirm-card-resolved');
        state.isStreaming = false;
        elements.userInput.focus();
    }

    document.getElementById('confirm-allow-' + confirmId).addEventListener('click', () => respond(true));
    document.getElementById('confirm-deny-' + confirmId).addEventListener('click', () => respond(false));
}

// --- Markdown Rendering ---
function renderMarkdown(text) {
    if (typeof marked.setOptions === 'function') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            highlight: function (code, lang) {
                if (typeof hljs !== 'undefined') {
                    if (lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    }
                    return hljs.highlightAuto(code).value;
                }
                return code;
            },
        });
    }

    let html = text;

    // Preprocess LaTeX blocks $$...$$ before markdown
    const latexBlocks = [];
    html = html.replace(/\$\$([\s\S]*?)\$\$/g, (_, formula) => {
        latexBlocks.push({ type: 'block', formula });
        return `%%LATEX_BLOCK_${latexBlocks.length - 1}%%`;
    });
    // Preprocess inline LaTeX $...$
    html = html.replace(/\$(.*?)\$/g, (_, formula) => {
        latexBlocks.push({ type: 'inline', formula });
        return `%%LATEX_INLINE_${latexBlocks.length - 1}%%`;
    });

    // Render markdown
    html = marked.parse(html);

    // Restore LaTeX
    html = html.replace(/<p>%%LATEX_BLOCK_(\d+)%%<\/p>/g, (_, idx) => {
        const item = latexBlocks[parseInt(idx)];
        try {
            return katex.renderToString(item.formula, { displayMode: true });
        } catch (e) {
            return `<code>${escapeHtml(item.formula)}</code>`;
        }
    });
    html = html.replace(/%%LATEX_BLOCK_(\d+)%%/g, (_, idx) => {
        const item = latexBlocks[parseInt(idx)];
        try {
            return katex.renderToString(item.formula, { displayMode: true });
        } catch (e) {
            return `<code>${escapeHtml(item.formula)}</code>`;
        }
    });
    html = html.replace(/%%LATEX_INLINE_(\d+)%%/g, (_, idx) => {
        const item = latexBlocks[parseInt(idx)];
        try {
            return katex.renderToString(item.formula, { displayMode: false });
        } catch (e) {
            return `<code>${escapeHtml(item.formula)}</code>`;
        }
    });

    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// --- Sessions ---
async function loadSessions() {
    try {
        const resp = await fetch('/api/sessions');
        const sessions = await resp.json();
        renderSessionList(sessions);
    } catch (e) {
        console.error('Failed to load sessions:', e);
    }
}

function renderSessionList(sessions) {
    elements.sessionList.innerHTML = '';
    sessions.forEach(s => {
        const div = document.createElement('div');
        div.className = 'session-item';
        if (s.id === state.currentSessionId) {
            div.classList.add('active');
        }

        const title = document.createElement('span');
        title.className = 'item-title';
        title.textContent = s.title || (i18n._lang === 'zh' ? '未命名' : 'Untitled');

        const actions = document.createElement('span');
        actions.className = 'item-actions';

        const renameBtn = document.createElement('button');
        renameBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
        renameBtn.title = i18n.t('rename');
        renameBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            startRename(s.id, title, div);
        });

        const deleteBtn = document.createElement('button');
        deleteBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>';
        deleteBtn.title = i18n.t('delete');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteSession(s.id);
        });

        actions.appendChild(renameBtn);
        actions.appendChild(deleteBtn);
        div.appendChild(title);
        div.appendChild(actions);

        div.addEventListener('click', () => loadSession(s.id));
        elements.sessionList.appendChild(div);
    });
}

async function loadSession(sessionId) {
    try {
        const resp = await fetch(`/api/sessions/${sessionId}`);
        const data = await resp.json();
        state.currentSessionId = sessionId;
        elements.messages.innerHTML = '';
        removeEmptyState();
        if (!data.messages || data.messages.length === 0) {
            // Show empty state if no messages
            showEmptyState();
        } else {
            data.messages.forEach(msg => {
                appendMessage(msg.role, msg.content);
            });
        }
        loadSessions();
    } catch (e) {
        console.error('Failed to load session:', e);
    }
}

function newChat() {
    state.currentSessionId = null;
    state.isStreaming = false;
    elements.messages.innerHTML = '';
    showEmptyState();
    loadSessions();
}

async function startRename(sessionId, titleEl, itemEl) {
    const oldTitle = titleEl.textContent;
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'rename-input';
    input.value = oldTitle;
    itemEl.replaceChild(input, titleEl);
    // Hide actions during rename
    const actions = itemEl.querySelector('.item-actions');
    if (actions) actions.style.display = 'none';
    input.focus();
    input.select();

    const finish = async () => {
        const newTitle = input.value.trim() || oldTitle;
        try {
            const resp = await fetch(`/api/sessions/${sessionId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle }),
            });
            if (!resp.ok) {
                console.error('Rename failed:', resp.status);
            }
        } catch (e) {
            console.error('Rename failed:', e);
        }
        titleEl.textContent = newTitle;
        itemEl.replaceChild(titleEl, input);
        if (actions) actions.style.display = '';
        // Refresh list to reflect server state
        loadSessions();
    };

    input.addEventListener('blur', finish);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
        if (e.key === 'Escape') { input.value = oldTitle; input.blur(); }
    });
}

async function deleteSession(sessionId) {
    if (!confirm(i18n.t('delete-confirm'))) return;
    try {
        await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
        if (state.currentSessionId === sessionId) {
            newChat();
        } else {
            loadSessions();
        }
    } catch (e) {
        console.error('Delete failed:', e);
    }
}

function showEmptyState() {
    if (elements.messages.children.length === 0) {
        elements.messages.innerHTML = `
            <div class="empty-state">
                <img src="/logo.png" class="logo-icon" alt="PuppyCLI logo" onerror="this.style.display='none';this.nextElementSibling.style.display='block';"><span class="logo-icon-fallback" style="display:none;font-size:64px;">🐶</span>
                <p>PuppyCLI</p>
            </div>`;
    }
}

function removeEmptyState() {
    const empty = elements.messages.querySelector('.empty-state');
    if (empty) empty.remove();
}

// --- Settings ---
function openSettings() {
    fetch('/api/config')
        .then(r => r.json())
        .then(config => {
            const keyVal = config.api_key || '';
            $('#cfg-api-key').value = keyVal;
            $('#cfg-api-key').placeholder = keyVal ? '(already set — leave blank to keep)' : 'sk-...';
            $('#cfg-model').value = config.model || 'deepseek-chat';
            $('#cfg-base-url').value = config.base_url || 'https://api.deepseek.com';
            $('#cfg-python-env').value = config.python_env || '';
            $('#cfg-data-dir').value = config.data_dir || '';
        })
        .catch(() => {});
    elements.settingsModal.classList.remove('hidden');
    // Re-apply i18n in case modal was rendered before
    i18n.apply();
}

function closeSettings() {
    elements.settingsModal.classList.add('hidden');
}

async function saveSettings() {
    const isZh = i18n._lang === 'zh';
    const updates = {
        api_key: $('#cfg-api-key').value.trim(),
        model: $('#cfg-model').value.trim(),
        base_url: $('#cfg-base-url').value.trim(),
        python_env: $('#cfg-python-env').value.trim(),
        data_dir: $('#cfg-data-dir').value.trim(),
    };
    try {
        await fetch('/api/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates),
        });
        closeSettings();
    } catch (e) {
        alert((isZh ? '保存设置失败: ' : 'Failed to save settings: ') + e.message);
    }
}

// --- Helpers ---
function autoResizeTextarea() {
    const el = elements.userInput;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 240) + 'px';
}

function scrollToBottom() {
    elements.messages.scrollTop = elements.messages.scrollHeight;
}
