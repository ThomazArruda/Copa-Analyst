import { getUploadCountToday, getDownloadCountThisMonth } from '@/services/documents.service';

jest.mock('@/services/supabase', () => ({
  supabase: {
    from: jest.fn(() => ({
      select: jest.fn().mockReturnThis(),
      eq: jest.fn().mockReturnThis(),
      gte: jest.fn().mockReturnThis(),
      order: jest.fn().mockReturnThis(),
      limit: jest.fn().mockResolvedValue({ data: [], error: null }),
      single: jest.fn().mockResolvedValue({ data: null, error: null }),
      range: jest.fn().mockReturnThis(),
      or: jest.fn().mockReturnThis(),
      insert: jest.fn().mockReturnThis(),
      upsert: jest.fn().mockResolvedValue({ error: null }),
      delete: jest.fn().mockReturnThis(),
      maybeSingle: jest.fn().mockResolvedValue({ data: null, error: null }),
    })),
    rpc: jest.fn().mockResolvedValue({ error: null }),
  },
}));

describe('documents.service', () => {
  beforeEach(() => jest.clearAllMocks());

  describe('getUploadCountToday', () => {
    it('returns count from supabase', async () => {
      const { supabase } = require('@/services/supabase');
      const mockChain = {
        select: jest.fn().mockReturnThis(),
        eq: jest.fn().mockReturnThis(),
        gte: jest.fn().mockResolvedValue({ count: 3, error: null }),
      };
      supabase.from.mockReturnValueOnce(mockChain);

      const count = await getUploadCountToday('user-123');
      expect(count).toBe(3);
    });

    it('returns 0 when no uploads today', async () => {
      const { supabase } = require('@/services/supabase');
      const mockChain = {
        select: jest.fn().mockReturnThis(),
        eq: jest.fn().mockReturnThis(),
        gte: jest.fn().mockResolvedValue({ count: 0, error: null }),
      };
      supabase.from.mockReturnValueOnce(mockChain);

      const count = await getUploadCountToday('user-123');
      expect(count).toBe(0);
    });
  });

  describe('getDownloadCountThisMonth', () => {
    it('returns monthly download count', async () => {
      const { supabase } = require('@/services/supabase');
      const mockChain = {
        select: jest.fn().mockReturnThis(),
        eq: jest.fn().mockReturnThis(),
        gte: jest.fn().mockResolvedValue({ count: 12, error: null }),
      };
      supabase.from.mockReturnValueOnce(mockChain);

      const count = await getDownloadCountThisMonth('user-123');
      expect(count).toBe(12);
    });
  });
});
