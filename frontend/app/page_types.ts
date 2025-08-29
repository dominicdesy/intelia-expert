// page_types.ts
export interface Country {
  value: string
  label: string
  phoneCode: string
  flag?: string
}

export interface LoginData {
  email: string
  password: string
  rememberMe: boolean
}

export interface SignupData {
  email: string
  password: string
  confirmPassword: string
  firstName: string
  lastName: string
  linkedinProfile: string
  country: string
  countryCode: string
  areaCode: string
  phoneNumber: string
  companyName: string
  companyWebsite: string
  companyLinkedin: string
}

export interface TranslationStrings {
  title: string
  email: string
  password: string
  confirmPassword: string
  login: string
  signup: string
  rememberMe: string
  forgotPassword: string
  newToIntelia: string
  connecting: string
  creating: string
  loginError: string
  signupError: string
  emailRequired: string
  emailInvalid: string
  passwordRequired: string
  passwordTooShort: string
  passwordMismatch: string
  firstNameRequired: string
  lastNameRequired: string
  countryRequired: string
  phoneInvalid: string
  terms: string
  privacy: string
  gdprNotice: string
  needHelp: string
  contactSupport: string
  createAccount: string
  backToLogin: string
  confirmationSent: string
  accountCreated: string
  personalInfo: string
  firstName: string
  lastName: string
  linkedinProfile: string
  contact: string
  country: string
  countryCode: string
  areaCode: string
  phoneNumber: string
  company: string
  companyName: string
  companyWebsite: string
  companyLinkedin: string
  optional: string
  required: string
  close: string
  alreadyHaveAccount: string
  authSuccess: string
  authError: string
  authIncomplete: string
  sessionCleared: string
  forceLogout: string
  loadingCountries: string
  limitedCountryList: string
  selectCountry: string
  // NOUVEAUX CHAMPS AJOUTÉS
  emailPlaceholder: string
  passwordPlaceholder: string
}