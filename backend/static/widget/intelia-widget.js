/**
 * Intelia Chat Widget
 * VERSION 1.0.0
 *
 * Widget JavaScript pour intégration chat sur sites externes
 *
 * Usage:
 *   <script src="https://votre-domaine.com/widget/intelia-widget.js"></script>
 *   <script>
 *     InteliaWidget.init({
 *       apiUrl: 'https://votre-domaine.com/api/v1/widget',
 *       getToken: async () => {
 *         // Appeler votre serveur pour générer un JWT
 *         const response = await fetch('/api/widget-token');
 *         const data = await response.json();
 *         return data.token;
 *       },
 *       userId: 'user123',  // Optionnel
 *       userEmail: 'user@example.com',  // Optionnel
 *       position: 'bottom-right',  // 'bottom-right', 'bottom-left'
 *       primaryColor: '#2563eb',  // Couleur principale
 *       locale: 'fr'  // 'fr', 'en'
 *     });
 *   </script>
 */

(function() {
  'use strict';

  // Éviter double initialisation
  if (window.InteliaWidget) {
    console.warn('InteliaWidget déjà initialisé');
    return;
  }

  // Configuration par défaut
  const DEFAULT_CONFIG = {
    apiUrl: '',
    getToken: null,
    userId: null,
    userEmail: null,
    position: 'bottom-right',
    primaryColor: '#2563eb',
    locale: 'en',
    placeholder: {
      en: 'Ask your question...',
      fr: 'Posez votre question...',
      es: 'Haga su pregunta...',
      de: 'Stellen Sie Ihre Frage...',
      it: 'Fai la tua domanda...',
      pt: 'Faça sua pergunta...',
      nl: 'Stel uw vraag...',
      pl: 'Zadaj pytanie...',
      ja: '質問を入力してください...',
      zh: '请提问...',
      ar: 'اطرح سؤالك...',
      hi: 'अपना प्रश्न पूछें...',
      id: 'Ajukan pertanyaan Anda...',
      th: 'ถามคำถามของคุณ...',
      tr: 'Sorunuzu sorun...',
      vi: 'Đặt câu hỏi của bạn...'
    },
    welcomeMessage: {
      en: 'Hello! How can I help you?',
      fr: 'Bonjour ! Comment puis-je vous aider ?',
      es: '¡Hola! ¿Cómo puedo ayudarle?',
      de: 'Hallo! Wie kann ich Ihnen helfen?',
      it: 'Ciao! Come posso aiutarti?',
      pt: 'Olá! Como posso ajudá-lo?',
      nl: 'Hallo! Hoe kan ik u helpen?',
      pl: 'Cześć! Jak mogę Ci pomóc?',
      ja: 'こんにちは！どのようにお手伝いできますか？',
      zh: '您好！我能帮您什么？',
      ar: 'مرحبا! كيف يمكنني مساعدتك؟',
      hi: 'नमस्ते! मैं आपकी कैसे मदद कर सकता हूं?',
      id: 'Halo! Bagaimana saya bisa membantu Anda?',
      th: 'สวัสดี! ฉันจะช่วยคุณได้อย่างไร?',
      tr: 'Merhaba! Size nasıl yardımcı olabilirim?',
      vi: 'Xin chào! Tôi có thể giúp gì cho bạn?'
    },
    buttonLabel: {
      en: 'Need help?',
      fr: 'Besoin d\'aide ?',
      es: '¿Necesita ayuda?',
      de: 'Brauchen Sie Hilfe?',
      it: 'Hai bisogno di aiuto?',
      pt: 'Precisa de ajuda?',
      nl: 'Hulp nodig?',
      pl: 'Potrzebujesz pomocy?',
      ja: 'お困りですか？',
      zh: '需要帮助吗？',
      ar: 'هل تحتاج إلى مساعدة؟',
      hi: 'मदद चाहिए?',
      id: 'Butuh bantuan?',
      th: 'ต้องการความช่วยเหลือ?',
      tr: 'Yardıma mı ihtiyacınız var?',
      vi: 'Cần giúp đỡ?'
    },
    sendButton: {
      en: 'Send',
      fr: 'Envoyer',
      es: 'Enviar',
      de: 'Senden',
      it: 'Invia',
      pt: 'Enviar',
      nl: 'Verzenden',
      pl: 'Wyślij',
      ja: '送信',
      zh: '发送',
      ar: 'إرسال',
      hi: 'भेजें',
      id: 'Kirim',
      th: 'ส่ง',
      tr: 'Gönder',
      vi: 'Gửi'
    },
    errorMessages: {
      network: {
        en: 'Connection error. Please try again.',
        fr: 'Erreur de connexion. Veuillez réessayer.',
        es: 'Error de conexión. Por favor, inténtelo de nuevo.',
        de: 'Verbindungsfehler. Bitte versuchen Sie es erneut.',
        it: 'Errore di connessione. Riprova.',
        pt: 'Erro de conexão. Por favor, tente novamente.',
        nl: 'Verbindingsfout. Probeer het opnieuw.',
        pl: 'Błąd połączenia. Spróbuj ponownie.',
        ja: '接続エラー。もう一度お試しください。',
        zh: '连接错误。请重试。',
        ar: 'خطأ في الاتصال. يرجى المحاولة مرة أخرى.',
        hi: 'कनेक्शन त्रुटि। कृपया पुनः प्रयास करें।',
        id: 'Kesalahan koneksi. Silakan coba lagi.',
        th: 'ข้อผิดพลาดในการเชื่อมต่อ กรุณาลองอีกครั้ง',
        tr: 'Bağlantı hatası. Lütfen tekrar deneyin.',
        vi: 'Lỗi kết nối. Vui lòng thử lại.'
      },
      token: {
        en: 'Authentication error.',
        fr: 'Erreur d\'authentification.',
        es: 'Error de autenticación.',
        de: 'Authentifizierungsfehler.',
        it: 'Errore di autenticazione.',
        pt: 'Erro de autenticação.',
        nl: 'Authenticatiefout.',
        pl: 'Błąd uwierzytelniania.',
        ja: '認証エラー。',
        zh: '认证错误。',
        ar: 'خطأ في المصادقة.',
        hi: 'प्रमाणीकरण त्रुटि।',
        id: 'Kesalahan autentikasi.',
        th: 'ข้อผิดพลาดในการตรวจสอบสิทธิ์',
        tr: 'Kimlik doğrulama hatası.',
        vi: 'Lỗi xác thực.'
      },
      quota: {
        en: 'Usage limit reached.',
        fr: 'Limite d\'utilisation atteinte.',
        es: 'Límite de uso alcanzado.',
        de: 'Nutzungslimit erreicht.',
        it: 'Limite di utilizzo raggiunto.',
        pt: 'Limite de uso atingido.',
        nl: 'Gebruikslimiet bereikt.',
        pl: 'Osiągnięto limit użycia.',
        ja: '使用制限に達しました。',
        zh: '已达到使用限制。',
        ar: 'تم الوصول إلى حد الاستخدام.',
        hi: 'उपयोग सीमा पहुंच गई।',
        id: 'Batas penggunaan tercapai.',
        th: 'ถึงขีดจำกัดการใช้งานแล้ว',
        tr: 'Kullanım sınırına ulaşıldı.',
        vi: 'Đã đạt giới hạn sử dụng.'
      }
    }
  };

  // État global du widget
  let config = {};
  let conversationId = null;
  let messages = [];
  let isOpen = false;
  let isLoading = false;
  let hasShownWelcome = false;

  // Langues RTL (Right-to-Left)
  const RTL_LANGUAGES = ['ar', 'he', 'fa', 'ur'];

  /**
   * Initialisation du widget
   */
  function init(userConfig) {
    if (!userConfig || !userConfig.apiUrl || !userConfig.getToken) {
      console.error('InteliaWidget: apiUrl et getToken sont requis');
      return;
    }

    config = { ...DEFAULT_CONFIG, ...userConfig };
    conversationId = generateUUID();

    // Injecter les styles
    injectStyles();

    // Créer le DOM du widget
    createWidget();

    // Écouter les événements
    attachEventListeners();

    console.log('InteliaWidget initialisé', { conversationId });
  }

  /**
   * Générer UUID v4
   */
  function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  /**
   * Injecter les styles CSS
   */
  function injectStyles() {
    const style = document.createElement('style');
    style.id = 'intelia-widget-styles';
    style.textContent = `
      /* Container principal */
      #intelia-widget-container {
        position: fixed;
        ${config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
        bottom: 20px;
        z-index: 9999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
      }

      /* Bouton d'ouverture */
      #intelia-widget-button {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: white;
        color: white;
        border: none;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        transition: all 0.3s ease;
        overflow: hidden;
        padding: 8px;
      }

      #intelia-widget-button img {
        width: 100%;
        height: 100%;
        object-fit: contain;
      }

      #intelia-widget-button:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
      }

      #intelia-widget-button.open {
        transform: rotate(45deg);
      }

      /* Fenêtre de chat */
      #intelia-widget-chat {
        position: absolute;
        ${config.position.includes('right') ? 'right: 0;' : 'left: 0;'}
        bottom: 80px;
        width: 380px;
        max-width: calc(100vw - 40px);
        height: 600px;
        max-height: calc(100vh - 120px);
        background: white;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
        display: none;
        flex-direction: column;
        overflow: hidden;
        animation: slideUp 0.3s ease;
      }

      #intelia-widget-chat.open {
        display: flex;
      }

      @keyframes slideUp {
        from {
          opacity: 0;
          transform: translateY(20px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      /* Header */
      #intelia-widget-header {
        background: ${config.primaryColor};
        color: white;
        padding: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }

      #intelia-widget-header h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
      }

      #intelia-widget-close {
        background: none;
        border: none;
        color: white;
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        transition: background 0.2s;
      }

      #intelia-widget-close:hover {
        background: rgba(255, 255, 255, 0.2);
      }

      /* Messages */
      #intelia-widget-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: #f9fafb;
      }

      .intelia-message {
        max-width: 80%;
        padding: 10px 14px;
        border-radius: 12px;
        line-height: 1.4;
        font-size: 14px;
        word-wrap: break-word;
      }

      .intelia-message.user {
        align-self: flex-end;
        background: ${config.primaryColor};
        color: white;
        border-bottom-right-radius: 4px;
      }

      .intelia-message.assistant {
        align-self: flex-start;
        background: white;
        color: #1f2937;
        border: 1px solid #e5e7eb;
        border-bottom-left-radius: 4px;
      }

      .intelia-message.error {
        align-self: center;
        background: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecaca;
        font-size: 13px;
      }

      /* Typing indicator */
      .intelia-typing {
        align-self: flex-start;
        background: white;
        border: 1px solid #e5e7eb;
        padding: 10px 14px;
        border-radius: 12px;
        border-bottom-left-radius: 4px;
        display: flex;
        gap: 4px;
      }

      .intelia-typing span {
        width: 8px;
        height: 8px;
        background: #9ca3af;
        border-radius: 50%;
        animation: typing 1.4s infinite;
      }

      .intelia-typing span:nth-child(2) {
        animation-delay: 0.2s;
      }

      .intelia-typing span:nth-child(3) {
        animation-delay: 0.4s;
      }

      @keyframes typing {
        0%, 60%, 100% {
          transform: translateY(0);
          opacity: 0.5;
        }
        30% {
          transform: translateY(-10px);
          opacity: 1;
        }
      }

      /* Input */
      #intelia-widget-input-container {
        padding: 12px;
        border-top: 1px solid #e5e7eb;
        background: white;
        display: flex;
        gap: 8px;
      }

      #intelia-widget-input {
        flex: 1;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 14px;
        outline: none;
        resize: none;
        max-height: 120px;
        font-family: inherit;
      }

      #intelia-widget-input:focus {
        border-color: ${config.primaryColor};
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
      }

      #intelia-widget-send {
        background: ${config.primaryColor};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 16px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s;
        white-space: nowrap;
      }

      #intelia-widget-send:hover:not(:disabled) {
        opacity: 0.9;
        transform: translateY(-1px);
      }

      #intelia-widget-send:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      /* Scrollbar personnalisée */
      #intelia-widget-messages::-webkit-scrollbar {
        width: 6px;
      }

      #intelia-widget-messages::-webkit-scrollbar-track {
        background: transparent;
      }

      #intelia-widget-messages::-webkit-scrollbar-thumb {
        background: #d1d5db;
        border-radius: 3px;
      }

      #intelia-widget-messages::-webkit-scrollbar-thumb:hover {
        background: #9ca3af;
      }

      /* Mobile responsive */
      @media (max-width: 480px) {
        #intelia-widget-chat {
          width: calc(100vw - 40px);
          height: calc(100vh - 120px);
        }
      }

      /* RTL Support (Arabic, Hebrew, etc.) */
      ${RTL_LANGUAGES.includes(config.locale) ? `
        #intelia-widget-chat {
          direction: rtl;
        }

        #intelia-widget-messages {
          direction: rtl;
        }

        .intelia-message.user {
          align-self: flex-start;
          border-bottom-right-radius: 12px;
          border-bottom-left-radius: 4px;
        }

        .intelia-message.assistant {
          align-self: flex-end;
          border-bottom-left-radius: 12px;
          border-bottom-right-radius: 4px;
        }

        #intelia-widget-input-container {
          direction: rtl;
        }

        #intelia-widget-input {
          text-align: right;
        }
      ` : ''}
    `;
    document.head.appendChild(style);
  }

  /**
   * Créer le DOM du widget
   */
  function createWidget() {
    const container = document.createElement('div');
    container.id = 'intelia-widget-container';
    container.innerHTML = `
      <button id="intelia-widget-button" aria-label="${config.buttonLabel[config.locale]}">
        <img src="/api/static/images/logo.png" alt="Intelia" />
      </button>
      <div id="intelia-widget-chat">
        <div id="intelia-widget-header">
          <h3>Intelia Cognito</h3>
          <button id="intelia-widget-close" aria-label="Fermer">×</button>
        </div>
        <div id="intelia-widget-messages">
          <div class="intelia-message assistant">
            ${config.welcomeMessage[config.locale]}
          </div>
        </div>
        <div id="intelia-widget-input-container">
          <textarea
            id="intelia-widget-input"
            placeholder="${config.placeholder[config.locale]}"
            rows="1"
          ></textarea>
          <button id="intelia-widget-send">${config.sendButton[config.locale]}</button>
        </div>
      </div>
    `;
    document.body.appendChild(container);
  }

  /**
   * Attacher les event listeners
   */
  function attachEventListeners() {
    const button = document.getElementById('intelia-widget-button');
    const closeBtn = document.getElementById('intelia-widget-close');
    const sendBtn = document.getElementById('intelia-widget-send');
    const input = document.getElementById('intelia-widget-input');

    button.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', closeChat);
    sendBtn.addEventListener('click', sendMessage);

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-resize textarea
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = input.scrollHeight + 'px';
    });
  }

  /**
   * Toggle ouverture/fermeture du chat
   */
  function toggleChat() {
    isOpen = !isOpen;
    const button = document.getElementById('intelia-widget-button');
    const chat = document.getElementById('intelia-widget-chat');

    if (isOpen) {
      button.classList.add('open');
      chat.classList.add('open');

      // Afficher le message d'accueil la première fois
      if (!hasShownWelcome) {
        hasShownWelcome = true;
        const welcomeText = config.welcomeMessage[config.locale] || config.welcomeMessage['en'];
        addMessage('assistant', welcomeText);
      }

      document.getElementById('intelia-widget-input').focus();
    } else {
      button.classList.remove('open');
      chat.classList.remove('open');
    }
  }

  /**
   * Fermer le chat
   */
  function closeChat() {
    isOpen = false;
    document.getElementById('intelia-widget-button').classList.remove('open');
    document.getElementById('intelia-widget-chat').classList.remove('open');
  }

  /**
   * Envoyer un message
   */
  async function sendMessage() {
    const input = document.getElementById('intelia-widget-input');
    const message = input.value.trim();

    if (!message || isLoading) return;

    // Ajouter le message utilisateur
    addMessage('user', message);
    input.value = '';
    input.style.height = 'auto';

    // Afficher typing indicator
    showTypingIndicator();
    isLoading = true;
    updateSendButton();

    try {
      // Récupérer le token
      const token = await config.getToken();
      if (!token) {
        throw new Error('token_missing');
      }

      // Appeler l'API
      const response = await fetch(`${config.apiUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          user_id: config.userId,
          user_email: config.userEmail
        })
      });

      hideTypingIndicator();

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));

        if (response.status === 429) {
          throw new Error('quota_exceeded');
        } else if (response.status === 401) {
          throw new Error('auth_failed');
        } else {
          throw new Error('api_error');
        }
      }

      // Lire la réponse (streaming SSE)
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Ajouter au buffer
        buffer += decoder.decode(value, { stream: true });

        // Parser les lignes SSE
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Garder la dernière ligne incomplète dans le buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));

              // Extraire seulement le contenu des chunks
              if (data.type === 'chunk' && data.content) {
                assistantMessage += data.content;
                // Mettre à jour le message en temps réel
                updateLastAssistantMessage(assistantMessage);
              }
            } catch (e) {
              // Ignorer les erreurs de parsing JSON
              console.debug('Parse error:', e);
            }
          }
        }
      }

      // Message complet reçu
      if (assistantMessage) {
        messages.push({ role: 'assistant', content: assistantMessage });
      }

    } catch (error) {
      console.error('Widget error:', error);
      hideTypingIndicator();

      let errorMsg = config.errorMessages.network[config.locale];
      if (error.message === 'token_missing' || error.message === 'auth_failed') {
        errorMsg = config.errorMessages.token[config.locale];
      } else if (error.message === 'quota_exceeded') {
        errorMsg = config.errorMessages.quota[config.locale];
      }

      addMessage('error', errorMsg);
    } finally {
      isLoading = false;
      updateSendButton();
    }
  }

  /**
   * Ajouter un message au chat
   */
  function addMessage(role, content) {
    messages.push({ role, content });

    const messagesContainer = document.getElementById('intelia-widget-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `intelia-message ${role}`;
    messageDiv.textContent = content;
    messagesContainer.appendChild(messageDiv);

    // Scroll vers le bas
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  /**
   * Afficher typing indicator
   */
  function showTypingIndicator() {
    const messagesContainer = document.getElementById('intelia-widget-messages');
    const typing = document.createElement('div');
    typing.className = 'intelia-typing';
    typing.id = 'intelia-typing-indicator';
    typing.innerHTML = '<span></span><span></span><span></span>';
    messagesContainer.appendChild(typing);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  /**
   * Cacher typing indicator
   */
  function hideTypingIndicator() {
    const typing = document.getElementById('intelia-typing-indicator');
    if (typing) typing.remove();
  }

  /**
   * Mettre à jour le dernier message assistant (streaming)
   */
  function updateLastAssistantMessage(content) {
    const messagesContainer = document.getElementById('intelia-widget-messages');
    let lastMessage = messagesContainer.querySelector('.intelia-message.assistant:last-child');

    if (!lastMessage) {
      lastMessage = document.createElement('div');
      lastMessage.className = 'intelia-message assistant';
      messagesContainer.appendChild(lastMessage);
    }

    lastMessage.textContent = content;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  /**
   * Mettre à jour l'état du bouton d'envoi
   */
  function updateSendButton() {
    const sendBtn = document.getElementById('intelia-widget-send');
    sendBtn.disabled = isLoading;
    sendBtn.textContent = isLoading ? '...' : config.sendButton[config.locale];
  }

  // Exposer l'API publique
  window.InteliaWidget = {
    init,
    open: () => { if (!isOpen) toggleChat(); },
    close: closeChat,
    version: '1.0.0'
  };

})();
