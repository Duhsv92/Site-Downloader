/* ============================================
   SaveClip — Application Logic
   Integração com Cobalt API (self-hosted)
   ============================================ */

   document.addEventListener('DOMContentLoaded', () => {
    const DOWNLOAD_API = '/api/download';

    // --- DOM Elements ---
    const navbar = document.getElementById('navbar');
    const urlInput = document.getElementById('url-input');
    const pasteBtn = document.getElementById('paste-btn');
    const downloadBtn = document.getElementById('download-btn');
    const statusArea = document.getElementById('status-area');
    const resultCard = document.getElementById('result-card');
    const platformBtns = document.querySelectorAll('.platform-btn');
    const faqItems = document.querySelectorAll('.faq-item');

    let selectedPlatform = 'instagram';

    // =========================================
    // Navbar scroll effect
    // =========================================
    const handleScroll = () => {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });

    // =========================================
    // Platform selector
    // =========================================
    platformBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            platformBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedPlatform = btn.dataset.platform;

            const placeholders = {
                instagram: 'Cole o link do Instagram aqui...',
                facebook: 'Cole o link do Facebook aqui...',
                tiktok: 'Cole o link do TikTok aqui...'
            };
            urlInput.placeholder = placeholders[selectedPlatform];
            btn.style.transform = 'scale(0.95)';
            setTimeout(() => btn.style.transform = '', 150);
        });
    });

    // =========================================
    // Paste button
    // =========================================
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            urlInput.value = text;
            urlInput.focus();
            showStatus('📋 Link colado com sucesso!', 'success');
            autoDetectPlatform(text);
        } catch (err) {
            showStatus('Não foi possível acessar a área de transferência', 'error');
        }
    });

    // =========================================
    // Auto-detect platform from URL
    // =========================================
    function autoDetectPlatform(url) {
        const lower = url.toLowerCase();
        let detected = null;

        if (lower.includes('instagram.com') || lower.includes('instagr.am')) {
            detected = 'instagram';
        } else if (lower.includes('facebook.com') || lower.includes('fb.watch') || lower.includes('fb.com')) {
            detected = 'facebook';
        } else if (lower.includes('tiktok.com') || lower.includes('vm.tiktok.com')) {
            detected = 'tiktok';
        }

        if (detected) {
            platformBtns.forEach(b => {
                b.classList.toggle('active', b.dataset.platform === detected);
            });
            selectedPlatform = detected;
        }
    }

    urlInput.addEventListener('paste', () => {
        setTimeout(() => autoDetectPlatform(urlInput.value), 100);
    });

    // =========================================
    // Status messages
    // =========================================
    function showStatus(message, type = 'info') {
        statusArea.innerHTML = `
            <div class="status-message ${type}">
                ${getStatusIcon(type)}
                ${message}
            </div>
        `;

        if (type !== 'info') {
            setTimeout(() => {
                const msg = statusArea.querySelector('.status-message');
                if (msg) {
                    msg.style.opacity = '0';
                    msg.style.transform = 'translateY(-10px)';
                    setTimeout(() => statusArea.innerHTML = '', 300);
                }
            }, 6000);
        }
    }

    function getStatusIcon(type) {
        const icons = {
            error: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
            success: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
            info: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
        };
        return icons[type] || icons.info;
    }

    // =========================================
    // Validate URL
    // =========================================
    function validateUrl(url) {
        if (!url || url.trim() === '') {
            return { valid: false, message: 'Por favor, cole um link de vídeo' };
        }

        const patterns = {
            instagram: /^https?:\/\/(www\.)?(instagram\.com|instagr\.am)\/.+/i,
            facebook: /^https?:\/\/(www\.)?(facebook\.com|fb\.watch|fb\.com|m\.facebook\.com)\/.+/i,
            tiktok: /^https?:\/\/(www\.|vm\.)?(tiktok\.com)\/.+/i
        };

        let matchedPlatform = null;
        for (const [platform, pattern] of Object.entries(patterns)) {
            if (pattern.test(url)) {
                matchedPlatform = platform;
                break;
            }
        }

        if (!matchedPlatform) {
            return { valid: false, message: 'Link inválido. Use um link do Instagram, Facebook ou TikTok' };
        }

        return { valid: true, platform: matchedPlatform };
    }

    // =========================================
    // Download button handler
    // =========================================
    downloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        const validation = validateUrl(url);

        if (!validation.valid) {
            showStatus(validation.message, 'error');
            urlInput.focus();
            urlInput.parentElement.style.animation = 'shake 0.4s ease-in-out';
            setTimeout(() => urlInput.parentElement.style.animation = '', 400);
            return;
        }

        if (validation.platform !== selectedPlatform) {
            autoDetectPlatform(url);
        }

        // Start loading
        downloadBtn.classList.add('loading');
        downloadBtn.disabled = true;
        resultCard.classList.add('hidden');
        showStatus('⏳ Conectando à API...', 'info');

        try {
            await processWithCobalt(url);
        } catch (error) {
            console.error('Download error:', error);
            showStatus(error.message || 'Erro ao processar o vídeo. Tente novamente.', 'error');
        } finally {
            downloadBtn.classList.remove('loading');
            downloadBtn.disabled = false;
        }
    });

    // =========================================
    // COBALT API — Main Processing
    // =========================================
    async function processWithCobalt(url) {
        showStatus('⏳ Processando seu vídeo...', 'info');

        // Build request body according to Cobalt API docs
        // https://github.com/imputnet/cobalt/blob/main/docs/api.md
        const requestBody = {
            url: url,
            videoQuality: '1080',
            filenameStyle: 'pretty',
            downloadMode: 'auto'
        };

        let response;
        try {
            response = await fetch(DOWNLOAD_API, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
        } catch (networkError) {
            console.error('Network error:', networkError);
            throw new Error(
                '❌ Não foi possível conectar à API. Tente novamente em instantes.'
            );
        }

        // Handle HTTP errors
        if (!response.ok) {
            const errorHandlers = {
                429: 'Muitas requisições. Aguarde um momento e tente novamente.',
                401: 'Serviço temporariamente indisponível. Tente novamente mais tarde.',
                403: 'Acesso negado. Tente novamente mais tarde.',
                500: 'Erro interno do servidor. Tente novamente em instantes.',
                502: 'Serviço de download indisponível. Tente novamente em instantes.',
                503: 'Servidor sobrecarregado. Tente novamente em instantes.'
            };
            const msg = errorHandlers[response.status] || `Erro na API (HTTP ${response.status})`;
            throw new Error(`❌ ${msg}`);
        }

        let data;
        try {
            data = await response.json();
        } catch (parseError) {
            throw new Error('❌ Resposta inválida do servidor. Tente novamente.');
        }

        // Process response based on status field
        handleCobaltResponse(data, url);
    }

    // =========================================
    // Handle Cobalt API Response
    // =========================================
    // =========================================
    // Handle Cobalt API Response
    // =========================================
    function handleCobaltResponse(data, originalUrl) {
        switch (data.status) {
            case 'tunnel':
            case 'redirect':
                // Single file download — url + filename + thumb returned
                showSingleResult({
                    url: data.url,
                    filename: data.filename || 'video.mp4',
                    thumb: data.thumb || data.thumbnail || null
                }, originalUrl);
                break;

            case 'picker':
                // Multiple items (carousel, slideshow)
                showPickerResults(data, originalUrl);
                break;

            case 'error':
                handleCobaltError(data);
                break;

            default:
                throw new Error('❌ Resposta inesperada da API. Tente novamente.');
        }
    }

    function handleCobaltError(data) {
        // Cobalt returns error.code in the response
        const errorCode = data.error?.code || data.error || '';

        const errorMessages = {
            'error.api.link.invalid': 'Link inválido. Verifique o link e tente novamente.',
            'error.api.content.video.unavailable': 'Vídeo não encontrado ou indisponível.',
            'error.api.fetch.fail': 'Não foi possível acessar o vídeo. Ele pode ser privado ou ter sido removido.',
            'error.api.fetch.rate': 'Limite de requisições atingido. Tente novamente em alguns minutos.',
            'error.api.fetch.critical': 'Erro crítico ao buscar o vídeo. Tente novamente.',
            'error.api.service.unsupported': 'Esta plataforma não é suportada.',
            'error.api.service.disabled': 'Este serviço está desabilitado nesta instância.',
            'error.api.link.unsupported': 'Este tipo de link não é suportado.',
            'error.api.auth.key.missing': 'Serviço temporariamente indisponível. Tente novamente mais tarde.',
            'error.api.auth.jwt.missing': 'Esta instância requer autenticação Bearer.',
        };

        const msg = errorMessages[errorCode] || `Erro: ${errorCode || 'desconhecido'}`;
        throw new Error(`❌ ${msg}`);
    }

    // =========================================
    // Show Single Download Result & Auto-Trigger
    // =========================================
    function showSingleResult(data, originalUrl) {
        const resultTitle = document.getElementById('result-title');
        const resultMeta = document.getElementById('result-meta');
        const resultPreview = document.getElementById('result-preview');
        const actionsContainer = document.querySelector('.result-actions');

        const platformName = getPlatformName(originalUrl);
        resultTitle.textContent = `Vídeo do ${platformName}`;
        resultMeta.textContent = `📁 ${data.filename}`;

        // Render preview: Video player with poster or Image thumbnail
        const thumbUrl = data.thumb || data.thumbnail || null;
        const mediaUrl = data.url || null;

        if (mediaUrl) {
            const posterAttr = thumbUrl ? `poster="${escapeHtml(thumbUrl)}"` : '';
            resultPreview.innerHTML = `
                <video src="${escapeHtml(mediaUrl)}" ${posterAttr} controls muted loop playsinline preload="metadata" style="width:100%; height:100%; object-fit:cover;"></video>
            `;
        } else if (thumbUrl) {
            resultPreview.innerHTML = `
                <img src="${escapeHtml(thumbUrl)}" alt="Prévia do Vídeo" loading="lazy">
            `;
        } else {
            resultPreview.innerHTML = `
                <div class="preview-placeholder">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <polygon points="5 3 19 12 5 21 5 3"/>
                    </svg>
                </div>
            `;
        }

        // Build download buttons (Video and Audio MP3)
        actionsContainer.innerHTML = '';

        const videoBtn = createDownloadButton(data.url, data.filename, '🎬 Baixar Vídeo', true);
        actionsContainer.appendChild(videoBtn);

        const audioBtn = document.createElement('button');
        audioBtn.className = 'action-btn secondary';
        audioBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18V5l12-2v13"/>
                <circle cx="6" cy="18" r="3"/>
                <circle cx="18" cy="16" r="3"/>
            </svg>
            🎵 Baixar Áudio (MP3)
        `;
        audioBtn.onclick = (e) => {
            e.preventDefault();
            if (data.audio) {
                triggerDownload(data.audio, data.audioFilename || (data.filename ? data.filename.replace(/\.[^/.]+$/, "") + '.mp3' : 'audio.mp3'));
            } else {
                fetchAndDownloadAudio(originalUrl, data.filename);
            }
        };
        actionsContainer.appendChild(audioBtn);

        resultCard.classList.remove('hidden');
        showStatus('✅ Vídeo encontrado! Escolha se deseja baixar o vídeo ou apenas o áudio em MP3.', 'success');
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // =========================================
    // Show Picker (Multiple Items) Results
    // =========================================
    function showPickerResults(data, originalUrl) {
        const items = data.picker;
        const platformName = getPlatformName(originalUrl);

        if (!items || items.length === 0) {
            throw new Error('❌ Nenhum vídeo encontrado neste link.');
        }

        // Single item? Treat as single download
        if (items.length === 1) {
            showSingleResult({
                url: items[0].url,
                filename: `${platformName}_video.mp4`
            }, originalUrl);
            return;
        }

        const resultTitle = document.getElementById('result-title');
        const resultMeta = document.getElementById('result-meta');
        const resultPreview = document.getElementById('result-preview');
        const actionsContainer = document.querySelector('.result-actions');

        resultTitle.textContent = `${items.length} itens encontrados — ${platformName}`;
        resultMeta.textContent = 'Escolha qual mídia deseja baixar';

        // Show first thumbnail if available
        if (items[0].thumb) {
            resultPreview.innerHTML = `<img src="${escapeHtml(items[0].thumb)}" alt="Preview" loading="lazy">`;
        } else {
            resultPreview.innerHTML = `
                <div class="preview-placeholder">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <polygon points="5 3 19 12 5 21 5 3"/>
                    </svg>
                </div>
            `;
        }

        // Build picker buttons
        actionsContainer.innerHTML = '';

        items.forEach((item, index) => {
            const typeLabel = item.type === 'photo' ? '🖼️ Foto' :
                              item.type === 'gif' ? '🎞️ GIF' : '🎬 Vídeo';
            const ext = item.type === 'photo' ? '.jpg' : item.type === 'gif' ? '.gif' : '.mp4';
            const filename = `${platformName}_${index + 1}${ext}`;

            const btn = createDownloadButton(
                item.url,
                filename,
                `${typeLabel} ${index + 1}`,
                index === 0
            );

            // Hover to preview thumbnail
            if (item.thumb) {
                btn.addEventListener('mouseenter', () => {
                    resultPreview.innerHTML = `<img src="${escapeHtml(item.thumb)}" alt="Preview" loading="lazy">`;
                });
            }

            actionsContainer.appendChild(btn);
        });

        // "Download All" button
        const downloadAllBtn = document.createElement('button');
        downloadAllBtn.className = 'action-btn primary';
        downloadAllBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Baixar Todos
        `;
        downloadAllBtn.onclick = async () => {
            for (let i = 0; i < items.length; i++) {
                const ext = items[i].type === 'photo' ? '.jpg' : '.mp4';
                triggerDownload(items[i].url, `${platformName}_${i + 1}${ext}`);
                await new Promise(r => setTimeout(r, 600));
            }
            showStatus(`✅ ${items.length} downloads iniciados!`, 'success');
        };
        actionsContainer.appendChild(downloadAllBtn);

        // If there's background audio (e.g., TikTok slideshow)
        if (data.audio) {
            const audioBtn = createDownloadButton(
                data.audio,
                data.audioFilename || `${platformName}_audio.mp3`,
                '🎵 Áudio',
                false
            );
            actionsContainer.appendChild(audioBtn);
        }

        resultCard.classList.remove('hidden');
        showStatus(`✅ ${items.length} itens encontrados! Escolha qual baixar.`, 'success');
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // =========================================
    // Helper: Create download button
    // =========================================
    function createDownloadButton(url, filename, label, isPrimary) {
        const btn = document.createElement('a');
        btn.href = url;
        btn.className = `action-btn ${isPrimary ? 'primary' : 'secondary'}`;
        btn.target = '_blank';
        btn.rel = 'noopener noreferrer';
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            ${label}
        `;
        btn.onclick = (e) => {
            e.preventDefault();
            triggerDownload(url, filename);
        };
        return btn;
    }

    // =========================================
    // Trigger file download directly to device
    // =========================================
    async function triggerDownload(url, filename) {
        const targetFilename = filename || 'video.mp4';
        showStatus('📥 Salvando arquivo no seu dispositivo...', 'info');

        try {
            // Tenta obter como Blob para forçar o salvamento direto sem abrir em nova aba (mesmo em domínios diferentes)
            const response = await fetch(url);
            if (!response.ok) throw new Error('HTTP ' + response.status);
            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = blobUrl;
            a.download = targetFilename;
            document.body.appendChild(a);
            a.click();

            setTimeout(() => {
                if (document.body.contains(a)) {
                    document.body.removeChild(a);
                }
                URL.revokeObjectURL(blobUrl);
            }, 2000);

            showStatus('✅ Arquivo salvo no seu dispositivo!', 'success');
        } catch (err) {
            console.warn('Fallback para download direto por link:', err);

            // Fallback se o Blob for bloqueado por CORS no CDN: clica no link diretamente
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = targetFilename;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            document.body.appendChild(a);
            a.click();

            setTimeout(() => {
                if (document.body.contains(a)) {
                    document.body.removeChild(a);
                }
            }, 1000);

            showStatus('📥 Download iniciado no seu navegador!', 'success');
        }
    }

    // =========================================
    // Extract and download audio MP3
    // =========================================
    async function fetchAndDownloadAudio(url, baseFilename) {
        const audioFilename = (baseFilename || 'audio.mp4').replace(/\.[^/.]+$/, "") + '.mp3';
        showStatus('⏳ Extraindo áudio MP3...', 'info');

        try {
            const response = await fetch(DOWNLOAD_API, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    downloadMode: 'audio',
                    audioFormat: 'mp3',
                    audioBitrate: '320'
                })
            });

            if (!response.ok) throw new Error('HTTP ' + response.status);
            const data = await response.json();

            if (data.status === 'tunnel' || data.status === 'redirect') {
                triggerDownload(data.url, data.filename || audioFilename);
            } else if (data.url) {
                triggerDownload(data.url, audioFilename);
            } else if (data.status === 'error') {
                handleCobaltError(data);
            } else {
                throw new Error('Erro ao obter áudio.');
            }
        } catch (err) {
            console.error('Audio download error:', err);
            showStatus('❌ Não foi possível baixar o áudio em MP3. Tente baixar o vídeo.', 'error');
        }
    }

    // =========================================
    // Utility functions
    // =========================================
    function getPlatformName(url) {
        const lower = url.toLowerCase();
        if (lower.includes('instagram')) return 'Instagram';
        if (lower.includes('facebook') || lower.includes('fb.')) return 'Facebook';
        if (lower.includes('tiktok')) return 'TikTok';
        return 'Video';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // =========================================
    // Enter key to download
    // =========================================
    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') downloadBtn.click();
    });

    // =========================================
    // FAQ Accordion
    // =========================================
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        question.addEventListener('click', () => {
            const isActive = item.classList.contains('active');
            faqItems.forEach(i => i.classList.remove('active'));
            if (!isActive) item.classList.add('active');
        });
    });

    // =========================================
    // Scroll reveal animations
    // =========================================
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.platform-card, .step-card, .stat-card, .faq-item').forEach(el => {
        observer.observe(el);
    });

    // =========================================
    // Stats counter animation
    // =========================================
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                statsObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.3 });

    const statsSection = document.getElementById('stats-section');
    if (statsSection) statsObserver.observe(statsSection);

    function animateCounters() {
        document.querySelectorAll('.stat-number').forEach(counter => {
            const target = parseInt(counter.dataset.count);
            const duration = 2000;
            const start = Date.now();

            function update() {
                const progress = Math.min((Date.now() - start) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const current = Math.floor(eased * target);

                if (target >= 1000000) counter.textContent = (current / 1000000).toFixed(1) + 'M+';
                else if (target >= 1000) counter.textContent = (current / 1000).toFixed(0) + 'K+';
                else if (counter.closest('#stat-uptime')) counter.textContent = current + '%';
                else counter.textContent = current;

                if (progress < 1) requestAnimationFrame(update);
            }
            requestAnimationFrame(update);
        });
    }

    // =========================================
    // Smooth scroll for nav links
    // =========================================
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener('click', (e) => {
            const target = document.querySelector(link.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // --- Inject shake animation ---
    const style = document.createElement('style');
    style.textContent = `
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            20% { transform: translateX(-8px); }
            40% { transform: translateX(8px); }
            60% { transform: translateX(-4px); }
            80% { transform: translateX(4px); }
        }
    `;
    document.head.appendChild(style);
});
