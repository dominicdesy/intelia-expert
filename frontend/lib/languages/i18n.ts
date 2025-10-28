/**
 * I18N
 * Version: 1.4.1
 * Last modified: 2025-10-26
 */
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
  "about.backToHome": string;
  "about.companyInformation": string;
  "about.companyName": string;
  "about.downloadDescription": string;
  "about.downloadFull": string;
  "about.email": string;
  "about.introduction": string;
  "about.lastUpdated": string;
  "about.license": string;
  "about.licensesUsed": string;
  "about.location": string;
  "about.openSourceLicenses": string;
  "about.pageTitle": string;
  "about.thirdPartyIntro": string;
  "about.thirdPartyNotices": string;
  "about.version": string;
  "about.versionDate": string;
  "about.versionInfo": string;
  "about.website": string;
  "account.notifications": string;
  "account.preferences": string;
  "account.privacy": string;
  "account.security": string;
  "account.settings": string;
  "admin.accessDenied": string;
  "admin.currency.loadError": string;
  "admin.history.loadError": string;
  "admin.plans.actions": string;
  "admin.plans.active": string;
  "admin.plans.basePriceUSD": string;
  "admin.plans.clickToEdit": string;
  "admin.plans.displayName": string;
  "admin.plans.editName": string;
  "admin.plans.editQuota": string;
  "admin.plans.inactive": string;
  "admin.plans.loadError": string;
  "admin.plans.nameButton": string;
  "admin.plans.nameUpdated": string;
  "admin.plans.noPlans": string;
  "admin.plans.plan": string;
  "admin.plans.priceUpdated": string;
  "admin.plans.questions": string;
  "admin.plans.quota": string;
  "admin.plans.quotaButton": string;
  "admin.plans.quotaUpdated": string;
  "admin.plans.recalculateConfirm": string;
  "admin.plans.recalculateError": string;
  "admin.plans.recalculateSuccess": string;
  "admin.plans.status": string;
  "admin.plans.subtitle": string;
  "admin.plans.tierDeveloped": string;
  "admin.plans.tierEmerging": string;
  "admin.plans.tierIntermediate": string;
  "admin.plans.tierPremium": string;
  "admin.plans.tierPricing": string;
  "admin.plans.tierPricingSubtitle": string;
  "admin.plans.title": string;
  "admin.plans.updateError": string;
  "admin.plans.usdPricingNote": string;
  "admin.pricing.cancel": string;
  "admin.pricing.countriesConfigured": string;
  "admin.pricing.country": string;
  "admin.pricing.currency": string;
  "admin.pricing.customPrice": string;
  "admin.pricing.customPriceTooltip": string;
  "admin.pricing.customizeNote": string;
  "admin.pricing.deleteButton": string;
  "admin.pricing.deleteConfirm": string;
  "admin.pricing.deleteError": string;
  "admin.pricing.deleteSuccess": string;
  "admin.pricing.edit": string;
  "admin.pricing.editButton": string;
  "admin.pricing.loadError": string;
  "admin.pricing.marketingPrice": string;
  "admin.pricing.marketingPriceTooltip": string;
  "admin.pricing.noCountries": string;
  "admin.pricing.noCountriesFound": string;
  "admin.pricing.refresh": string;
  "admin.pricing.save": string;
  "admin.pricing.searchPlaceholder": string;
  "admin.pricing.sortAZ": string;
  "admin.pricing.sortTier": string;
  "admin.pricing.tier": string;
  "admin.pricing.tier1": string;
  "admin.pricing.tier2": string;
  "admin.pricing.tier3": string;
  "admin.pricing.tier4": string;
  "admin.pricing.tierLevel": string;
  "admin.pricing.tierUpdateError": string;
  "admin.pricing.tierUpdated": string;
  "admin.pricing.title": string;
  "admin.pricing.updateError": string;
  "admin.quality.analysisComplete": string;
  "admin.quality.analyzeConfirm": string;
  "admin.quality.analyzeError": string;
  "admin.quality.deleteConfirm": string;
  "admin.quality.deleteError": string;
  "admin.quality.loadError": string;
  "admin.quality.markError": string;
  "admin.quality.markedFalsePositive": string;
  "admin.quality.markedReviewed": string;
  "admin.questions.noQuestionsToExport": string;
  "admin.subscriptions.activeSubscriptions": string;
  "admin.subscriptions.back": string;
  "admin.subscriptions.exportComing": string;
  "admin.subscriptions.exportData": string;
  "admin.subscriptions.loadError": string;
  "admin.subscriptions.loading": string;
  "admin.subscriptions.monthlyRevenue": string;
  "admin.subscriptions.openStripeDashboard": string;
  "admin.subscriptions.percentage": string;
  "admin.subscriptions.plan": string;
  "admin.subscriptions.planBreakdown": string;
  "admin.subscriptions.quickActions": string;
  "admin.subscriptions.refreshData": string;
  "admin.subscriptions.revenue": string;
  "admin.subscriptions.subscribers": string;
  "admin.subscriptions.subtitle": string;
  "admin.subscriptions.tabs.history": string;
  "admin.subscriptions.tabs.overview": string;
  "admin.subscriptions.tabs.plans": string;
  "admin.subscriptions.tabs.pricing": string;
  "admin.subscriptions.title": string;
  "admin.subscriptions.totalSubscriptions": string;
  "app.description": string;
  "auth.accountCreated": string;
  "auth.connecting": string;
  "auth.continueWith": string;
  "auth.createAccount": string;
  "auth.creating": string;
  "auth.emailAlreadyExists": string;
  "auth.emailNotConfirmed": string;
  "auth.error": string;
  "auth.forgotPassword": string;
  "auth.incomplete": string;
  "auth.invalidCredentials": string;
  "auth.login": string;
  "auth.newToIntelia": string;
  "auth.noAccountYet": string;
  "auth.oauthError": string;
  "auth.passwordRequirementsNotMet": string;
  "auth.success": string;
  "billing.billingCurrency": string;
  "billing.canSelectDifferent": string;
  "billing.changeCurrency": string;
  "billing.currencyAlreadySet": string;
  "billing.currencyDescription": string;
  "billing.currencyRequired": string;
  "billing.currencyRequiredDescription": string;
  "billing.currencyRequiredForUpgrade": string;
  "billing.currencyUpdateFailed": string;
  "billing.currencyUpdated": string;
  "billing.current": string;
  "billing.currentCurrency": string;
  "billing.currentPlan": string;
  "billing.discount15": string;
  "billing.errorLoadingCurrency": string;
  "billing.errorTitle": string;
  "billing.free": string;
  "billing.freePlan": string;
  "billing.loading": string;
  "billing.loadingCurrency": string;
  "billing.manageSubscription": string;
  "billing.monthly": string;
  "billing.notSetYet": string;
  "billing.notes.secure": string;
  "billing.notes.secureDesc": string;
  "billing.notes.trial": string;
  "billing.notes.trialDesc": string;
  "billing.notes.unlimited": string;
  "billing.popular": string;
  "billing.recommended": string;
  "billing.redirecting": string;
  "billing.selectCurrency": string;
  "billing.selectYourCurrency": string;
  "billing.startFreeTrial": string;
  "billing.subscribe": string;
  "billing.suggested": string;
  "billing.suggestedBasedOnLocation": string;
  "billing.trial14days": string;
  "billing.yearly": string;
  "chat.addImages": string;
  "chat.analyzeImageDefault": string;
  "chat.askQuestion": string;
  "chat.authInitError": string;
  "chat.clarificationInstruction": string;
  "chat.clarificationMode": string;
  "chat.clarificationPlaceholder": string;
  "chat.commentNotSent": string;
  "chat.cot.analysis": string;
  "chat.cot.answer": string;
  "chat.cot.hideReasoning": string;
  "chat.cot.showReasoning": string;
  "chat.cot.thinking": string;
  "chat.disclaimer": string;
  "chat.emptyContent": string;
  "chat.errorMessage": string;
  "chat.feedbackCommentPrefix": string;
  "chat.feedbackGeneralError": string;
  "chat.feedbackSendError": string;
  "chat.feedbackThanks": string;
  "chat.formatError": string;
  "chat.helpfulResponse": string;
  "chat.historyLoadError": string;
  "chat.historyLoaded": string;
  "chat.imageQuotaCheckError": string;
  "chat.imageQuotaExceeded": string;
  "chat.imageQuotaNoPlan": string;
  "chat.imageQuotaPlanNotAllowed": string;
  "chat.imageQuotaRemaining": string;
  "chat.imageQuotaUnlimited": string;
  "chat.imageSent": string;
  "chat.imagesCount": string;
  "chat.loading": string;
  "chat.loadingChat": string;
  "chat.logout": string;
  "chat.newConversation": string;
  "chat.noConversations": string;
  "chat.noMessages": string;
  "chat.notHelpfulResponse": string;
  "chat.placeholder": string;
  "chat.placeholderMobile": string;
  "chat.planName": string;
  "chat.questionsUsed": string;
  "chat.quotaExceeded": string;
  "chat.recentLogout": string;
  "chat.redirectingInProgress": string;
  "chat.redirectingLogin": string;
  "chat.rejectionMessage": string;
  "chat.removeImage": string;
  "chat.satisfactionCommentPlaceholder": string;
  "chat.satisfactionCommentPrompt": string;
  "chat.satisfactionHelpful": string;
  "chat.satisfactionNeutral": string;
  "chat.satisfactionOkay": string;
  "chat.satisfactionPoor": string;
  "chat.satisfactionQuestion": string;
  "chat.satisfactionSatisfied": string;
  "chat.satisfactionSkip": string;
  "chat.satisfactionThankYou.default": string;
  "chat.satisfactionThankYou.neutral.0": string;
  "chat.satisfactionThankYou.neutral.1": string;
  "chat.satisfactionThankYou.neutral.2": string;
  "chat.satisfactionThankYou.satisfied.0": string;
  "chat.satisfactionThankYou.satisfied.1": string;
  "chat.satisfactionThankYou.satisfied.2": string;
  "chat.satisfactionThankYou.unsatisfied.0": string;
  "chat.satisfactionThankYou.unsatisfied.1": string;
  "chat.satisfactionThankYou.unsatisfied.2": string;
  "chat.satisfactionThanks": string;
  "chat.satisfactionUnsatisfied": string;
  "chat.scrollToBottom": string;
  "chat.send": string;
  "chat.sendError": string;
  "chat.sending": string;
  "chat.sessionExpired": string;
  "chat.startQuestion": string;
  "chat.stop": string;
  "chat.submit": string;
  "chat.suggestedTopics": string;
  "chat.upgradePrompt": string;
  "chat.uploadImages": string;
  "chat.voiceError": string;
  "chat.voiceInput": string;
  "chat.voiceListening": string;
  "chat.voiceNoSpeech": string;
  "chat.voiceNotSupported": string;
  "chat.voicePermissionDenied": string;
  "chat.voiceRealtimeAdminOnly": string;
  "chat.voiceRealtimeBetaTitle": string;
  "chat.voiceRealtimeClickStart": string;
  "chat.voiceRealtimeConnecting": string;
  "chat.voiceRealtimeDoubleClick": string;
  "chat.voiceRealtimeError": string;
  "chat.voiceRealtimeIdle": string;
  "chat.voiceRealtimeListening": string;
  "chat.voiceRealtimeSpeaking": string;
  "chat.voiceRecording": string;
  "chat.voiceStart": string;
  "chat.voiceStop": string;
  "chat.welcome": string;
  "common.and": string;
  "common.appName": string;
  "common.apply": string;
  "common.cancel": string;
  "common.clear": string;
  "common.confirm": string;
  "common.delete": string;
  "common.edit": string;
  "common.error": string;
  "common.filter": string;
  "common.goBack": string;
  "common.loading": string;
  "common.notSpecified": string;
  "common.optional": string;
  "common.or": string;
  "common.reset": string;
  "common.save": string;
  "common.saving": string;
  "common.search": string;
  "common.success": string;
  "common.unexpectedError": string;
  "common.update": string;
  "common.view": string;
  "components.cachedData": string;
  "components.close": string;
  "components.delete": string;
  "components.selectImage": string;
  "components.subscriptionPlans": string;
  "components.toggleBilling": string;
  "contact.corporatePlanSubject": string;
  "contact.email": string;
  "contact.emailDescription": string;
  "contact.message": string;
  "contact.messageSent": string;
  "contact.phone": string;
  "contact.phoneDescription": string;
  "contact.sendMessage": string;
  "contact.subject": string;
  "contact.supportEmail": string;
  "contact.title": string;
  "contact.website": string;
  "contact.websiteDescription": string;
  "countries.fallbackWarning": string;
  "countries.limitedList": string;
  "countries.listLabel": string;
  "countries.loading": string;
  "countries.noResults": string;
  "countries.searchPlaceholder": string;
  "countries.select": string;
  "country.belgium": string;
  "country.brazil": string;
  "country.canada": string;
  "country.france": string;
  "country.mexico": string;
  "country.switzerland": string;
  "country.usa": string;
  "date.format": string;
  "date.today": string;
  "dialog.cancel": string;
  "dialog.confirm": string;
  "dialog.no": string;
  "dialog.ok": string;
  "dialog.yes": string;
  "error.changePassword": string;
  "error.checkConnection": string;
  "error.companyNameTooLong": string;
  "error.confirmPasswordRequired": string;
  "error.connection": string;
  "error.currentPasswordIncorrect": string;
  "error.currentPasswordRequired": string;
  "error.emailInvalid": string;
  "error.emailRequired": string;
  "error.emailTooLong": string;
  "error.firstNameRequired": string;
  "error.firstNameTooLong": string;
  "error.generic": string;
  "error.invalidShareToken": string;
  "error.lastNameRequired": string;
  "error.lastNameTooLong": string;
  "error.linkedinInvalid": string;
  "error.loadVoiceSettings": string;
  "error.newPasswordRequired": string;
  "error.noTokenReceived": string;
  "error.passwordServerError": string;
  "error.phonePrefix": string;
  "error.saveVoiceSettings": string;
  "error.serverError": string;
  "error.serviceUnavailable": string;
  "error.unexpectedResponse": string;
  "error.updateProfile": string;
  "error.urlInvalid": string;
  "error.urlProtocol": string;
  "error.userNotConnected": string;
  "error.validationErrors": string;
  "export.button": string;
  "export.error": string;
  "export.exporting": string;
  "export.notAuthenticated": string;
  "export.planRestriction": string;
  "export.serverError": string;
  "export.tooltip": string;
  "feedback.characterCount": string;
  "feedback.description": string;
  "feedback.learnMore": string;
  "feedback.limitWarning": string;
  "feedback.negativePlaceholder": string;
  "feedback.negativeTitle": string;
  "feedback.positivePlaceholder": string;
  "feedback.positiveTitle": string;
  "feedback.privacyNotice": string;
  "feedback.send": string;
  "feedback.sendError": string;
  "feedback.sending": string;
  "forgotPassword.backToLogin": string;
  "forgotPassword.checkInbox": string;
  "forgotPassword.connectionError": string;
  "forgotPassword.contactSupport": string;
  "forgotPassword.description": string;
  "forgotPassword.emailLabel": string;
  "forgotPassword.emailNotFound": string;
  "forgotPassword.emailPlaceholder": string;
  "forgotPassword.emailSent": string;
  "forgotPassword.enterEmail": string;
  "forgotPassword.genericError": string;
  "forgotPassword.invalidEmail": string;
  "forgotPassword.noAccount": string;
  "forgotPassword.otpEmailHint": string;
  "forgotPassword.redirecting": string;
  "forgotPassword.securityInfo": string;
  "forgotPassword.securityInfo2": string;
  "forgotPassword.sendButton": string;
  "forgotPassword.sending": string;
  "forgotPassword.supportProblem": string;
  "forgotPassword.title": string;
  "forgotPassword.tooManyAttempts": string;
  "form.passwordLowercase": string;
  "form.passwordMinLength": string;
  "form.passwordMismatch": string;
  "form.passwordNumber": string;
  "form.passwordSpecial": string;
  "form.passwordUppercase": string;
  "form.phoneFormat": string;
  "form.required": string;
  "gdpr.confirmDelete": string;
  "gdpr.contactSupport": string;
  "gdpr.deleteAccount": string;
  "gdpr.dpoContactTitle": string;
  "gdpr.dpoDescription": string;
  "gdpr.dpoResponseTime": string;
  "gdpr.dpoTitle": string;
  "gdpr.exportData": string;
  "gdpr.notice": string;
  "gdpr.signupNotice": string;
  "help.buttonTitle": string;
  "help.cameraDesc": string;
  "help.cameraTitle": string;
  "help.close": string;
  "help.finish": string;
  "help.historyDesc": string;
  "help.historyTitle": string;
  "help.inputDesc": string;
  "help.inputTitle": string;
  "help.newChatDesc": string;
  "help.newChatTitle": string;
  "help.next": string;
  "help.previous": string;
  "help.profileDesc": string;
  "help.profileTitle": string;
  "help.sendDesc": string;
  "help.sendTitle": string;
  "help.voiceAssistantDesc": string;
  "help.voiceAssistantTitle": string;
  "help.voiceDesc": string;
  "help.voiceTitle": string;
  "history.clear": string;
  "history.confirmClear": string;
  "history.confirmClearAll": string;
  "history.conversationsLoaded": string;
  "history.delete": string;
  "history.deleteConversation": string;
  "history.export": string;
  "history.filter": string;
  "history.groups.older": string;
  "history.groups.thisMonth": string;
  "history.groups.thisWeek": string;
  "history.groups.today": string;
  "history.groups.yesterday": string;
  "history.loadingConversations": string;
  "history.loadingConversationsFor": string;
  "history.loadingError": string;
  "history.messageCount": string;
  "history.newConversation": string;
  "history.noConversations": string;
  "history.noResults": string;
  "history.refresh": string;
  "history.renderState": string;
  "history.retrievingHistory": string;
  "history.search": string;
  "history.startQuestion": string;
  "history.toggleClicked": string;
  "history.userPresent": string;
  "invitation.accountCreatedPleaseLogin": string;
  "invitation.backendValidation": string;
  "invitation.completeProfile": string;
  "invitation.createAccount": string;
  "invitation.creatingAccount": string;
  "invitation.emailFromInvitation": string;
  "invitation.errors.accountCompletion": string;
  "invitation.errors.generic": string;
  "invitation.errors.missingAccessToken": string;
  "invitation.errors.missingToken": string;
  "invitation.errors.noInvitation": string;
  "invitation.errors.processing": string;
  "invitation.errors.profileCompletion": string;
  "invitation.errors.tokenValidation": string;
  "invitation.finalizingInvitation": string;
  "invitation.invitedBy": string;
  "invitation.loadingInvitation": string;
  "invitation.needHelp": string;
  "invitation.personalMessage": string;
  "invitation.phoneAutoFill": string;
  "invitation.pleaseLogin": string;
  "invitation.processing": string;
  "invitation.redirecting.dashboard": string;
  "invitation.redirecting.login": string;
  "invitation.status.accountCreated": string;
  "invitation.status.accountError": string;
  "invitation.status.processing": string;
  "invitation.status.tokenError": string;
  "invitation.status.tokenValidated": string;
  "invitation.success.accountCreated": string;
  "invitation.success.tokenValidated": string;
  "invitation.success.welcome": string;
  "invitation.validatedSuccess": string;
  "invitation.validating": string;
  "invitation.waitMessage": string;
  "invitation.welcomeComplete": string;
  "invite.alreadyInvitedByOther": string;
  "invite.alreadyInvitedByYou": string;
  "invite.authError": string;
  "invite.authRetrievalError": string;
  "invite.emailAddresses": string;
  "invite.emailFormat": string;
  "invite.emailHelp": string;
  "invite.emailPlaceholder": string;
  "invite.emailRequired": string;
  "invite.error": string;
  "invite.footerInfo": string;
  "invite.invalidEmail": string;
  "invite.invalidEmails": string;
  "invite.invitationSent": string;
  "invite.inviteOthers": string;
  "invite.lastLogin": string;
  "invite.loginRequired": string;
  "invite.loginRequiredTitle": string;
  "invite.maxLimit": string;
  "invite.messageHelp": string;
  "invite.messagePlaceholder": string;
  "invite.namePlaceholder": string;
  "invite.noValidEmails": string;
  "invite.optional": string;
  "invite.personalMessage": string;
  "invite.rateLimit": string;
  "invite.recipientCount": string;
  "invite.reconnectSuggestion": string;
  "invite.retryOrContact": string;
  "invite.send": string;
  "invite.sendButton": string;
  "invite.sendError": string;
  "invite.sendFailed": string;
  "invite.sendStatus": string;
  "invite.sending": string;
  "invite.sentSuccess": string;
  "invite.sessionExpired": string;
  "invite.sessionExpiredDetail": string;
  "invite.subtitle": string;
  "invite.title": string;
  "invite.userExists": string;
  "invite.userExistsWithDate": string;
  "invite.validationError": string;
  "language.changeSuccess": string;
  "language.continueWithoutReload": string;
  "language.current": string;
  "language.debug.changeError": string;
  "language.debug.changing": string;
  "language.debug.interfaceUpdated": string;
  "language.debug.localStorageSaved": string;
  "language.debug.modalClosed": string;
  "language.description": string;
  "language.interfaceUpdated": string;
  "language.reloadForWidget": string;
  "language.reloadNow": string;
  "language.title": string;
  "language.updating": string;
  "legal.and": string;
  "legal.lastUpdated": string;
  "legal.privacy": string;
  "legal.privacyPolicy": string;
  "legal.privacyPolicyDesc": string;
  "legal.readPrivacyPolicy": string;
  "legal.readTermsOfService": string;
  "legal.terms": string;
  "legal.termsOfService": string;
  "legal.termsOfServiceDesc": string;
  "login.email": string;
  "login.emailLabel": string;
  "login.emailPlaceholder": string;
  "login.hidePassword": string;
  "login.password": string;
  "login.passwordLabel": string;
  "login.passwordPlaceholder": string;
  "login.rememberMe": string;
  "login.showPassword": string;
  "modal.back": string;
  "modal.cancel": string;
  "modal.close": string;
  "modal.loading": string;
  "modal.save": string;
  "modal.updating": string;
  "nav.about": string;
  "nav.account": string;
  "nav.clearAll": string;
  "nav.closeSidebar": string;
  "nav.contact": string;
  "nav.conversationSidebar": string;
  "nav.history": string;
  "nav.inviteFriend": string;
  "nav.language": string;
  "nav.legal": string;
  "nav.logout": string;
  "nav.newConversation": string;
  "nav.profile": string;
  "nav.settings": string;
  "nav.statistics": string;
  "nav.subscription": string;
  "page.title": string;
  "passkey.addedOn": string;
  "passkey.benefits.faster": string;
  "passkey.benefits.noPassword": string;
  "passkey.benefits.secure": string;
  "passkey.description": string;
  "passkey.devices.supported": string;
  "passkey.info.benefits": string;
  "passkey.info.description": string;
  "passkey.info.devices": string;
  "passkey.info.whatIs": string;
  "passkey.login.button": string;
  "passkey.login.canceled": string;
  "passkey.login.description": string;
  "passkey.login.error": string;
  "passkey.login.inProgress": string;
  "passkey.login.success": string;
  "passkey.login.title": string;
  "passkey.manage.addedOn": string;
  "passkey.manage.confirmDelete": string;
  "passkey.manage.delete": string;
  "passkey.manage.deleteError": string;
  "passkey.manage.deleteSuccess": string;
  "passkey.manage.description": string;
  "passkey.manage.deviceName": string;
  "passkey.manage.lastUsed": string;
  "passkey.manage.local": string;
  "passkey.manage.never": string;
  "passkey.manage.noDevices": string;
  "passkey.manage.synced": string;
  "passkey.manage.title": string;
  "passkey.noPasskeys": string;
  "passkey.registered": string;
  "passkey.setup.alreadySetup": string;
  "passkey.setup.button": string;
  "passkey.setup.description": string;
  "passkey.setup.deviceName": string;
  "passkey.setup.devicePlaceholder": string;
  "passkey.setup.error": string;
  "passkey.setup.inProgress": string;
  "passkey.setup.notSupported": string;
  "passkey.setup.success": string;
  "passkey.setup.title": string;
  "passkey.setupButton": string;
  "passkey.setupTitle": string;
  "passkey.title": string;
  "phone.areaCode": string;
  "phone.areaCodeHelp": string;
  "phone.areaCodePlaceholder": string;
  "phone.countryCode": string;
  "phone.countryCodeHelp": string;
  "phone.limitedList": string;
  "phone.loading": string;
  "phone.loadingCodes": string;
  "phone.phoneNumber": string;
  "phone.phoneNumberHelp": string;
  "phone.phoneNumberPlaceholder": string;
  "phone.select": string;
  "phone.validation.countryRequired": string;
  "phone.validation.numberRequired": string;
  "placeholder.companyName": string;
  "placeholder.companyWebsite": string;
  "placeholder.confirmNewPassword": string;
  "placeholder.confirmPassword": string;
  "placeholder.countrySelect": string;
  "placeholder.createSecurePassword": string;
  "placeholder.currentPassword": string;
  "placeholder.email": string;
  "placeholder.firstName": string;
  "placeholder.jobTitle": string;
  "placeholder.lastName": string;
  "placeholder.linkedinCorporate": string;
  "placeholder.linkedinPersonal": string;
  "placeholder.newPassword": string;
  "plan.contactUs": string;
  "plan.corporate": string;
  "plan.corporate.description": string;
  "plan.corporate.feature1": string;
  "plan.corporate.feature2": string;
  "plan.corporate.feature3": string;
  "plan.corporate.feature4": string;
  "plan.corporate.feature5": string;
  "plan.corporate.feature6": string;
  "plan.currentPlan": string;
  "plan.elite": string;
  "plan.elite.description": string;
  "plan.elite.feature1": string;
  "plan.elite.feature2": string;
  "plan.elite.feature3": string;
  "plan.elite.feature4": string;
  "plan.elite.feature5": string;
  "plan.essential": string;
  "plan.essential.description": string;
  "plan.essential.feature1": string;
  "plan.essential.feature2": string;
  "plan.essential.feature3": string;
  "plan.essential.feature4": string;
  "plan.free": string;
  "plan.perMonth": string;
  "plan.popular": string;
  "plan.pro": string;
  "plan.pro.description": string;
  "plan.pro.feature1": string;
  "plan.pro.feature2": string;
  "plan.pro.feature3": string;
  "plan.pro.feature4": string;
  "plan.pro.feature5": string;
  "profile.accountType": string;
  "profile.accountType.producer": string;
  "profile.accountType.professional": string;
  "profile.areaCode": string;
  "profile.backToChat": string;
  "profile.category.breedingHatchery": string;
  "profile.category.description": string;
  "profile.category.equipmentTechnology": string;
  "profile.category.farmOperations": string;
  "profile.category.feedNutrition": string;
  "profile.category.healthVeterinary": string;
  "profile.category.label": string;
  "profile.category.managementOversight": string;
  "profile.category.other": string;
  "profile.category.otherPlaceholder": string;
  "profile.category.processing": string;
  "profile.category.why": string;
  "profile.company": string;
  "profile.companyLinkedin": string;
  "profile.companyName": string;
  "profile.companyWebsite": string;
  "profile.confirmPassword": string;
  "profile.contact": string;
  "profile.country": string;
  "profile.countryCode": string;
  "profile.currentPassword": string;
  "profile.description": string;
  "profile.email": string;
  "profile.emailNotEditable": string;
  "profile.error.deleteFailed": string;
  "profile.error.exportFailed": string;
  "profile.error.invalidAccountType": string;
  "profile.error.nameMinLength": string;
  "profile.error.updateFailed": string;
  "profile.firstName": string;
  "profile.fullName": string;
  "profile.jobTitle": string;
  "profile.lastName": string;
  "profile.linkedinCorporate": string;
  "profile.linkedinProfile": string;
  "profile.newPassword": string;
  "profile.optional": string;
  "profile.password": string;
  "profile.passwordChanged": string;
  "profile.passwordErrors": string;
  "profile.passwordRequirements": string;
  "profile.passwordRequirements8": string;
  "profile.passwordRequirementsLower": string;
  "profile.passwordRequirementsNumber": string;
  "profile.passwordRequirementsSpecial": string;
  "profile.passwordRequirementsUpper": string;
  "profile.personalInfo": string;
  "profile.phone": string;
  "profile.phoneNumber": string;
  "profile.privacy.cancel": string;
  "profile.privacy.confirmDelete": string;
  "profile.privacy.dataManagement": string;
  "profile.privacy.deleteAccount": string;
  "profile.privacy.deleteWarning": string;
  "profile.privacy.deleting": string;
  "profile.privacy.downloadData": string;
  "profile.privacy.exportData": string;
  "profile.privacy.exportDescription": string;
  "profile.privacy.retentionDescription": string;
  "profile.privacy.retentionPolicy": string;
  "profile.privacy.yesDelete": string;
  "profile.productionType.both": string;
  "profile.productionType.broiler": string;
  "profile.productionType.description": string;
  "profile.productionType.label": string;
  "profile.productionType.layer": string;
  "profile.productionType.why": string;
  "profile.professionalInfo": string;
  "profile.profileUpdated": string;
  "profile.saveChanges": string;
  "profile.saving": string;
  "profile.security": string;
  "profile.settings.chooseLanguage": string;
  "profile.settings.interfaceLanguage": string;
  "profile.settings.notifications": string;
  "profile.settings.receiveEmails": string;
  "profile.success.dataExported": string;
  "profile.success.profileUpdated": string;
  "profile.tabs.password": string;
  "profile.tabs.personalInfo": string;
  "profile.tabs.professionalInfo": string;
  "profile.title": string;
  "profile.whatsappDescription": string;
  "profile.whatsappNumber": string;
  "pwa.install.button": string;
  "pwa.install.dismiss": string;
  "pwa.install.subtitle": string;
  "pwa.install.title": string;
  "pwa.ios.close": string;
  "pwa.ios.instructions": string;
  "pwa.ios.step1": string;
  "pwa.ios.step2": string;
  "pwa.ios.step3": string;
  "pwa.ios.subtitle": string;
  "pwa.ios.title": string;
  "resetPassword.backToLogin": string;
  "resetPassword.confirmPassword": string;
  "resetPassword.contactSupport": string;
  "resetPassword.description": string;
  "resetPassword.errors.connectionProblem": string;
  "resetPassword.errors.generic": string;
  "resetPassword.errors.tokenExpired": string;
  "resetPassword.errors.tooManyAttempts": string;
  "resetPassword.invalidToken.backToSite": string;
  "resetPassword.invalidToken.description": string;
  "resetPassword.invalidToken.requestNew": string;
  "resetPassword.invalidToken.title": string;
  "resetPassword.needHelp": string;
  "resetPassword.newPassword": string;
  "resetPassword.passwordStrength": string;
  "resetPassword.requirements.hasLetter": string;
  "resetPassword.requirements.noRepetition": string;
  "resetPassword.requirements.reasonableLength": string;
  "resetPassword.securityInfo": string;
  "resetPassword.strength.excellent": string;
  "resetPassword.strength.good": string;
  "resetPassword.strength.medium": string;
  "resetPassword.strength.weak": string;
  "resetPassword.success.description": string;
  "resetPassword.success.goToSite": string;
  "resetPassword.tip.longerPassword": string;
  "resetPassword.tip.mixCase": string;
  "resetPassword.tip.specialChars": string;
  "resetPassword.tips": string;
  "resetPassword.title": string;
  "resetPassword.updateButton": string;
  "resetPassword.updating": string;
  "resetPassword.validatingLink": string;
  "resetPassword.validation.avoidSequences": string;
  "resetPassword.validation.letterRequired": string;
  "resetPassword.validation.maxLength": string;
  "resetPassword.validation.tooCommon": string;
  "resetPassword.validation.tooRepetitive": string;
  "share.anonymize": string;
  "share.anonymizeHelp": string;
  "share.button": string;
  "share.copied": string;
  "share.copy": string;
  "share.error": string;
  "share.expiration": string;
  "share.expiration.30days": string;
  "share.expiration.7days": string;
  "share.expiration.90days": string;
  "share.expiration.never": string;
  "share.expirationHelp": string;
  "share.generate": string;
  "share.generating": string;
  "share.modalTitle": string;
  "share.successMessage": string;
  "share.successTitle": string;
  "shared.answer": string;
  "shared.backToHome": string;
  "shared.createAccount": string;
  "shared.createFreeAccount": string;
  "shared.dataAnonymized": string;
  "shared.error": string;
  "shared.expired": string;
  "shared.expiresOn": string;
  "shared.generatedBy": string;
  "shared.impressed": string;
  "shared.loadError": string;
  "shared.loading": string;
  "shared.notFound": string;
  "shared.question": string;
  "shared.sharedBy": string;
  "shared.signIn": string;
  "shared.subtitle": string;
  "shared.title": string;
  "shared.tryFree": string;
  "shared.unavailable": string;
  "shared.viewCount": string;
  "shared.viewCountPlural": string;
  "signup.acceptTerms": string;
  "signup.and": string;
  "signup.loading": string;
  "signup.passwordsMatch": string;
  "signup.passwordsMismatch": string;
  "signup.searchCountry": string;
  "status.connected": string;
  "status.connecting": string;
  "status.disconnected": string;
  "status.offline": string;
  "status.online": string;
  "stripe.account.currentPlan": string;
  "stripe.account.manageSubscription": string;
  "stripe.account.monthlyBilling": string;
  "stripe.account.subscription": string;
  "stripe.account.upgradePlan": string;
  "stripe.admin.activeSubscriptions": string;
  "stripe.admin.back": string;
  "stripe.admin.exportComing": string;
  "stripe.admin.exportData": string;
  "stripe.admin.loading": string;
  "stripe.admin.loadingError": string;
  "stripe.admin.monthlyRevenue": string;
  "stripe.admin.openStripeDashboard": string;
  "stripe.admin.percentage": string;
  "stripe.admin.plan": string;
  "stripe.admin.planBreakdown": string;
  "stripe.admin.quickActions": string;
  "stripe.admin.refreshData": string;
  "stripe.admin.revenue": string;
  "stripe.admin.subscribers": string;
  "stripe.admin.subtitle": string;
  "stripe.admin.title": string;
  "stripe.admin.totalSubscriptions": string;
  "stripe.billing.cancel.backToHome": string;
  "stripe.billing.cancel.canStill": string;
  "stripe.billing.cancel.contactSupport": string;
  "stripe.billing.cancel.contactUs": string;
  "stripe.billing.cancel.continueEssential": string;
  "stripe.billing.cancel.message": string;
  "stripe.billing.cancel.needHelp": string;
  "stripe.billing.cancel.retry": string;
  "stripe.billing.cancel.retryLater": string;
  "stripe.billing.cancel.title": string;
  "stripe.billing.success.advanced": string;
  "stripe.billing.success.contactSupport": string;
  "stripe.billing.success.features": string;
  "stripe.billing.success.goToDashboard": string;
  "stripe.billing.success.manageSubscription": string;
  "stripe.billing.success.message": string;
  "stripe.billing.success.needHelp": string;
  "stripe.billing.success.priority": string;
  "stripe.billing.success.redirecting": string;
  "stripe.billing.success.seconds": string;
  "stripe.billing.success.thankyou": string;
  "stripe.billing.success.title": string;
  "stripe.billing.success.unlimited": string;
  "stripe.features.elite.all": string;
  "stripe.features.elite.api": string;
  "stripe.features.elite.customization": string;
  "stripe.features.elite.dedicated": string;
  "stripe.features.elite.unlimitedPriority": string;
  "stripe.features.essential.basic": string;
  "stripe.features.essential.emailSupport": string;
  "stripe.features.essential.questions": string;
  "stripe.features.pro.advanced": string;
  "stripe.features.pro.history": string;
  "stripe.features.pro.priority": string;
  "stripe.features.pro.unlimited": string;
  "stripe.plan.elite": string;
  "stripe.plan.essential": string;
  "stripe.plan.pro": string;
  "stripe.portal.error": string;
  "stripe.upgrade.choosePlan": string;
  "stripe.upgrade.currentPlan": string;
  "stripe.upgrade.currentPlanBadge": string;
  "stripe.upgrade.error": string;
  "stripe.upgrade.free": string;
  "stripe.upgrade.loading": string;
  "stripe.upgrade.paymentInfo": string;
  "stripe.upgrade.perMonth": string;
  "stripe.upgrade.redirecting": string;
  "stripe.upgrade.selectPlan": string;
  "stripe.upgrade.stripeLinkInfo": string;
  "stripe.upgrade.title": string;
  "subscription.cancel": string;
  "subscription.cancellation": string;
  "subscription.comparison.category.ai": string;
  "subscription.comparison.category.base": string;
  "subscription.comparison.category.capacity": string;
  "subscription.comparison.category.experience": string;
  "subscription.comparison.elite": string;
  "subscription.comparison.essential": string;
  "subscription.comparison.feature": string;
  "subscription.comparison.feature.adFree": string;
  "subscription.comparison.feature.history": string;
  "subscription.comparison.feature.imageAnalysis": string;
  "subscription.comparison.feature.languages": string;
  "subscription.comparison.feature.pdfExport": string;
  "subscription.comparison.feature.queries": string;
  "subscription.comparison.feature.roleAdaptation": string;
  "subscription.comparison.feature.voiceAssistant": string;
  "subscription.comparison.feature.voiceInput": string;
  "subscription.comparison.pro": string;
  "subscription.comparison.title": string;
  "subscription.comparison.value.100": string;
  "subscription.comparison.value.25perMonth": string;
  "subscription.comparison.value.30days": string;
  "subscription.comparison.value.unlimited": string;
  "subscription.comparison.value.unlimitedStar": string;
  "subscription.confirmCancel": string;
  "subscription.currentPlan": string;
  "subscription.description": string;
  "subscription.featuresIncluded": string;
  "subscription.free": string;
  "subscription.invoices": string;
  "subscription.modify": string;
  "subscription.payment": string;
  "subscription.premium.price": string;
  "subscription.title": string;
  "subscription.update": string;
  "success.authSynchronized": string;
  "success.languageUpdated": string;
  "success.passwordChanged": string;
  "success.profileUpdated": string;
  "success.voiceSettingsSaved": string;
  "ui.close": string;
  "ui.collapse": string;
  "ui.expand": string;
  "ui.menu": string;
  "ui.next": string;
  "ui.open": string;
  "ui.previous": string;
  "user.account": string;
  "user.logout": string;
  "user.menu": string;
  "user.profile": string;
  "user.settings": string;
  "userMenu.debug.changeDetected": string;
  "userMenu.debug.currentIsOpen": string;
  "userMenu.debug.logoutServiceError": string;
  "userMenu.debug.logoutViaService": string;
  "userMenu.debug.toggleOpen": string;
  "userMenu.debug.unmounting": string;
  "userMenu.openMenu": string;
  "userMenu.superAdmin": string;
  "validation.correctErrors": string;
  "validation.invalidData": string;
  "validation.password.lowercase": string;
  "validation.password.match": string;
  "validation.password.minLength": string;
  "validation.password.mismatch": string;
  "validation.password.number": string;
  "validation.password.requirements": string;
  "validation.password.special": string;
  "validation.password.uppercase": string;
  "validation.phone.incomplete": string;
  "validation.phone.invalid": string;
  "validation.required.accessToken": string;
  "validation.required.confirmPassword": string;
  "validation.required.country": string;
  "validation.required.email": string;
  "validation.required.firstName": string;
  "validation.required.fullName": string;
  "validation.required.lastName": string;
  "validation.required.password": string;
  "verification.autoRedirect": string;
  "verification.backToLogin": string;
  "verification.contactSupport": string;
  "verification.error.alreadyUsed": string;
  "verification.error.alreadyVerified": string;
  "verification.error.expired": string;
  "verification.error.generic": string;
  "verification.error.invalid": string;
  "verification.error.invalidOrExpired": string;
  "verification.error.network": string;
  "verification.error.possibleCauses": string;
  "verification.error.retrySignup": string;
  "verification.error.title": string;
  "verification.loadingVerification": string;
  "verification.loginNow": string;
  "verification.noEmail": string;
  "verification.pending.checkEmail": string;
  "verification.pending.emailSent": string;
  "verification.pending.emailSentTo": string;
  "verification.pending.nextSteps": string;
  "verification.pending.step1": string;
  "verification.pending.step2": string;
  "verification.pending.step3": string;
  "verification.pending.title": string;
  "verification.redirecting": string;
  "verification.refreshPage": string;
  "verification.retrySignup": string;
  "verification.subtitle": string;
  "verification.success.canLogin": string;
  "verification.success.confirmed": string;
  "verification.success.emailConfirmed": string;
  "verification.success.title": string;
  "verification.success.verified": string;
  "verification.supportQuestion": string;
  "verification.supportSubject": string;
  "verification.title": string;
  "verification.verifying": string;
  "voiceSettings.currentPlan": string;
  "voiceSettings.fast": string;
  "voiceSettings.faster": string;
  "voiceSettings.listen": string;
  "voiceSettings.normal": string;
  "voiceSettings.selectVoice": string;
  "voiceSettings.slower": string;
  "voiceSettings.speed": string;
  "voiceSettings.title": string;
  "voiceSettings.upgradeMessage": string;
  "voiceSettings.upgradeRequired": string;
  "voiceSettings.veryFast": string;
  "widget.buttonLabel": string;
  "widget.errorNetwork": string;
  "widget.errorQuota": string;
  "widget.errorToken": string;
  "widget.placeholder": string;
  "widget.sendButton": string;
  "widget.welcomeMessage": string;
};

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
