import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, ActivityIndicator, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import { router } from 'expo-router';
import { useAuth } from '@/hooks/useAuth';
import { isValidEmail } from '@/utils/validators';

export default function ForgotPasswordScreen() {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleReset = async () => {
    if (!isValidEmail(email)) {
      Alert.alert('E-mail inválido', 'Informe um e-mail válido.');
      return;
    }
    setLoading(true);
    try {
      await resetPassword(email.trim().toLowerCase());
      setSent(true);
    } catch (err: any) {
      Alert.alert('Erro', err.message ?? 'Tente novamente.');
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
        <TouchableOpacity onPress={() => router.back()} className="mb-8">
          <Text className="text-primary-600 text-base">← Voltar</Text>
        </TouchableOpacity>

        <Text className="text-3xl font-bold text-neutral-900 dark:text-white mb-2">
          Recuperar senha
        </Text>

        {sent ? (
          <>
            <Text className="text-neutral-500 mb-8">
              Enviamos um link de recuperação para {email}. Verifique sua caixa de entrada.
            </Text>
            <TouchableOpacity className="bg-primary-600 rounded-xl py-4 items-center" onPress={() => router.replace('/(auth)/login')}>
              <Text className="text-white font-semibold">Voltar ao login</Text>
            </TouchableOpacity>
          </>
        ) : (
          <>
            <Text className="text-neutral-500 mb-8">
              Digite seu e-mail e enviaremos um link para redefinir sua senha.
            </Text>
            <TextInput
              className="border border-neutral-300 dark:border-neutral-700 rounded-xl px-4 py-3 mb-6 text-base text-neutral-900 dark:text-white bg-neutral-50 dark:bg-neutral-900"
              placeholder="Seu e-mail"
              placeholderTextColor="#9CA3AF"
              keyboardType="email-address"
              autoCapitalize="none"
              value={email}
              onChangeText={setEmail}
            />
            <TouchableOpacity
              className="bg-primary-600 rounded-xl py-4 items-center"
              onPress={handleReset}
              disabled={loading}
            >
              {loading ? <ActivityIndicator color="#fff" /> : <Text className="text-white font-semibold">Enviar link</Text>}
            </TouchableOpacity>
          </>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}
