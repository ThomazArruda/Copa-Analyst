import { isValidFileSize, isValidMimeType, isValidSemester, isValidEmail, isValidPassword } from '@/utils/validators';

describe('validators', () => {
  describe('isValidFileSize', () => {
    it('accepts file within limit', () => {
      expect(isValidFileSize(10 * 1024 * 1024)).toBe(true);
    });
    it('rejects file above limit', () => {
      expect(isValidFileSize(21 * 1024 * 1024)).toBe(false);
    });
    it('accepts exactly at limit', () => {
      expect(isValidFileSize(20 * 1024 * 1024)).toBe(true);
    });
    it('accepts custom limit', () => {
      expect(isValidFileSize(5 * 1024 * 1024, 5)).toBe(true);
      expect(isValidFileSize(6 * 1024 * 1024, 5)).toBe(false);
    });
  });

  describe('isValidMimeType', () => {
    it('accepts PDF', () => expect(isValidMimeType('application/pdf')).toBe(true));
    it('accepts JPEG', () => expect(isValidMimeType('image/jpeg')).toBe(true));
    it('accepts PNG', () => expect(isValidMimeType('image/png')).toBe(true));
    it('rejects Word doc', () => expect(isValidMimeType('application/msword')).toBe(false));
    it('rejects MP4', () => expect(isValidMimeType('video/mp4')).toBe(false));
  });

  describe('isValidSemester', () => {
    it('accepts valid format 2024.1', () => expect(isValidSemester('2024.1')).toBe(true));
    it('accepts valid format 2024.2', () => expect(isValidSemester('2024.2')).toBe(true));
    it('rejects semester 3', () => expect(isValidSemester('2024.3')).toBe(false));
    it('rejects short year', () => expect(isValidSemester('24.1')).toBe(false));
    it('rejects missing dot', () => expect(isValidSemester('20241')).toBe(false));
  });

  describe('isValidEmail', () => {
    it('accepts valid email', () => expect(isValidEmail('user@uni.edu.br')).toBe(true));
    it('rejects missing @', () => expect(isValidEmail('useruni.edu.br')).toBe(false));
    it('rejects missing domain', () => expect(isValidEmail('user@')).toBe(false));
  });

  describe('isValidPassword', () => {
    it('accepts 8+ chars', () => expect(isValidPassword('senha123')).toBe(true));
    it('rejects less than 8 chars', () => expect(isValidPassword('abc123')).toBe(false));
  });
});
