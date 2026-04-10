/**
 * Meeting Summarizer - Frontend Application
 */
class MeetingSummarizerApp {
    constructor() {
        this.currentTaskId = null;
        this.pollInterval = null;
        this.storageKeys = {
            apiKey: 'meeting_summarizer_yandex_api_key',
            folderId: 'meeting_summarizer_yandex_folder_id',
            gptKey: 'meeting_summarizer_yandex_gpt_api_key'
        };
        this.credentials = {
            apiKey: '',
            folderId: '',
            gptKey: ''
        };
        this.loadStoredCredentials();
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');

        // Клик по области загрузки
        uploadArea.addEventListener('click', () => fileInput.click());

        // Выбор файла
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelect(e.target.files[0]);
            }
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            
            if (e.dataTransfer.files.length > 0) {
                this.handleFileSelect(e.dataTransfer.files[0]);
            }
        });

        this.initializeCredentialControls();
        this.initializeInstructionsModal();
    }

    initializeCredentialControls() {
        const saveBtn = document.getElementById('saveCredentialsBtn');
        const clearBtn = document.getElementById('clearCredentialsBtn');

        if (saveBtn) {
            saveBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.saveCredentials();
            });
        }

        if (clearBtn) {
            clearBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.clearCredentials();
            });
        }
    }

    initializeInstructionsModal() {
        const openBtn = document.getElementById('openInstructionsBtn');
        const modal = document.getElementById('instructionsModal');
        const overlay = document.getElementById('instructionsOverlay');
        const closeButtons = document.querySelectorAll('.instructions-close');

        if (!modal) return;

        const closeModal = () => modal.classList.add('hidden');
        const openModal = () => modal.classList.remove('hidden');

        if (openBtn) {
            openBtn.addEventListener('click', (e) => {
                e.preventDefault();
                openModal();
            });
        }

        if (overlay) {
            overlay.addEventListener('click', closeModal);
        }

        closeButtons.forEach((btn) => btn.addEventListener('click', closeModal));
    }

    loadStoredCredentials() {
        if (typeof window === 'undefined') return;

        this.credentials = {
            apiKey: localStorage.getItem(this.storageKeys.apiKey) || '',
            folderId: localStorage.getItem(this.storageKeys.folderId) || '',
            gptKey: localStorage.getItem(this.storageKeys.gptKey) || ''
        };

        const apiInput = document.getElementById('apiKeyInput');
        const folderInput = document.getElementById('folderIdInput');
        const gptInput = document.getElementById('gptKeyInput');

        if (apiInput) apiInput.value = this.credentials.apiKey;
        if (folderInput) folderInput.value = this.credentials.folderId;
        if (gptInput) gptInput.value = this.credentials.gptKey;
    }

    getCurrentCredentials() {
        const apiInput = document.getElementById('apiKeyInput');
        const folderInput = document.getElementById('folderIdInput');
        const gptInput = document.getElementById('gptKeyInput');

        return {
            apiKey: apiInput ? apiInput.value.trim() : '',
            folderId: folderInput ? folderInput.value.trim() : '',
            gptKey: gptInput ? gptInput.value.trim() : ''
        };
    }

    saveCredentials() {
        const creds = this.getCurrentCredentials();

        if (typeof window !== 'undefined') {
            localStorage.setItem(this.storageKeys.apiKey, creds.apiKey);
            localStorage.setItem(this.storageKeys.folderId, creds.folderId);
            localStorage.setItem(this.storageKeys.gptKey, creds.gptKey);
        }

        this.credentials = creds;

        const saveBtn = document.getElementById('saveCredentialsBtn');
        if (saveBtn) {
            const originalText = saveBtn.textContent;
            saveBtn.textContent = 'Сохранено ✅';
            setTimeout(() => (saveBtn.textContent = originalText), 2000);
        }
    }

    clearCredentials() {
        if (typeof window !== 'undefined') {
            localStorage.removeItem(this.storageKeys.apiKey);
            localStorage.removeItem(this.storageKeys.folderId);
            localStorage.removeItem(this.storageKeys.gptKey);
        }

        this.credentials = { apiKey: '', folderId: '', gptKey: '' };

        const apiInput = document.getElementById('apiKeyInput');
        const folderInput = document.getElementById('folderIdInput');
        const gptInput = document.getElementById('gptKeyInput');

        if (apiInput) apiInput.value = '';
        if (folderInput) folderInput.value = '';
        if (gptInput) gptInput.value = '';
    }

    handleFileSelect(file) {
        // Валидация файла
        const allowedTypes = ['.mp4', '.mp3', '.wav', '.ogg'];
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(fileExt)) {
            alert('Неподдерживаемый формат файла. Разрешены: MP4, MP3, WAV, OGG');
            return;
        }

        // Проверка размера (2GB)
        const maxSize = 2 * 1024 * 1024 * 1024;
        if (file.size > maxSize) {
            alert('Файл слишком большой. Максимальный размер: 2GB');
            return;
        }

        // Показываем информацию о файле
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileInfo').classList.remove('hidden');

        // Загружаем файл
        this.uploadFile(file);
    }

    async uploadFile(file) {
        try {
            this.showProgress(true);
            document.getElementById('resultsSection').classList.add('hidden');
            
            const formData = new FormData();
            formData.append('file', file);

            const creds = this.getCurrentCredentials();
            if (creds.apiKey) formData.append('yandex_api_key', creds.apiKey);
            if (creds.folderId) formData.append('yandex_folder_id', creds.folderId);
            if (creds.gptKey) formData.append('yandex_gpt_api_key', creds.gptKey);

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка загрузки файла');
            }

            const result = await response.json();
            this.currentTaskId = result.task_id;

            // Начинаем опрос статуса
            this.startPolling();

        } catch (error) {
            console.error('Ошибка:', error);
            alert('Произошла ошибка при загрузке файла: ' + error.message);
            this.showProgress(false);
        }
    }

    startPolling() {
        // Очищаем предыдущий интервал если есть
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        
        // Проверяем статус сразу
        this.checkStatus();
        
        // Затем каждые 2 секунды
        this.pollInterval = setInterval(() => this.checkStatus(), 2000);
    }

    async checkStatus() {
        if (!this.currentTaskId) return;

        try {
            const response = await fetch(`/api/status/${this.currentTaskId}`);
            
            if (!response.ok) {
                throw new Error('Ошибка проверки статуса');
            }

            const status = await response.json();
            this.updateProgress(status.progress, status.message);

            if (status.status === 'completed') {
                clearInterval(this.pollInterval);
                await this.loadResults();
            } else if (status.status === 'failed') {
                clearInterval(this.pollInterval);
                alert(`Ошибка обработки: ${status.message}`);
                this.showProgress(false);
            }

        } catch (error) {
            console.error('Ошибка проверки статуса:', error);
        }
    }

    updateProgress(percent, message) {
        document.getElementById('progressBar').style.width = `${percent}%`;
        document.getElementById('progressPercent').textContent = `${percent}%`;
        document.getElementById('progressMessage').textContent = message;
    }

    async loadResults() {
        try {
            const response = await fetch(`/api/result/${this.currentTaskId}`);
            
            if (!response.ok) {
                throw new Error('Ошибка загрузки результатов');
            }

            const result = await response.json();
            this.displayResults(result);
            this.showProgress(false);
            document.getElementById('resultsSection').classList.remove('hidden');

        } catch (error) {
            console.error('Ошибка загрузки результатов:', error);
            alert('Ошибка загрузки результатов: ' + error.message);
        }
    }

    displayResults(result) {
        // Summary
        const summary = result.summary || {};
        const summaryHtml = `
            <div class="bg-blue-50 p-6 rounded-lg mb-4">
                <h3 class="font-bold text-xl mb-2 text-blue-900">
                    <i class="fas fa-lightbulb mr-2"></i>
                    ${summary.topic || 'Встреча'}
                </h3>
                <p class="text-gray-700 mb-4">${summary.overall_summary || ''}</p>
                ${summary.key_points && summary.key_points.length > 0 ? `
                    <div class="mt-4">
                        <h4 class="font-semibold mb-2 text-blue-900">Ключевые моменты:</h4>
                        <ul class="list-disc list-inside space-y-1">
                            ${summary.key_points.map(point => `<li class="text-gray-700">${point}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div class="bg-gray-50 p-4 rounded">
                    <strong class="text-gray-700">Участников:</strong> 
                    <span class="text-gray-900">${result.speakers ? result.speakers.length : 0}</span>
                </div>
                <div class="bg-gray-50 p-4 rounded">
                    <strong class="text-gray-700">Длительность:</strong> 
                    <span class="text-gray-900">${this.formatDuration(result.duration || 0)}</span>
                </div>
            </div>
        `;
        document.getElementById('summaryContent').innerHTML = summaryHtml;

        // Speakers
        if (result.speakers && result.speakers.length > 0) {
            const speakersHtml = result.speakers.map((speaker, idx) => {
                const segmentsHtml = speaker.segments && speaker.segments.length > 0
                    ? speaker.segments.map(seg => `
                        <div class="mb-2 p-3 bg-gray-50 rounded transcript-segment">
                            <p class="text-gray-800">${seg.text}</p>
                        </div>
                    `).join('')
                    : '<p class="text-gray-500 italic">Нет реплик</p>';

                return `
                    <div class="bg-gray-50 p-6 rounded-lg mb-4">
                        <h3 class="font-bold text-lg mb-3 text-gray-800">
                            <i class="fas fa-user-circle mr-2 text-blue-600"></i>
                            ${speaker.name || `Спикер ${speaker.speaker_id}`}
                        </h3>
                        <p class="text-sm text-gray-600 mb-3">
                            <strong>Резюме:</strong> ${speaker.summary || 'Нет резюме'}
                        </p>
                        <div class="mt-4">
                            <h4 class="font-semibold mb-2 text-gray-700">Реплики:</h4>
                            ${segmentsHtml}
                        </div>
                    </div>
                `;
            }).join('');
            document.getElementById('speakersContent').innerHTML = speakersHtml;
        } else {
            document.getElementById('speakersContent').innerHTML = 
                '<p class="text-gray-500">Информация о спикерах недоступна</p>';
        }

        // Transcription
        const transcription = result.transcription || '';
        const transcriptionHtml = `
            <div class="bg-gray-50 p-4 rounded">
                <p class="text-gray-800 whitespace-pre-wrap">${transcription}</p>
            </div>
        `;
        document.getElementById('transcriptionContent').innerHTML = transcriptionHtml;
    }

    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    showProgress(show) {
        const progressSection = document.getElementById('progressSection');
        if (show) {
            progressSection.classList.remove('hidden');
        } else {
            progressSection.classList.add('hidden');
        }
    }
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    new MeetingSummarizerApp();
});

