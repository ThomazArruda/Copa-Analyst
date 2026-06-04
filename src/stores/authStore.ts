import { create } from 'zustand';
import type { Session, User } from '@supabase/supabase-js';
import type { Profile } from '@/types/app.types';
import { DEMO_MODE, mockUser, mockProfile } from '@/mocks';

interface AuthState {
  user: User | null;
  session: Session | null;
  profile: Profile | null;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setSession: (session: Session | null) => void;
  setProfile: (profile: Profile | null) => void;
  setIsLoading: (loading: boolean) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  // Em demo mode o store já nasce com usuário preenchido — sem depender de useEffect
  user: DEMO_MODE ? (mockUser as unknown as User) : null,
  session: null,
  profile: DEMO_MODE ? mockProfile : null,
  isLoading: !DEMO_MODE, // false imediatamente em demo; true aguarda Supabase no modo real
  setUser: (user) => set({ user }),
  setSession: (session) => set({ session }),
  setProfile: (profile) => set({ profile }),
  setIsLoading: (isLoading) => set({ isLoading }),
  clearAuth: () => set({ user: null, session: null, profile: null }),
}));
