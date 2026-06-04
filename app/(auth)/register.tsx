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
  ScrollView,
} from 'react-native';
import { Link, router } from 'expo-router';
import { useAuth } from '@/hooks/useAuth';
import { isValidEmail, isValidPassword } from '@/utils/validators';

export default function RegisterScreen() {
  const { signUp } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    if (!email || !password || !confirm) {
      Alert.alert('Atenção', 'Preencha todos os campos.');
      return;
    }
    if (!isValidEmail(email)) {
      Alert.alert('E-mail inválido', 'Informe um e-mail válido.');
      return;
    }
    if (!isValidPassword(password)) {
      Alert.alert('Senha fraca', 'A senha deve ter pelo menos 8 caracteres.');
      return;
    }
    if (password !== confirm) {
      Alert.alert('Senhas diferentes', 'As senhas não coincidem.');
      return;
    }
    setLoading(true);
    try {
      await signUp(email.trim().toLowerCase(), password);
      router.replace('/(auth)/onboarding');
    } catch (err: any) {
      Alert.alert('Erro ao criar conta', err.message ?? 'Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-white dark:bg-neutral-950"
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        contentContainerClassName="flex-grow justify-center px-6 py-10"
        keyboardShouldPersistTaps="handled"
      >
        <TouchableOpacity onPress={() => router.back()} className="mb-6">
          <Text className="text-primary-600 text-base">← Voltar</Text>
        </TouchableOpacity>

        <Text className="text-3xl font-bold text-neutral-900 dark:text-white mb-2">
          Criar conta
        </Text>
        <Text className="text-neutral-500 mb-8">
          Junte-se à comunidade ProvaPool
        </Text>

        <TextInput
          className="border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3 mb-4 text-base text-neutral-900 dark:text-white bg-neutral-50 dark:bg-neutral-900"
          placeholder="E-mail universitário"
          placeholderTextColor="#9CA3AF"
          keyboardType="email-address"
          autoCapitalize="none"
          value={email}
          onChangeText={setEmail}
        />

        <TextInput
          className="border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3 mb-4 text-base text-neutral-900 dark:text-white bg-neutral-50 dark:bg-neutral-900"
          placeholder="Senha (mínimo 8 caracteres)"
          placeholderTextColor="#9CA3AF"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />

        <TextInput
          className="border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3 mb-8 text-base text-neutral-900 dark:text-white bg-neutral-50 dark:bg-neutral-900"
          placeholder="Confirmar senha"
          placeholderTextColor="#9CA3AF"
          secureTextEntry
          value={confirm}
          onChangeText={setConfirm}
        />

        <TouchableOpacity
          className="bg-primary-600 rounded-xl py-4 items-center"
          onPress={handleRegister}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text className="text-white font-semibold text-base">Criar Conta</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
