import { View, Text, TouchableOpacity, FlatList, ActivityIndicator, Alert } from 'react-native';
import { router } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/services/supabase';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/stores/authStore';
import { useReputation } from '@/hooks/useReputation';
import { DEMO_MODE, mockMyUploads } from '@/mocks';
import { formatReputation, formatRelativeDate } from '@/utils/formatters';
import type { Document } from '@/types/app.types';

export default function ProfileScreen() {
  const { signOut } = useAuth();
  const { user, profile } = useAuthStore();
  const reputation = useReputation(profile ?? { reputation: 0, plan: 'free' });

  const { data: uploadsData = [], isLoading } = useQuery({
    queryKey: ['profile', 'uploads', user?.id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('documents')
        .select('*, subject:subjects(name)')
        .eq('uploader_id', user!.id)
        .order('created_at', { ascending: false })
        .limit(20);
      if (error) throw error;
      return (data ?? []) as Document[];
    },
    enabled: !!user && !DEMO_MODE,
  });

  // Em demo mode usa uploads simulados
  const uploads = DEMO_MODE ? mockMyUploads : uploadsData;

  const handleSignOut = () => {
    Alert.alert('Sair', 'Deseja sair da sua conta?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Sair', style: 'destructive', onPress: signOut },
    ]);
  };

  const downloadLimit = reputation.monthlyDownloadLimit;

  return (
    <FlatList
      className="flex-1 bg-neutral-50 dark:bg-neutral-950"
      data={uploads}
      keyExtractor={(item) => item.id}
      ListHeaderComponent={
        <>
          <View className="px-4 pt-14 pb-4">
            <View className="flex-row items-center justify-between mb-6">
              <Text className="text-2xl font-bold text-neutral-900 dark:text-white">Meu Perfil</Text>
              <TouchableOpacity onPress={handleSignOut}>
                <Text className="text-red-500 text-sm font-medium">Sair</Text>
              </TouchableOpacity>
            </View>

            {/* Avatar + info */}
            <View className="bg-white dark:bg-neutral-800 rounded-2xl p-5 mb-4 border border-neutral-100 dark:border-neutral-700">
              <View className="flex-row items-center gap-4">
                <View className="w-16 h-16 rounded-full bg-primary-100 items-center justify-center">
                  <Text className="text-2xl font-bold text-primary-600">
                    {(profile?.username ?? user?.email ?? 'U')[0].toUpperCase()}
                  </Text>
                </View>
                <View className="flex-1">
                  <Text className="text-lg font-bold text-neutral-900 dark:text-white">
                    {profile?.full_name ?? profile?.username ?? user?.email?.split('@')[0]}
                  </Text>
                  <Text className="text-sm text-neutral-500">{user?.email}</Text>
                  <View className="flex-row items-center mt-1">
                    <Text className="text-xs font-medium px-2 py-0.5 rounded-full bg-primary-100 text-primary-700">
                      {profile?.plan === 'pro' ? '⭐ Pro' : 'Free'}
                    </Text>
                  </View>
                </View>
              </View>
            </View>

            {/* Stats */}
            <View className="flex-row gap-3 mb-4">
              <View className="flex-1 bg-white dark:bg-neutral-800 rounded-xl p-4 border border-neutral-100 dark:border-neutral-700 items-center">
                <Text className="text-2xl font-bold text-primary-600">
                  {formatReputation(profile?.reputation ?? 0)}
                </Text>
                <Text className="text-xs text-neutral-500 mt-1">Reputação</Text>
              </View>
              <View className="flex-1 bg-white dark:bg-neutral-800 rounded-xl p-4 border border-neutral-100 dark:border-neutral-700 items-center">
                <Text className="text-2xl font-bold text-neutral-900 dark:text-white">
                  {uploads.length}
                </Text>
                <Text className="text-xs text-neutral-500 mt-1">Uploads</Text>
              </View>
              <View className="flex-1 bg-white dark:bg-neutral-800 rounded-xl p-4 border border-neutral-100 dark:border-neutral-700 items-center">
                <Text className="text-2xl font-bold text-neutral-900 dark:text-white">
                  {downloadLimit === Infinity ? '∞' : downloadLimit}
                </Text>
                <Text className="text-xs text-neutral-500 mt-1">Downloads/mês</Text>
              </View>
            </View>

            <Text className="text-lg font-bold text-neutral-900 dark:text-white mb-3">
              Meus documentos
            </Text>
          </View>
        </>
      }
      renderItem={({ item }) => (
        <TouchableOpacity
          className="bg-white dark:bg-neutral-800 mx-4 mb-3 p-4 rounded-xl border border-neutral-100 dark:border-neutral-700"
          onPress={() => router.push(`/document/${item.id}`)}
          activeOpacity={0.7}
        >
          <Text className="font-semibold text-neutral-900 dark:text-white" numberOfLines={1}>
            {item.title}
          </Text>
          {item.subject && (
            <Text className="text-sm text-neutral-500 mt-0.5">{item.subject.name}</Text>
          )}
          <Text className="text-xs text-neutral-400 mt-1">{formatRelativeDate(item.created_at)}</Text>
        </TouchableOpacity>
      )}
      ListEmptyComponent={
        !isLoading ? (
          <Text className="text-center text-neutral-400 py-10">
            Você ainda não enviou nenhum documento
          </Text>
        ) : null
      }
      ListFooterComponent={isLoading && !DEMO_MODE ? <ActivityIndicator className="py-6" color="#4F46E5" /> : null}
      contentContainerClassName="pb-10"
    />
  );
}
