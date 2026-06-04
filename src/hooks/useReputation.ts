import type { Profile } from '@/types/app.types';

interface ReputationInfo {
  monthlyDownloadLimit: number;
  dailyUploadLimit: number;
  canDownload: (downloadCountThisMonth: number) => boolean;
  canUploadToday: (uploadCountToday: number) => boolean;
}

export const useReputation = (profile: Pick<Profile, 'reputation' | 'plan'>): ReputationInfo => {
  const monthlyDownloadLimit =
    profile.plan === 'pro'
      ? Infinity
      : profile.reputation >= 0
      ? 20
      : 3;

  const dailyUploadLimit = profile.plan === 'pro' ? Infinity : 5;

  const canDownload = (downloadCountThisMonth: number) =>
    downloadCountThisMonth < monthlyDownloadLimit;

  const canUploadToday = (uploadCountToday: number) =>
    uploadCountToday < dailyUploadLimit;

  return { monthlyDownloadLimit, dailyUploadLimit, canDownload, canUploadToday };
};
