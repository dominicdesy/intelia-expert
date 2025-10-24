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
  "login.showPassword": string;
  "login.hidePassword": string;

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
  "forgotPassword.otpEmailHint": string;

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
  "invitation.pleaseLogin": string;
  "invitation.accountCreatedPleaseLogin": string;

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
  "chat.voiceNoSpeech": string;
  "chat.voicePermissionDenied": string;
  "chat.voiceError": string;
  "chat.voiceNotSupported": string;
  "chat.voiceStop": string;
  "chat.voiceStart": string;
  "chat.voiceListening": string;
  "chat.voiceRealtimeIdle": string;
  "chat.voiceRealtimeConnecting": string;
  "chat.voiceRealtimeListening": string;
  "chat.voiceRealtimeSpeaking": string;
  "chat.voiceRealtimeError": string;
  "chat.voiceRealtimeBetaTitle": string;
  "chat.voiceRealtimeClickStart": string;
  "chat.voiceRealtimeDoubleClick": string;
  "chat.voiceRealtimeAdminOnly": string;
  "chat.satisfactionQuestion": string;
  "chat.satisfactionSatisfied": string;
  "chat.satisfactionNeutral": string;
  "chat.satisfactionUnsatisfied": string;
  "chat.satisfactionHelpful": string;
  "chat.satisfactionOkay": string;
  "chat.satisfactionPoor": string;
  "chat.satisfactionCommentPrompt": string;
  "chat.satisfactionCommentPlaceholder": string;
  "chat.satisfactionSkip": string;
  "chat.satisfactionThanks": string;
  "chat.submit": string;
  "chat.noConversations": string;
  "chat.loading": string;
  "chat.errorMessage": string;
  "chat.planName": string;
  "chat.questionsUsed": string;
  "chat.quotaExceeded": string;
  "chat.upgradePrompt": string;
  "chat.newConversation": string;
  "chat.disclaimer": string;
  "chat.cot.showReasoning": string;
  "chat.cot.hideReasoning": string;
  "chat.cot.thinking": string;
  "chat.cot.analysis": string;
  "chat.cot.answer": string;
  "chat.send": string;
  "chat.askQuestion": string;
  "chat.analyzeImageDefault": string;
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
  "chat.uploadImages": string;

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
  "profile.description": string;
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
  "profile.whatsappNumber": string;
  "profile.whatsappDescription": string;
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

  // User Profiling - Production Type & Category
  "profile.productionType.label": string;
  "profile.productionType.description": string;
  "profile.productionType.broiler": string;
  "profile.productionType.layer": string;
  "profile.productionType.both": string;
  "profile.productionType.why": string;
  "profile.category.label": string;
  "profile.category.description": string;
  "profile.category.why": string;
  "profile.category.breedingHatchery": string;
  "profile.category.feedNutrition": string;
  "profile.category.farmOperations": string;
  "profile.category.healthVeterinary": string;
  "profile.category.processing": string;
  "profile.category.managementOversight": string;
  "profile.category.equipmentTechnology": string;
  "profile.category.other": string;
  "profile.category.otherPlaceholder": string;

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
  "subscription.description": string;
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
  "subscription.comparison.title": string;
  "subscription.comparison.feature": string;
  "subscription.comparison.essential": string;
  "subscription.comparison.pro": string;
  "subscription.comparison.elite": string;
  "subscription.comparison.category.base": string;
  "subscription.comparison.category.capacity": string;
  "subscription.comparison.category.ai": string;
  "subscription.comparison.category.experience": string;
  "subscription.comparison.feature.languages": string;
  "subscription.comparison.feature.roleAdaptation": string;
  "subscription.comparison.feature.queries": string;
  "subscription.comparison.feature.history": string;
  "subscription.comparison.feature.pdfExport": string;
  "subscription.comparison.feature.imageAnalysis": string;
  "subscription.comparison.feature.voiceInput": string;
  "subscription.comparison.feature.voiceAssistant": string;
  "subscription.comparison.feature.adFree": string;
  "subscription.comparison.value.100": string;
  "subscription.comparison.value.unlimited": string;
  "subscription.comparison.value.unlimitedStar": string;
  "subscription.comparison.value.30days": string;
  "subscription.comparison.value.25perMonth": string;

  // ===========================================
  // BILLING & CURRENCY
  // ===========================================
  "billing.billingCurrency": string;
  "billing.current": string;
  "billing.suggested": string;
  "billing.notSetYet": string;
  "billing.currencyRequiredForUpgrade": string;
  "billing.changeCurrency": string;
  "billing.selectCurrency": string;
  "billing.loadingCurrency": string;
  "billing.currencyUpdated": string;
  "billing.currencyUpdateFailed": string;
  "billing.monthly": string;
  "billing.yearly": string;
  "billing.discount15": string;
  "billing.free": string;
  "billing.currentPlan": string;
  "billing.freePlan": string;
  "billing.popular": string;
  "billing.recommended": string;
  "billing.trial14days": string;
  "billing.startFreeTrial": string;
  "billing.manageSubscription": string;
  "billing.loading": string;
  "billing.redirecting": string;
  "billing.notes.trial": string;
  "billing.notes.trialDesc": string;
  "billing.notes.secure": string;
  "billing.notes.secureDesc": string;
  "billing.notes.unlimited": string;

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
  "contact.corporatePlanSubject": string;

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
  "error.invalidShareToken": string;
  "error.noTokenReceived": string;

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
  "plan.elite": string;
  "plan.corporate": string;

  // Plan descriptions
  "plan.essential.description": string;
  "plan.pro.description": string;
  "plan.elite.description": string;
  "plan.corporate.description": string;

  // Essential features
  "plan.essential.feature1": string; // 50 questions par mois
  "plan.essential.feature2": string; // Accès aux documents publics
  "plan.essential.feature3": string; // Support par email
  "plan.essential.feature4": string; // Interface web

  // Pro features
  "plan.pro.feature1": string; // Questions illimitées
  "plan.pro.feature2": string; // Accès documents confidentiels
  "plan.pro.feature3": string; // Support prioritaire
  "plan.pro.feature4": string; // Interface web + mobile
  "plan.pro.feature5": string; // Analytics avancées

  // Elite features
  "plan.elite.feature1": string; // Tout du plan Pro
  "plan.elite.feature2": string; // Questions illimitées prioritaires
  "plan.elite.feature3": string; // Analyse de photos
  "plan.elite.feature4": string; // Support dédié 24/7
  "plan.elite.feature5": string; // Intégrations personnalisées

  // Corporate features
  "plan.corporate.feature1": string; // Tout du plan Elite
  "plan.corporate.feature2": string; // Knowledge base personnalisée
  "plan.corporate.feature3": string; // Intégration documents privés
  "plan.corporate.feature4": string; // Formation équipe dédiée
  "plan.corporate.feature5": string; // SLA garanti
  "plan.corporate.feature6": string; // Support dédié 24/7

  // Pricing labels
  "plan.popular": string;
  "plan.currentPlan": string;
  "plan.contactUs": string;
  "plan.perMonth": string;
  "plan.free": string;

  // ===========================================
  // GDPR & LEGAL - NOUVELLES CLÉS AJOUTÉES
  // ===========================================
  "gdpr.notice": string;
  "gdpr.signupNotice": string;
  "gdpr.deleteAccount": string;
  "gdpr.exportData": string;
  "gdpr.confirmDelete": string;
  "gdpr.contactSupport": string;
  "gdpr.dpoTitle": string;
  "gdpr.dpoContactTitle": string;
  "gdpr.dpoDescription": string;
  "gdpr.dpoResponseTime": string;
  "legal.terms": string;
  "legal.privacy": string;
  "legal.and": string;

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
  // EXPORT PDF
  // ===========================================
  "export.button": string;
  "export.tooltip": string;
  "export.exporting": string;
  "export.error": string;
  "export.planRestriction": string;
  "export.notAuthenticated": string;
  "export.serverError": string;

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
  "about.versionDate": string;
  "about.lastUpdated": string;
  "about.license": string;
  "about.backToHome": string;

  // ===========================================
  // HELP TOUR
  // ===========================================
  "help.buttonTitle": string;
  "help.close": string;
  "help.previous": string;
  "help.next": string;
  "help.finish": string;
  "help.inputTitle": string;
  "help.inputDesc": string;
  "help.sendTitle": string;
  "help.sendDesc": string;
  "help.newChatTitle": string;
  "help.newChatDesc": string;
  "help.historyTitle": string;
  "help.historyDesc": string;
  "help.profileTitle": string;
  "help.profileDesc": string;
  "help.cameraTitle": string;
  "help.cameraDesc": string;
  "help.voiceTitle": string;
  "help.voiceDesc": string;

  // ===========================================
  // STRIPE PAYMENTS & BILLING
  // ===========================================
  // Upgrade Modal
  "stripe.upgrade.title": string;
  "stripe.upgrade.choosePlan": string;
  "stripe.upgrade.currentPlanBadge": string;
  "stripe.upgrade.perMonth": string;
  "stripe.upgrade.selectPlan": string;
  "stripe.upgrade.redirecting": string;
  "stripe.upgrade.paymentSecure": string;
  "stripe.upgrade.stripeLink": string;
  "stripe.upgrade.cancelAnytime": string;
  "stripe.upgrade.monthlyBilling": string;
  "stripe.upgrade.noCommitment": string;
  "stripe.upgrade.error": string;

  // Account Modal
  "stripe.account.title": string;
  "stripe.account.currentPlan": string;
  "stripe.account.badge": string;
  "stripe.account.free": string;
  "stripe.account.upgradeButton": string;
  "stripe.account.upgradePlan": string;
  "stripe.account.manageSubscription": string;
  "stripe.account.managingSubscription": string;

  // Customer Portal
  "stripe.portal.error": string;

  // Success Page
  "stripe.success.title": string;
  "stripe.success.message": string;
  "stripe.success.redirecting": string;
  "stripe.success.activated": string;
  "stripe.success.immediateAccess": string;
  "stripe.success.monthlyBilling": string;
  "stripe.success.confirmationEmail": string;
  "stripe.success.startNow": string;
  "stripe.success.viewProfile": string;
  "stripe.success.enjoy": string;
  "stripe.success.thanksForTrust": string;
  "stripe.success.backToChat": string;
  "stripe.success.needHelp": string;
  "stripe.success.contactSupport": string;

  // Cancel Page
  "stripe.cancel.title": string;
  "stripe.cancel.message": string;
  "stripe.cancel.youCanStill": string;
  "stripe.cancel.continueEssential": string;
  "stripe.cancel.retryLater": string;
  "stripe.cancel.contactUs": string;
  "stripe.cancel.backToHome": string;
  "stripe.cancel.retry": string;
  "stripe.cancel.needHelp": string;
  "stripe.cancel.contactSupport": string;

  // ===========================================
  // PASSKEY / WEBAUTHN - BIOMETRIC AUTHENTICATION
  // ===========================================
  "passkey.title": string;
  "passkey.description": string;
  "passkey.setupButton": string;
  "passkey.registered": string;
  "passkey.noPasskeys": string;

  // Login
  "passkey.login.title": string;
  "passkey.login.button": string;
  "passkey.login.description": string;
  "passkey.login.inProgress": string;
  "passkey.login.success": string;
  "passkey.login.error": string;
  "passkey.login.canceled": string;

  // Setup
  "passkey.setupTitle": string;
  "passkey.setup.title": string;
  "passkey.setup.description": string;
  "passkey.setup.button": string;
  "passkey.setup.deviceName": string;
  "passkey.setup.devicePlaceholder": string;
  "passkey.setup.inProgress": string;
  "passkey.setup.success": string;
  "passkey.setup.error": string;
  "passkey.setup.notSupported": string;
  "passkey.setup.alreadySetup": string;

  // Manage
  "passkey.manage.title": string;
  "passkey.manage.description": string;
  "passkey.manage.deviceName": string;
  "passkey.manage.addedOn": string;
  "passkey.manage.lastUsed": string;
  "passkey.manage.never": string;
  "passkey.manage.delete": string;
  "passkey.manage.confirmDelete": string;
  "passkey.manage.deleteSuccess": string;
  "passkey.manage.deleteError": string;
  "passkey.manage.noDevices": string;
  "passkey.manage.synced": string;
  "passkey.manage.local": string;

  // Info
  "passkey.info.whatIs": string;
  "passkey.info.description": string;
  "passkey.info.benefits": string;
  "passkey.info.devices": string;

  // Benefits
  "passkey.benefits.faster": string;
  "passkey.benefits.secure": string;
  "passkey.benefits.noPassword": string;

  // Devices
  "passkey.devices.supported": string;
}

// ✅ SOLUTION D: NotificationManager supprimé - Système redondant avec useState/useEffect

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
  };
}

// Fonction pour récupérer la langue depuis le localStorage
const getStoredLanguage = (): string | null => {
  try {
    const storedLang = localStorage.getItem("intelia-language");
    if (storedLang) {
      const parsed = JSON.parse(storedLang);
      return parsed?.state?.currentLanguage || null;
    }
  } catch (error) {
    secureLog.warn("Erreur lecture langue stockée:", error);
  }
  return null;
};

// ✅ SOLUTION B: Détection synchrone de la langue pour éviter le flash initial
const getInitialLanguageSync = (): string => {
  if (typeof window === 'undefined') return DEFAULT_LANGUAGE;

  try {
    // Vérifier localStorage en premier (le plus rapide)
    const stored = localStorage.getItem('intelia-language');
    if (stored) {
      const parsed = JSON.parse(stored);
      const lang = parsed?.state?.currentLanguage;
      if (lang && isValidLanguageCode(lang)) {
        secureLog.log(`[i18n] Init synchrone: langue depuis localStorage = ${lang}`);
        return lang;
      }
    }
  } catch (error) {
    secureLog.warn("[i18n] Erreur lecture synchrone localStorage:", error);
  }

  // Fallback : détection du navigateur
  const browserLang = detectBrowserLanguage();
  secureLog.log(`[i18n] Init synchrone: langue navigateur = ${browserLang}`);
  return browserLang;
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
  // AJOUT: Ref pour cleanup
  const isMountedRef = useRef(true);

  // ✅ SOLUTION B: Initialiser avec détection synchrone pour éliminer le flash anglais
  const [currentLanguage, setCurrentLanguage] =
    useState<string>(getInitialLanguageSync());
  const [translations, setTranslations] = useState<TranslationKeys>(
    {} as TranslationKeys,
  );
  const [loading, setLoading] = useState(true);
  // ✅ SOLUTION D: forceRender et NotificationManager supprimés - Redondants avec useState/useEffect

  // LOGIQUE CORRIGÉE : PRIORITÉ 1 = Backend (table users), PRIORITÉ 2 = localStorage, PRIORITÉ 3 = Navigateur
  useEffect(() => {
    const getUserLanguage = async () => {
      try {
        // PRIORITÉ 1: Backend - Langue depuis la table public.users (source de vérité)
        try {
          const authData = localStorage.getItem("intelia-expert-auth");
          if (authData) {
            // Import dynamique pour éviter circular dependency
            const { apiClient } = await import("@/lib/api/client");
            const response = await apiClient.getSecure<{ language?: string }>("/auth/me");

            if (response.success && response.data?.language) {
              const userLang = response.data.language;

              if (isValidLanguageCode(userLang)) {
                secureLog.log(`[i18n] PRIORITÉ 1 - Langue backend (table users): ${userLang}`);
                if (!isMountedRef.current) return; // PROTECTION
                setCurrentLanguage(userLang);

                // Synchroniser localStorage avec le backend
                try {
                  const langData = {
                    state: {
                      currentLanguage: userLang,
                    },
                  };
                  localStorage.setItem("intelia-language", JSON.stringify(langData));
                  secureLog.log("[i18n] localStorage synchronisé avec backend");
                } catch (error) {
                  secureLog.warn("[i18n] Erreur sync localStorage:", error);
                }
                return;
              }
            }
          }
        } catch (error) {
          // Si le backend échoue, continuer avec localStorage
          secureLog.log("[i18n] Pas de session authentifiée ou erreur backend, vérification localStorage");
        }

        // PRIORITÉ 2: localStorage (choix précédent si pas de backend)
        const storedLang = getStoredLanguage();
        if (storedLang && isValidLanguageCode(storedLang)) {
          secureLog.log(
            `[i18n] PRIORITÉ 2 - Langue localStorage: ${storedLang}`,
          );
          if (!isMountedRef.current) return; // PROTECTION
          setCurrentLanguage(storedLang);
          return;
        }

        // PRIORITÉ 3: Navigateur (détection automatique en dernier recours)
        const browserLang = detectBrowserLanguage();
        secureLog.log(`[i18n] PRIORITÉ 3 - Langue navigateur: ${browserLang}`);
        if (!isMountedRef.current) return; // PROTECTION
        setCurrentLanguage(browserLang);
      } catch (error) {
        secureLog.log(
          "Erreur initialisation langue, utilisation navigateur par défaut",
        );
        const browserLang = detectBrowserLanguage();
        if (!isMountedRef.current) return; // PROTECTION
        setCurrentLanguage(browserLang);
      }
    };
    getUserLanguage();
  }, []);

  // ✅ SOLUTION D: Polling interval supprimé - Le storage event listener suffit

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
      if (!isMountedRef.current) return; // Protection démontage
      setLoading(true);
      try {
        const loadedTranslations = await loadTranslations(currentLanguage);

        // PROTECTION: Vérifier que le composant est toujours monté avant state update
        if (!isMountedRef.current) return;

        // IMPORTANT: Mettre à jour les translations AVANT de mettre loading à false
        setTranslations(loadedTranslations);
        setLoading(false);
      } catch (error) {
        secureLog.error("Erreur chargement traductions:", error);

        // PROTECTION: Vérifier que le composant est toujours monté
        if (!isMountedRef.current) return;
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

    // NOUVEAU: Synchroniser avec le profil Supabase
    try {
      // Import dynamique pour éviter circular dependency
      const { useAuthStore } = await import("@/lib/stores/auth");
      const authStore = useAuthStore.getState();

      if (authStore.isAuthenticated && authStore.user) {
        secureLog.log("[i18n] Synchronisation langue avec profil Supabase...");
        await authStore.updateProfile({ language: newLanguage });
        secureLog.log("[i18n] Langue synchronisée avec le profil Supabase");
      } else {
        secureLog.log("[i18n] Utilisateur non connecté, pas de sync Supabase");
      }
    } catch (error) {
      secureLog.warn("[i18n] Erreur sync profil Supabase:", error);
      // Ne pas bloquer si la sync échoue - l'utilisateur a quand même sa langue dans localStorage
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
