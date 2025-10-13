// ==================== SYSTÈME DE TRADUCTION INTELIA EXPERT ====================

import { useState, useEffect, useRef } from "react";
import { getSupabaseClient } from "@/lib/supabase/singleton";
import {
  availableLanguages,
  DEFAULT_LANGUAGE,
  getLanguageByCode,
  isValidLanguageCode,
  detectBrowserLanguage,
} from "./config";

const supabase = getSupabaseClient();

// Types pour le système de traduction - VERSION ORGANISÉE PAR CATÉGORIES
export interface TranslationKeys {
  // ===========================================
  // PAGE TITLES & APP INFO
  // ===========================================
  "page.title": string;
  "app.description": string;

  // ===========================================
  // RESET PASSWORD - NOUVELLES CLÉS AJOUTÉES
  // ===========================================
  "resetPassword.title": string;
  "resetPassword.description": string;
  "resetPassword.newPassword": string;
  "resetPassword.confirmPassword": string;
  "resetPassword.updateButton": string;
  "resetPassword.updating": string;
  "resetPassword.backToLogin": string;
  "resetPassword.needHelp": string;
  "resetPassword.contactSupport": string;
  "resetPassword.validatingLink": string;
  "resetPassword.securityInfo": string;

  // Validation de mot de passe
  "resetPassword.validation.maxLength": string;
  "resetPassword.validation.letterRequired": string;
  "resetPassword.validation.tooCommon": string;
  "resetPassword.validation.tooRepetitive": string;
  "resetPassword.validation.avoidSequences": string;

  // Exigences mot de passe
  "resetPassword.requirements.hasLetter": string;
  "resetPassword.requirements.noRepetition": string;
  "resetPassword.requirements.reasonableLength": string;

  // Force du mot de passe
  "resetPassword.strength.weak": string;
  "resetPassword.strength.medium": string;
  "resetPassword.strength.good": string;
  "resetPassword.strength.excellent": string;
  "resetPassword.passwordStrength": string;
  "resetPassword.tips": string;

  // Conseils
  "resetPassword.tip.longerPassword": string;
  "resetPassword.tip.mixCase": string;
  "resetPassword.tip.specialChars": string;

  // Messages de succès
  "resetPassword.success.description": string;
  "resetPassword.success.goToSite": string;

  // Token invalide
  "resetPassword.invalidToken.title": string;
  "resetPassword.invalidToken.description": string;
  "resetPassword.invalidToken.requestNew": string;
  "resetPassword.invalidToken.backToSite": string;

  // Erreurs reset password
  "resetPassword.errors.tokenExpired": string;
  "resetPassword.errors.tooManyAttempts": string;
  "resetPassword.errors.connectionProblem": string;
  "resetPassword.errors.generic": string;

  // ===========================================
  // AUTHENTICATION & AUTH FLOWS - NOUVEAUX CHAMPS AJOUTÉS
  // ===========================================
  "auth.success": string;
  "auth.error": string;
  "auth.incomplete": string;
  "auth.connecting": string;
  "auth.login": string;
  "auth.forgotPassword": string;
  "auth.newToIntelia": string;
  "auth.createAccount": string;
  "auth.continueWith": string;
  "auth.noAccountYet": string;
  "auth.oauthError": string;

  // ===========================================
  // COMMON ELEMENTS
  // ===========================================
  "common.or": string;
  "common.optional": string;
  "common.appName": string;
  "common.notSpecified": string;
  "common.unexpectedError": string;
  "common.loading": string;
  "common.saving": string;
  "common.success": string;
  "common.error": string;
  "common.confirm": string;
  "common.delete": string;
  "common.edit": string;
  "common.view": string;
  "common.search": string;
  "common.filter": string;
  "common.clear": string;
  "common.reset": string;
  "common.apply": string;
  "common.update": string;

  // ===========================================
  // LOGIN FORM
  // ===========================================
  "login.email": string;
  "login.password": string;
  "login.rememberMe": string;
  "login.emailLabel": string;
  "login.passwordLabel": string;
  "login.emailPlaceholder": string;
  "login.passwordPlaceholder": string;

  // ===========================================
  // FORGOT PASSWORD
  // ===========================================
  "forgotPassword.title": string;
  "forgotPassword.description": string;
  "forgotPassword.emailLabel": string;
  "forgotPassword.emailPlaceholder": string;
  "forgotPassword.sendButton": string;
  "forgotPassword.sending": string;
  "forgotPassword.backToLogin": string;
  "forgotPassword.noAccount": string;
  "forgotPassword.supportProblem": string;
  "forgotPassword.contactSupport": string;
  "forgotPassword.securityInfo": string;
  "forgotPassword.securityInfo2": string;
  "forgotPassword.redirecting": string;
  "forgotPassword.enterEmail": string;
  "forgotPassword.invalidEmail": string;
  "forgotPassword.emailSent": string;
  "forgotPassword.checkInbox": string;
  "forgotPassword.emailNotFound": string;
  "forgotPassword.tooManyAttempts": string;
  "forgotPassword.connectionError": string;
  "forgotPassword.genericError": string;

  // ===========================================
  // EMAIL VERIFICATION
  // ===========================================
  "verification.title": string;
  "verification.subtitle": string;
  "verification.verifying": string;
  "verification.autoRedirect": string;
  "verification.loginNow": string;
  "verification.backToLogin": string;
  "verification.refreshPage": string;
  "verification.redirecting": string;
  "verification.loadingVerification": string;
  "verification.noEmail": string;
  "verification.retrySignup": string;
  "verification.supportQuestion": string;
  "verification.supportSubject": string;
  "verification.contactSupport": string;
  "verification.success.title": string;
  "verification.success.emailConfirmed": string;
  "verification.success.confirmed": string;
  "verification.success.canLogin": string;
  "verification.success.verified": string;
  "verification.error.title": string;
  "verification.error.possibleCauses": string;
  "verification.error.expired": string;
  "verification.error.alreadyUsed": string;
  "verification.error.invalid": string;
  "verification.error.retrySignup": string;
  "verification.error.invalidOrExpired": string;
  "verification.error.alreadyVerified": string;
  "verification.error.generic": string;
  "verification.error.network": string;
  "verification.pending.title": string;
  "verification.pending.emailSentTo": string;
  "verification.pending.emailSent": string;
  "verification.pending.checkEmail": string;
  "verification.pending.nextSteps": string;
  "verification.pending.step1": string;
  "verification.pending.step2": string;
  "verification.pending.step3": string;

  // ===========================================
  // INVITATION SYSTEM
  // ===========================================
  "invitation.validating": string;
  "invitation.processing": string;
  "invitation.completeProfile": string;
  "invitation.finalizingInvitation": string;
  "invitation.backendValidation": string;
  "invitation.waitMessage": string;
  "invitation.welcomeComplete": string;
  "invitation.validatedSuccess": string;
  "invitation.invitedBy": string;
  "invitation.personalMessage": string;
  "invitation.emailFromInvitation": string;
  "invitation.phoneAutoFill": string;
  "invitation.creatingAccount": string;
  "invitation.createAccount": string;
  "invitation.needHelp": string;
  "invitation.loadingInvitation": string;
  "invitation.status.tokenValidated": string;
  "invitation.status.tokenError": string;
  "invitation.status.accountCreated": string;
  "invitation.status.accountError": string;
  "invitation.status.processing": string;
  "invitation.redirecting.dashboard": string;
  "invitation.redirecting.login": string;
  "invitation.errors.missingToken": string;
  "invitation.errors.tokenValidation": string;
  "invitation.errors.noInvitation": string;
  "invitation.errors.processing": string;
  "invitation.errors.generic": string;
  "invitation.errors.missingAccessToken": string;
  "invitation.errors.profileCompletion": string;
  "invitation.errors.accountCompletion": string;
  "invitation.success.tokenValidated": string;
  "invitation.success.accountCreated": string;
  "invitation.success.welcome": string;

  // ===========================================
  // NAVIGATION
  // ===========================================
  "nav.history": string;
  "nav.newConversation": string;
  "nav.profile": string;
  "nav.language": string;
  "nav.subscription": string;
  "nav.contact": string;
  "nav.about": string;
  "nav.legal": string;
  "nav.logout": string;
  "nav.clearAll": string;
  "nav.inviteFriend": string;
  "nav.account": string;
  "nav.settings": string;
  "nav.statistics": string;
  "nav.conversationSidebar": string;
  "nav.closeSidebar": string;

  // ===========================================
  // CHAT INTERFACE - CLÉS AJOUTÉES/MODIFIÉES
  // ===========================================
  "chat.welcome": string;
  "chat.placeholder": string;
  "chat.helpfulResponse": string;
  "chat.notHelpfulResponse": string;
  "chat.voiceRecording": string;
  "chat.noConversations": string;
  "chat.loading": string;
  "chat.errorMessage": string;
  "chat.newConversation": string;
  "chat.disclaimer": string;
  "chat.send": string;
  "chat.askQuestion": string;
  "chat.clarificationPlaceholder": string;
  "chat.clarificationInstruction": string;
  "chat.clarificationMode": string;
  "chat.sending": string;
  "chat.noMessages": string;
  "chat.feedbackThanks": string;
  "chat.feedbackCommentPrefix": string; // NOUVELLE CLÉ
  "chat.scrollToBottom": string;
  "chat.startQuestion": string;
  "chat.redirectingLogin": string;
  "chat.sessionExpired": string;
  "chat.authInitError": string;
  "chat.recentLogout": string;
  "chat.logout": string;
  "chat.historyLoaded": string;
  "chat.historyLoadError": string;
  "chat.rejectionMessage": string;
  "chat.suggestedTopics": string;
  "chat.formatError": string;
  "chat.emptyContent": string;
  "chat.sendError": string;
  "chat.commentNotSent": string;
  "chat.feedbackSendError": string;
  "chat.feedbackGeneralError": string;
  "chat.redirectingInProgress": string;

  // ===========================================
  // CONVERSATION HISTORY - NOUVELLES CLÉS AJOUTÉES
  // ===========================================
  "history.confirmClearAll": string;
  "history.loadingConversations": string;
  "history.retrievingHistory": string;
  "history.noConversations": string;
  "history.startQuestion": string;
  "history.newConversation": string;
  "history.refresh": string;
  "history.messageCount": string;
  "history.deleteConversation": string;
  "history.clear": string;
  "history.delete": string;
  "history.export": string;
  "history.search": string;
  "history.filter": string;
  "history.noResults": string;
  "history.confirmClear": string;
  "history.toggleClicked": string;
  "history.userPresent": string;
  "history.loadingConversationsFor": string;
  "history.conversationsLoaded": string;
  "history.loadingError": string;
  "history.renderState": string;

  // Groupes de l'historique - NOUVELLES CLÉS
  "history.groups.today": string;
  "history.groups.yesterday": string;
  "history.groups.thisWeek": string;
  "history.groups.thisMonth": string;
  "history.groups.older": string;

  // ===========================================
  // USER PROFILE
  // ===========================================
  "profile.title": string;
  "profile.personalInfo": string;
  "profile.professionalInfo": string;
  "profile.contact": string;
  "profile.company": string;
  "profile.password": string;
  "profile.firstName": string;
  "profile.lastName": string;
  "profile.linkedinProfile": string;
  "profile.linkedinCorporate": string;
  "profile.email": string;
  "profile.phone": string;
  "profile.country": string;
  "profile.companyName": string;
  "profile.companyWebsite": string;
  "profile.companyLinkedin": string;
  "profile.currentPassword": string;
  "profile.newPassword": string;
  "profile.confirmPassword": string;
  "profile.passwordRequirements": string;
  "profile.passwordRequirements8": string;
  "profile.passwordRequirementsUpper": string;
  "profile.passwordRequirementsLower": string;
  "profile.passwordRequirementsNumber": string;
  "profile.passwordRequirementsSpecial": string;
  "profile.passwordErrors": string;
  "profile.passwordChanged": string;
  "profile.profileUpdated": string;
  "profile.optional": string;
  "profile.security": string;
  "profile.countryCode": string;
  "profile.areaCode": string;
  "profile.phoneNumber": string;
  "profile.jobTitle": string;

  // ===========================================
  // LANGUAGE SETTINGS
  // ===========================================
  "language.title": string;
  "language.description": string;
  "language.updating": string;
  "language.changeSuccess": string;
  "language.interfaceUpdated": string;
  "language.reloadForWidget": string;
  "language.reloadNow": string;
  "language.continueWithoutReload": string;
  "language.current": string;
  "language.debug.changing": string;
  "language.debug.interfaceUpdated": string;
  "language.debug.localStorageSaved": string;
  "language.debug.modalClosed": string;
  "language.debug.changeError": string;

  // ===========================================
  // SUBSCRIPTION & BILLING
  // ===========================================
  "subscription.title": string;
  "subscription.currentPlan": string;
  "subscription.modify": string;
  "subscription.payment": string;
  "subscription.update": string;
  "subscription.invoices": string;
  "subscription.cancellation": string;
  "subscription.cancel": string;
  "subscription.confirmCancel": string;
  "subscription.free": string;
  "subscription.premium.price": string;
  "subscription.featuresIncluded": string;

  // ===========================================
  // CONTACT & SUPPORT
  // ===========================================
  "contact.title": string;
  "contact.phone": string;
  "contact.phoneDescription": string;
  "contact.email": string;
  "contact.emailDescription": string;
  "contact.website": string;
  "contact.websiteDescription": string;
  "contact.subject": string;
  "contact.message": string;
  "contact.sendMessage": string;
  "contact.messageSent": string;
  "contact.supportEmail": string;

  // ===========================================
  // INVITATION MODAL & FRIEND INVITES
  // ===========================================
  "invite.title": string;
  "invite.subtitle": string;
  "invite.sendStatus": string;
  "invite.lastLogin": string;
  "invite.inviteOthers": string;
  "invite.emailAddresses": string;
  "invite.recipientCount": string;
  "invite.emailPlaceholder": string;
  "invite.emailHelp": string;
  "invite.personalMessage": string;
  "invite.messagePlaceholder": string;
  "invite.messageHelp": string;
  "invite.sending": string;
  "invite.send": string;
  "invite.footerInfo": string;
  "invite.authRetrievalError": string;
  "invite.loginRequired": string;
  "invite.loginRequiredTitle": string;
  "invite.emailRequired": string;
  "invite.invalidEmails": string;
  "invite.emailFormat": string;
  "invite.noValidEmails": string;
  "invite.maxLimit": string;
  "invite.sendError": string;
  "invite.authError": string;
  "invite.reconnectSuggestion": string;
  "invite.sessionExpired": string;
  "invite.sessionExpiredDetail": string;
  "invite.retryOrContact": string;
  "invite.validationError": string;
  "invite.invitationSent": string;
  "invite.userExists": string;
  "invite.userExistsWithDate": string;
  "invite.alreadyInvitedByYou": string;
  "invite.alreadyInvitedByOther": string;
  "invite.invalidEmail": string;
  "invite.rateLimit": string;
  "invite.sendFailed": string;
  "invite.namePlaceholder": string;
  "invite.sendButton": string;
  "invite.sentSuccess": string;
  "invite.error": string;
  "invite.optional": string;

  // ===========================================
  // FEEDBACK MODAL
  // ===========================================
  "feedback.sendError": string;
  "feedback.positiveTitle": string;
  "feedback.negativeTitle": string;
  "feedback.positivePlaceholder": string;
  "feedback.negativePlaceholder": string;
  "feedback.description": string;
  "feedback.characterCount": string;
  "feedback.limitWarning": string;
  "feedback.privacyNotice": string;
  "feedback.learnMore": string;
  "feedback.sending": string;
  "feedback.send": string;

  // ===========================================
  // COUNTRIES & REGIONS
  // ===========================================
  "countries.fallbackWarning": string;
  "countries.searchPlaceholder": string;
  "countries.listLabel": string;
  "countries.select": string;
  "countries.noResults": string;
  "countries.limitedList": string;
  "countries.loading": string;

  // ===========================================
  // PHONE INPUT & VALIDATION
  // ===========================================
  "phone.limitedList": string;
  "phone.countryCode": string;
  "phone.loading": string;
  "phone.select": string;
  "phone.countryCodeHelp": string;
  "phone.loadingCodes": string;
  "phone.areaCode": string;
  "phone.areaCodePlaceholder": string;
  "phone.areaCodeHelp": string;
  "phone.phoneNumber": string;
  "phone.phoneNumberPlaceholder": string;
  "phone.phoneNumberHelp": string;
  "phone.validation.countryRequired": string;
  "phone.validation.numberRequired": string;

  // ===========================================
  // USER MENU & INTERFACE CONTROLS
  // ===========================================
  "userMenu.openMenu": string;
  "userMenu.superAdmin": string;
  "userMenu.debug.unmounting": string;
  "userMenu.debug.changeDetected": string;
  "userMenu.debug.logoutViaService": string;
  "userMenu.debug.logoutServiceError": string;
  "userMenu.debug.toggleOpen": string;
  "userMenu.debug.currentIsOpen": string;

  // ===========================================
  // SUCCESS MESSAGES
  // ===========================================
  "success.authSynchronized": string;
  "success.profileUpdated": string;
  "success.passwordChanged": string;
  "success.languageUpdated": string;

  // ===========================================
  // ERROR MESSAGES
  // ===========================================
  "error.generic": string;
  "error.connection": string;
  "error.updateProfile": string;
  "error.changePassword": string;
  "error.firstNameRequired": string;
  "error.lastNameRequired": string;
  "error.emailRequired": string;
  "error.emailInvalid": string;
  "error.emailTooLong": string;
  "error.firstNameTooLong": string;
  "error.lastNameTooLong": string;
  "error.companyNameTooLong": string;
  "error.urlInvalid": string;
  "error.urlProtocol": string;
  "error.linkedinInvalid": string;
  "error.phonePrefix": string;
  "error.currentPasswordRequired": string;
  "error.newPasswordRequired": string;
  "error.confirmPasswordRequired": string;
  "error.currentPasswordIncorrect": string;
  "error.passwordServerError": string;
  "error.userNotConnected": string;
  "error.validationErrors": string;
  "error.serverError": string;
  "error.unexpectedResponse": string;
  "error.checkConnection": string;
  "error.serviceUnavailable": string;

  // ===========================================
  // AUTH ERROR MESSAGES - NOUVELLES CLÉS
  // ===========================================
  "auth.emailAlreadyExists": string;
  "auth.invalidCredentials": string;
  "auth.emailNotConfirmed": string;
  "auth.passwordRequirementsNotMet": string;

  // ===========================================
  // VALIDATION RULES & MESSAGES
  // ===========================================
  "validation.required.firstName": string;
  "validation.required.lastName": string;
  "validation.required.fullName": string;
  "validation.required.email": string;
  "validation.required.country": string;
  "validation.required.password": string;
  "validation.required.confirmPassword": string;
  "validation.required.accessToken": string;
  "validation.correctErrors": string;
  "validation.invalidData": string;
  "validation.password.requirements": string;
  "validation.password.minLength": string;
  "validation.password.uppercase": string;
  "validation.password.lowercase": string;
  "validation.password.number": string;
  "validation.password.special": string;
  "validation.password.match": string;
  "validation.password.mismatch": string;
  "validation.phone.incomplete": string;
  "validation.phone.invalid": string;

  // ===========================================
  // FORM ELEMENTS
  // ===========================================
  "form.required": string;
  "form.phoneFormat": string;
  "form.passwordMinLength": string;
  "form.passwordUppercase": string;
  "form.passwordLowercase": string;
  "form.passwordNumber": string;
  "form.passwordSpecial": string;
  "form.passwordMismatch": string;

  // ===========================================
  // MODAL DIALOGS
  // ===========================================
  "modal.close": string;
  "modal.cancel": string;
  "modal.save": string;
  "modal.back": string;
  "modal.loading": string;
  "modal.updating": string;

  // ===========================================
  // USER INTERFACE CONTROLS
  // ===========================================
  "ui.menu": string;
  "ui.close": string;
  "ui.open": string;
  "ui.expand": string;
  "ui.collapse": string;
  "ui.previous": string;
  "ui.next": string;

  // ===========================================
  // DIALOG BUTTONS
  // ===========================================
  "dialog.confirm": string;
  "dialog.cancel": string;
  "dialog.ok": string;
  "dialog.yes": string;
  "dialog.no": string;

  // ===========================================
  // SYSTEM STATUS
  // ===========================================
  "status.online": string;
  "status.offline": string;
  "status.connecting": string;
  "status.connected": string;
  "status.disconnected": string;

  // ===========================================
  // USER ACCOUNT SETTINGS
  // ===========================================
  "account.settings": string;
  "account.preferences": string;
  "account.security": string;
  "account.privacy": string;
  "account.notifications": string;

  // ===========================================
  // USER MENU ITEMS
  // ===========================================
  "user.menu": string;
  "user.profile": string;
  "user.settings": string;
  "user.logout": string;
  "user.account": string;

  // ===========================================
  // FORM PLACEHOLDERS - NOUVELLES CLÉS AJOUTÉES
  // ===========================================
  "placeholder.firstName": string;
  "placeholder.lastName": string;
  "placeholder.jobTitle": string;
  "placeholder.linkedinPersonal": string;
  "placeholder.companyName": string;
  "placeholder.companyWebsite": string;
  "placeholder.linkedinCorporate": string;
  "placeholder.countrySelect": string;
  "placeholder.currentPassword": string;
  "placeholder.newPassword": string;
  "placeholder.confirmPassword": string;
  "placeholder.email": string;
  "placeholder.createSecurePassword": string;
  "placeholder.confirmNewPassword": string;

  // ===========================================
  // DATE & TIME FORMATTING
  // ===========================================
  "date.today": string;
  "date.format": string;

  // ===========================================
  // SUBSCRIPTION PLANS
  // ===========================================
  "plan.essential": string;
  "plan.pro": string;
  "plan.max": string;

  // ===========================================
  // GDPR & LEGAL - NOUVELLES CLÉS AJOUTÉES
  // ===========================================
  "gdpr.notice": string;
  "gdpr.deleteAccount": string;
  "gdpr.exportData": string;
  "gdpr.confirmDelete": string;
  "gdpr.contactSupport": string;
  "legal.terms": string;
  "legal.privacy": string;

  // ===========================================
  // COUNTRIES LIST - NOUVELLES CLÉS AJOUTÉES
  // ===========================================
  "country.canada": string;
  "country.usa": string;
  "country.france": string;
  "country.belgium": string;
  "country.switzerland": string;
  "country.mexico": string;
  "country.brazil": string;

  // ===========================================
  // SHARE CONVERSATION
  // ===========================================
  "share.button": string;
  "share.modalTitle": string;
  "share.anonymize": string;
  "share.anonymizeHelp": string;
  "share.expiration": string;
  "share.expirationHelp": string;
  "share.expiration.7days": string;
  "share.expiration.30days": string;
  "share.expiration.90days": string;
  "share.expiration.never": string;
  "share.generating": string;
  "share.generate": string;
  "share.successTitle": string;
  "share.successMessage": string;
  "share.copy": string;
  "share.copied": string;
  "share.error": string;

  // ===========================================
  // ABOUT PAGE
  // ===========================================
  "about.pageTitle": string;
  "about.introduction": string;
  "about.companyInformation": string;
  "about.companyName": string;
  "about.location": string;
  "about.email": string;
  "about.website": string;
  "about.thirdPartyNotices": string;
  "about.thirdPartyIntro": string;
  "about.openSourceLicenses": string;
  "about.licensesUsed": string;
  "about.downloadFull": string;
  "about.downloadDescription": string;
  "about.versionInfo": string;
  "about.version": string;
  "about.lastUpdated": string;
  "about.license": string;
  "about.backToHome": string;
}

// SYSTÈME DE NOTIFICATION POUR FORCER LES RE-RENDERS
class I18nNotificationManager {
  private static instance: I18nNotificationManager;
  private subscribers: Array<() => void> = [];

  static getInstance(): I18nNotificationManager {
    if (!I18nNotificationManager.instance) {
      I18nNotificationManager.instance = new I18nNotificationManager();
    }
    return I18nNotificationManager.instance;
  }

  subscribe(callback: () => void): () => void {
    this.subscribers.push(callback);
    return () => {
      this.subscribers = this.subscribers.filter((cb) => cb !== callback);
    };
  }

  notify(): void {
    this.subscribers.forEach((callback) => {
      try {
        callback();
      } catch (error) {
        secureLog.error("Erreur notification i18n:", error);
      }
    });
  }
}

const notificationManager = I18nNotificationManager.getInstance();

// Cache pour les traductions chargées
const translationsCache: Record<string, TranslationKeys> = {};

// Cache des erreurs pour éviter les boucles infinies
const errorCache = new Set<string>();

// Variables globales pour la synchronisation - MODIFIÉ POUR UTILISER LE NAVIGATEUR
let globalTranslations: TranslationKeys = {} as TranslationKeys;
let globalLoading = true;
// CHANGEMENT CRITIQUE : utiliser detectBrowserLanguage() au lieu de DEFAULT_LANGUAGE
let globalLanguage =
  typeof window !== "undefined" ? detectBrowserLanguage() : DEFAULT_LANGUAGE;

// EXPOSER LES VARIABLES POUR LE DEBUG (seulement en développement)
if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
  (window as any).i18nDebug = {
    getGlobalTranslations: () => globalTranslations,
    getGlobalLoading: () => globalLoading,
    getGlobalLanguage: () => globalLanguage,
    getTranslationsCache: () => translationsCache,
    getErrorCache: () => errorCache,
    clearErrorCache: () => errorCache.clear(),
    notificationManager,
  };
}

// Fonction pour récupérer la langue depuis le localStorage
const getStoredLanguage = (): string => {
  try {
    const storedLang = localStorage.getItem("intelia-language");
    if (storedLang) {
      const parsed = JSON.parse(storedLang);
      return parsed?.state?.currentLanguage || detectBrowserLanguage();
    }
  } catch (error) {
    secureLog.warn("Erreur lecture langue stockée:", error);
  }
  return detectBrowserLanguage();
};

// Fonction pour charger les traductions depuis les fichiers JSON - AVEC PROTECTION ANTI-BOUCLE
async function loadTranslations(language: string): Promise<TranslationKeys> {
  // Vérifier le cache des erreurs
  if (errorCache.has(language)) {
    secureLog.warn(
      `[i18n] Langue ${language} en cache d'erreur, utilisation de ${DEFAULT_LANGUAGE}`,
    );
    if (language === DEFAULT_LANGUAGE) {
      return {} as TranslationKeys;
    }
    return loadTranslations(DEFAULT_LANGUAGE);
  }

  if (translationsCache[language]) {
    globalTranslations = translationsCache[language];
    globalLoading = false;
    globalLanguage = language;

    // NOTIFIER TOUS LES COMPOSANTS
    notificationManager.notify();

    return translationsCache[language];
  }

  try {
    const response = await fetch(`/locales/${language}.json`);
    if (!response.ok) {
      throw new Error(
        `HTTP ${response.status}: Failed to load translations for ${language}`,
      );
    }

    const translations = await response.json();

    // Vérifier que les traductions ne sont pas vides ou corrompues
    if (
      !translations ||
      typeof translations !== "object" ||
      Object.keys(translations).length === 0
    ) {
      throw new Error(`Empty or invalid translations for ${language}`);
    }

    translationsCache[language] = translations;
    globalTranslations = translations;
    globalLoading = false;
    globalLanguage = language;

    // NOTIFIER TOUS LES COMPOSANTS
    notificationManager.notify();

    secureLog.log(
      `[i18n] Traductions chargées pour ${language}: ${Object.keys(translations).length} clés`,
    );
    return translations;
  } catch (error) {
    secureLog.error(`[i18n] Could not load translations for ${language}:`, error);

    // Ajouter à la cache des erreurs pour éviter les boucles
    errorCache.add(language);

    // Fallback vers la langue par défaut
    if (language !== DEFAULT_LANGUAGE) {
      secureLog.warn(`[i18n] Falling back to ${DEFAULT_LANGUAGE}`);
      return loadTranslations(DEFAULT_LANGUAGE);
    }

    // Si même la langue par défaut échoue, retourner des clés vides
    secureLog.error(
      `[i18n] Even ${DEFAULT_LANGUAGE} failed to load, returning empty translations`,
    );
    return {} as TranslationKeys;
  }
}

// Hook de traduction - VERSION CORRIGÉE POUR DÉTECTER LA LANGUE DU NAVIGATEUR
export const useTranslation = () => {
  // AJOUT: Refs pour cleanup
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  // Initialiser avec DEFAULT_LANGUAGE comme valeur statique
  const [currentLanguage, setCurrentLanguage] =
    useState<string>(DEFAULT_LANGUAGE);
  const [translations, setTranslations] = useState<TranslationKeys>(
    {} as TranslationKeys,
  );
  const [loading, setLoading] = useState(true);
  const [, forceRender] = useState({}); // Pour forcer les re-renders

  // S'ABONNER AUX NOTIFICATIONS
  useEffect(() => {
    const unsubscribe = notificationManager.subscribe(() => {
      if (isMountedRef.current) {
        // AJOUT: protection démontage
        forceRender({});
      }
    });

    return unsubscribe;
  }, []);

  // LOGIQUE MODIFIÉE : PRIORITÉ 1 = localStorage, PRIORITÉ 2 = Navigateur
  useEffect(() => {
    const getUserLanguage = async () => {
      try {
        // PRIORITÉ 1: localStorage (choix explicite de l'utilisateur)
        const storedLang = getStoredLanguage();
        if (storedLang && isValidLanguageCode(storedLang)) {
          // Vérifier si ce n'est PAS la détection automatique du navigateur
          const browserLang = detectBrowserLanguage();
          if (storedLang !== browserLang) {
            // L'utilisateur a fait un choix explicite différent du navigateur
            secureLog.log(
              `[i18n] Choix utilisateur (localStorage): ${storedLang}`,
            );
            setCurrentLanguage(storedLang);
            return;
          }
        }

        // PRIORITÉ 2: Navigateur (nouveau défaut)
        const browserLang = detectBrowserLanguage();
        secureLog.log(`[i18n] Langue du navigateur détectée: ${browserLang}`);
        setCurrentLanguage(browserLang);

        // PRIORITÉ 3: Supabase (optionnel)
        try {
          const {
            data: { session },
          } = await supabase.auth.getSession();
          const userLang = session?.user?.user_metadata?.language;

          if (userLang && isValidLanguageCode(userLang) && !storedLang) {
            secureLog.log(`[i18n] Langue Supabase utilisée: ${userLang}`);
            setCurrentLanguage(userLang);
            return;
          }
        } catch (error) {
          // Ignorer les erreurs Supabase, continuer avec le navigateur
          secureLog.log("Pas de session Supabase, utilisation langue navigateur");
        }
      } catch (error) {
        secureLog.log(
          "Erreur initialisation langue, utilisation navigateur par défaut",
        );
        const browserLang = detectBrowserLanguage();
        setCurrentLanguage(browserLang);
      }
    };
    getUserLanguage();
  }, []);

  // Vérification continue de localStorage pour éviter le cache corrompu
  useEffect(() => {
    // Intervalle pour vérifier périodiquement les changements du localStorage
    const checkLocalStorageInterval = setInterval(() => {
      if (!isMountedRef.current) return; // AJOUT: protection démontage

      const storedLang = getStoredLanguage();
      if (
        storedLang &&
        storedLang !== currentLanguage &&
        isValidLanguageCode(storedLang)
      ) {
        secureLog.log(
          `[i18n] Resynchronisation détectée: ${currentLanguage} → ${storedLang}`,
        );
        setCurrentLanguage(storedLang);
      }
    }, 1000); // Vérifier toutes les secondes

    intervalRef.current = checkLocalStorageInterval; // AJOUT

    // AJOUT: Nettoyer l'intervalle au démontage
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [currentLanguage]);

  // Écouter les événements de localStorage pour une réactivité immédiate
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (!isMountedRef.current) return; // AJOUT: protection démontage

      if (e.key === "intelia-language" && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue);
          const newLang = parsed?.state?.currentLanguage;

          if (
            newLang &&
            newLang !== currentLanguage &&
            isValidLanguageCode(newLang)
          ) {
            secureLog.log(
              `[i18n] Changement localStorage détecté: ${currentLanguage} → ${newLang}`,
            );
            setCurrentLanguage(newLang);
          }
        } catch (error) {
          secureLog.warn("Erreur parsing localStorage change:", error);
        }
      }
    };

    // Écouter les changements de localStorage depuis d'autres onglets/composants
    window.addEventListener("storage", handleStorageChange);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
    };
  }, [currentLanguage]);

  // Charger les traductions quand la langue change
  useEffect(() => {
    const loadLanguage = async () => {
      setLoading(true);
      try {
        const loadedTranslations = await loadTranslations(currentLanguage);

        // IMPORTANT: Mettre à jour les translations AVANT de mettre loading à false
        setTranslations(loadedTranslations);
        setLoading(false);
      } catch (error) {
        secureLog.error("Erreur chargement traductions:", error);
        setLoading(false);
      }
    };

    loadLanguage();
  }, [currentLanguage]);

  // Écouter les changements de langue
  useEffect(() => {
    const handleLanguageChange = (event: CustomEvent) => {
      if (!isMountedRef.current) return; // AJOUT: protection démontage
      setCurrentLanguage(event.detail.language);
    };

    window.addEventListener(
      "languageChanged",
      handleLanguageChange as EventListener,
    );

    return () => {
      window.removeEventListener(
        "languageChanged",
        handleLanguageChange as EventListener,
      );
    };
  }, []);

  // AJOUT: Effect de démontage pour nettoyer les refs
  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;

      // Cleanup final de l'interval si nécessaire
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  const t = (key: keyof TranslationKeys): string => {
    // LOGIQUE SIMPLIFIÉE : priorité aux translations locales, puis globales
    const finalTranslations =
      Object.keys(translations).length > 0 ? translations : globalTranslations;
    const isStillLoading = loading && globalLoading;

    if (isStillLoading || !finalTranslations[key]) {
      return key;
    }

    return finalTranslations[key];
  };

  const changeLanguage = async (newLanguage: string) => {
    // NETTOYER COMPLÈTEMENT le cache avant changement pour éviter contamination
    Object.keys(translationsCache).forEach((lang) => {
      delete translationsCache[lang];
    });

    // Réinitialiser les variables globales
    globalTranslations = {} as TranslationKeys;
    globalLoading = true;

    // Nettoyer le cache d'erreur si on retente une langue
    errorCache.delete(newLanguage);

    setCurrentLanguage(newLanguage);

    // Sauvegarder dans localStorage avec la structure attendue
    try {
      const langData = {
        state: {
          currentLanguage: newLanguage,
        },
      };
      localStorage.setItem("intelia-language", JSON.stringify(langData));
      secureLog.log("[i18n] Langue sauvegardée:", newLanguage);
    } catch (error) {
      secureLog.warn("[i18n] Erreur sauvegarde langue:", error);
    }

    // Forcer le rechargement complet des traductions
    await loadTranslations(newLanguage);

    // Émettre l'événement pour mettre à jour d'autres composants
    window.dispatchEvent(
      new CustomEvent("languageChanged", {
        detail: { language: newLanguage },
      }),
    );
  };

  const getCurrentLanguage = () => currentLanguage;

  const formatDate = (date: Date) => {
    const langConfig = getLanguageByCode(currentLanguage);
    const locale = langConfig?.dateFormat || "en-US";
    return date.toLocaleDateString(locale, {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  };

  return {
    t,
    changeLanguage,
    getCurrentLanguage,
    formatDate,
    currentLanguage,
    loading,
  };
};

// Fonction utilitaire pour obtenir les langues disponibles (compatibilité)
export const getAvailableLanguages = () =>
  availableLanguages.map((lang) => ({
    code: lang.code,
    name: lang.nativeName,
    region: lang.region,
  }));

// Export de la configuration complète pour les composants
export {
  availableLanguages,
  DEFAULT_LANGUAGE,
  getLanguageByCode,
} from "./config";
import { secureLog } from "@/lib/utils/secureLogger";
