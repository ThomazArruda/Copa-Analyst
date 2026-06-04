export const isValidFileSize = (bytes: number, maxMB = 20): boolean =>
  bytes <= maxMB * 1024 * 1024;

export const isValidMimeType = (mime: string): boolean =>
  ['application/pdf', 'image/jpeg', 'image/png'].includes(mime);

export const isValidSemester = (semester: string): boolean =>
  /^\d{4}\.(1|2)$/.test(semester);

export const isValidEmail = (email: string): boolean =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

export const isValidPassword = (password: string): boolean =>
  password.length >= 8;

export const isValidUsername = (username: string): boolean =>
  /^[a-zA-Z0-9_]{3,30}$/.test(username);
