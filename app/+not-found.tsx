import { View, Text, TouchableOpacity } from 'react-native';
import { router } from 'expo-router';

export default function NotFoundScreen() {
  return (
    <View className="flex-1 items-center justify-center bg-white dark:bg-neutral-950 px-6">
      <Text className="text-6xl mb-4">🔍</Text>
      <Text className="text-xl font-bold text-neutral-900 dark:text-white mb-2">
        Página não encontrada
      </Text>
      <Text className="text-neutral-500 text-center mb-8">
        A rota que você acessou não existe.
      </Text>
      <TouchableOpacity
        className="bg-primary-600 px-8 py-3 rounded-xl"
        onPress={() => router.replace('/(tabs)')}
      >
        <Text className="text-white font-semibold">Ir para o início</Text>
      </TouchableOpacity>
    </View>
  );
}
