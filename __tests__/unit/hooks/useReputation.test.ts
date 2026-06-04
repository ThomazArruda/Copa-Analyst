import { useReputation } from '@/hooks/useReputation';

const runHook = (reputation: number, plan: 'free' | 'pro') =>
  useReputation({ reputation, plan });

describe('useReputation', () => {
  describe('monthlyDownloadLimit', () => {
    it('returns 20 for free user with positive reputation', () => {
      expect(runHook(45, 'free').monthlyDownloadLimit).toBe(20);
    });
    it('returns 20 for free user with zero reputation', () => {
      expect(runHook(0, 'free').monthlyDownloadLimit).toBe(20);
    });
    it('returns 3 for free user with negative reputation', () => {
      expect(runHook(-1, 'free').monthlyDownloadLimit).toBe(3);
    });
    it('returns Infinity for pro user regardless of reputation', () => {
      expect(runHook(-100, 'pro').monthlyDownloadLimit).toBe(Infinity);
      expect(runHook(0, 'pro').monthlyDownloadLimit).toBe(Infinity);
      expect(runHook(1000, 'pro').monthlyDownloadLimit).toBe(Infinity);
    });
  });

  describe('canDownload', () => {
    it('allows download within limit', () => {
      const { canDownload } = runHook(10, 'free');
      expect(canDownload(19)).toBe(true);
    });
    it('blocks download at limit', () => {
      const { canDownload } = runHook(10, 'free');
      expect(canDownload(20)).toBe(false);
    });
    it('always allows pro user to download', () => {
      const { canDownload } = runHook(0, 'pro');
      expect(canDownload(9999)).toBe(true);
    });
  });

  describe('canUploadToday', () => {
    it('allows upload within daily limit', () => {
      const { canUploadToday } = runHook(10, 'free');
      expect(canUploadToday(4)).toBe(true);
    });
    it('blocks upload at daily limit', () => {
      const { canUploadToday } = runHook(10, 'free');
      expect(canUploadToday(5)).toBe(false);
    });
  });
});
