import { Redirect } from 'expo-router';
import { View, ActivityIndicator } from 'react-native';
import { useAuthStore } from '@/stores/authStore';

/**
 * Rota raiz — decide para onde navegar:
 *   - autenticado (ou demo mode) → /(tabs)
 *   - não autenticado            → /(auth)/login
 *
 * O <Redirect> é o padrão correto do Expo Router: ao contrário de
 * router.replace(), ele age dentro da árvore de componentes APÓS
 * o navigator estar montado, evitando o erro "navigate before mounting".
 */
export default function Index() {
  const { user, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color="#4F46E5" />
      </View>
    );
  }

  if (user) {
    return <Redirect href="/(tabs)" />;
  }

  return <Redirect href="/(auth)/login" />;
}
