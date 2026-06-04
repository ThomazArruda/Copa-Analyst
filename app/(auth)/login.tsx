import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Link, router } from 'expo-router';
import { useAuth } from '@/hooks/useAuth';

export default function LoginScreen() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Atenção', 'Preencha e-mail e senha.');
      return;
    }
    setLoading(true);
    try {
      await signIn(email.trim().toLowerCase(), password);
      router.replace('/(tabs)');
    } catch (err: any) {
      Alert.alert('Erro ao entrar', err.message ?? 'Verifique suas credenciais.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-white dark:bg-neutral-950"
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View className="flex-1 justify-center px-6">
        <Text className="text-4xl font-bold text-primary-600 mb-2">ProvaPool</Text>
        <Text className="text-base text-neutral-500 mb-10">
          Repositório colaborativo de provas
        </Text>

        <TextInput
          className="border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3 mb-4 text-base text-neutral-900 dark:text-white bg-neutral-50 dark:bg-neutral-900"
          placeholder="E-mail"
          placeholderTextColor="#9CA3AF"
          keyboardType="email-address"
          autoCapitalize="none"
          value={email}
          onChangeText={setEmail}
          testID="input-email"
        />

        <TextInput
          className="border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3 mb-2 text-base text-neutral-900 dark:text-white bg-neutral-50 dark:bg-neutral-900"
          placeholder="Senha"
          placeholderTextColor="#9CA3AF"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
          testID="input-password"
        />

        <Link href="/(auth)/forgot-password" asChild>
          <TouchableOpacity className="self-end mb-6">
            <Text className="text-sm text-primary-600">Esqueci minha senha</Text>
          </TouchableOpacity>
        </Link>

        <TouchableOpacity
          className="bg-primary-600 rounded-xl py-4 items-center mb-4"
          onPress={handleLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text className="text-white font-semibold text-base">Entrar</Text>
          )}
        </TouchableOpacity>

        <View className="flex-row justify-center mt-4">
          <Text className="text-neutral-500">Não tem conta? </Text>
          <Link href="/(auth)/register" asChild>
            <TouchableOpacity>
              <Text className="text-primary-600 font-semibold">Criar conta</Text>
            </TouchableOpacity>
          </Link>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}
