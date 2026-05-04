export const ERROR_MESSAGES = {
  // Authentication errors
  auth: {
    invalidCredentials: "Invalid username or password. Please try again.",
    accountLocked: "Your account has been locked. Please contact support.",
    sessionExpired: "Your session has expired. Please sign in again.",
    unauthorized: "You don't have permission to access this resource.",
    notAuthenticated: "Please sign in to continue.",
    mfaRequired: "Multi-factor authentication is required for this action.",
    invalidMfaCode: "Invalid verification code. Please try again.",
  },

  // Network errors
  network: {
    offline: "You appear to be offline. Please check your internet connection.",
    timeout: "Request timed out. Please try again.",
    serverError: "Our servers are having issues. Please try again later.",
    connectionFailed: "Connection failed. Please check your internet and try again.",
  },

  // Validation errors
  validation: {
    required: "This field is required.",
    email: "Please enter a valid email address.",
    username:
      "Username must be 3-20 characters and contain only letters, numbers, and underscores.",
    password: "Password must be at least 8 characters long.",
    passwordMismatch: "Passwords do not match.",
    orcid: "Please enter a valid ORCID (e.g., 0000-0002-1825-0097).",
    institution: "Institution name is required.",
    role: "Please specify your role.",
    invalidFormat: "Invalid format. Please check and try again.",
  },

  // Profile errors
  profile: {
    updateFailed: "Failed to update profile. Please try again.",
    loadFailed: "Unable to load profile information.",
    photoUploadFailed: "Failed to upload photo. Please try again.",
    invalidFileType: "Please upload a valid image file (JPG, PNG, or GIF).",
    fileTooLarge: "File is too large. Please upload an image under 5MB.",
  },

  // Form errors
  form: {
    invalidData: "Please correct the highlighted fields.",
    submitFailed: "Failed to submit form. Please try again.",
    saveDraftFailed: "Failed to save draft. Your changes may not be preserved.",
  },

  // Generic errors
  generic: {
    unexpected: "An unexpected error occurred. Please try again.",
    notFound: "The requested resource was not found.",
    forbidden: "You don't have permission to perform this action.",
    maintenance: "System is under maintenance. Please try again later.",
  },
};

export const SUCCESS_MESSAGES = {
  profile: {
    updated: "Your profile has been updated successfully.",
    photoUploaded: "Profile photo uploaded successfully.",
    settingsSaved: "Settings saved successfully.",
  },
  auth: {
    signedIn: "Welcome back! You've been signed in successfully.",
    signedUp: "Account created successfully! Please complete your profile.",
    signedOut: "You've been signed out successfully.",
    passwordChanged: "Password changed successfully.",
    mfaEnabled: "Multi-factor authentication enabled successfully.",
    mfaDisabled: "Multi-factor authentication disabled.",
  },
  form: {
    submitted: "Form submitted successfully.",
    saved: "Your changes have been saved.",
    draftSaved: "Draft saved automatically.",
  },
};

export const INFO_MESSAGES = {
  onboarding: {
    welcome: "Welcome to INSPECT-AI! Let's get your account set up.",
    profileRequired: "Please complete your profile to access all features.",
    skipAvailable: "You can skip this step and complete it later.",
  },
  profile: {
    incompleteProfile: "Your profile is incomplete. Some features may be limited.",
    verificationPending: "Your account is pending verification.",
  },
  auth: {
    passwordStrengthWeak: "Consider using a stronger password.",
    passwordStrengthGood: "Good password strength.",
    passwordStrengthExcellent: "Excellent password strength!",
    mfaRecommended: "Enable multi-factor authentication for enhanced security.",
  },
};

export const WARNING_MESSAGES = {
  unsavedChanges: "You have unsaved changes. Are you sure you want to leave?",
  deleteAccount: "This action cannot be undone. Are you sure you want to delete your account?",
  removeConnection: "Are you sure you want to remove this connection?",
  sensitiveAction: "This is a sensitive action. Please confirm your password to continue.",
};

// Helper functions for error handling
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    // Check for common error patterns
    if (error.message.includes("network") || error.message.includes("fetch")) {
      return ERROR_MESSAGES.network.connectionFailed;
    }
    if (error.message.includes("timeout")) {
      return ERROR_MESSAGES.network.timeout;
    }
    if (error.message.includes("unauthorized") || error.message.includes("401")) {
      return ERROR_MESSAGES.auth.unauthorized;
    }
    if (error.message.includes("forbidden") || error.message.includes("403")) {
      return ERROR_MESSAGES.generic.forbidden;
    }
    if (error.message.includes("not found") || error.message.includes("404")) {
      return ERROR_MESSAGES.generic.notFound;
    }

    // Return the actual error message if it's user-friendly
    if (error.message.length < 100 && !error.message.includes("stack")) {
      return error.message;
    }
  }

  return ERROR_MESSAGES.generic.unexpected;
}

export function isNetworkError(error: unknown): boolean {
  if (error instanceof Error) {
    return (
      error.message.includes("network") ||
      error.message.includes("fetch") ||
      error.message.includes("ERR_NETWORK") ||
      error.message.includes("ERR_INTERNET_DISCONNECTED")
    );
  }
  return false;
}

export function isAuthError(error: unknown): boolean {
  if (error instanceof Error) {
    return (
      error.message.includes("unauthorized") ||
      error.message.includes("401") ||
      error.message.includes("authentication") ||
      error.message.includes("unauthenticated")
    );
  }
  return false;
}
