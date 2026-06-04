import { useCallback } from 'react';
import { useAuthStore } from '@/stores/authStore';
import * as authService from '@/services/auth.service';

export const useAuth = () => {
  const { user, session, profile, isLoading, clearAuth } = useAuthStore();

  const signIn = useCallback(async (email: string, password: string) => {
    return authService.signIn(email, password);
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    return authService.signUp(email, password);
  }, []);

  const signInWithGoogle = useCallback(async () => {
    return authService.signInWithGoogle();
  }, []);

  const signOut = useCallback(async () => {
    await authService.signOut();
    clearAuth();
  }, [clearAuth]);

  const resetPassword = useCallback(async (email: string) => {
    return authService.resetPassword(email);
  }, []);

  return {
    user,
    session,
    profile,
    isLoading,
    isAuthenticated: !!session,
    signIn,
    signUp,
    signInWithGoogle,
    signOut,
    resetPassword,
  };
};
