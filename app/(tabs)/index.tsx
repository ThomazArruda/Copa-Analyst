import { useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, ActivityIndicator, RefreshControl } from 'react-native';
import { router } from 'expo-router';
import { useRecentDocuments, usePopularDocuments } from '@/hooks/useDocuments';
import { useAuthStore } from '@/stores/authStore';
import { DEMO_MODE, mockDocuments } from '@/mocks';
import type { Document } from '@/types/app.types';

const TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  prova: { bg: 'bg-red-100', text: 'text-red-700' },
  lista: { bg: 'bg-blue-100', text: 'text-blue-700' },
  resumo: { bg: 'bg-green-100', text: 'text-green-700' },
  gabarito: { bg: 'bg-yellow-100', text: 'text-yellow-700' },
};

const TYPE_LABELS: Record<string, string> = {
  prova: 'Prova',
  lista: 'Lista',
  resumo: 'Resumo',
  gabarito: 'Gabarito',
};

function DocumentCard({ doc }: { doc: Document }) {
  const colors = TYPE_COLORS[doc.type];
  return (
    <TouchableOpacity
      className="bg-white dark:bg-neutral-800 rounded-xl p-4 mb-3 mx-4 shadow-sm border border-neutral-100 dark:border-neutral-700"
      onPress={() => router.push(`/document/${doc.id}`)}
      activeOpacity={0.7}
    >
      <View className="flex-row items-start justify-between mb-2">
        <Text
          className="text-base font-semibold text-neutral-900 dark:text-white flex-1 mr-2"
          numberOfLines={2}
        >
          {doc.title}
        </Text>
        {colors && (
          <View className={`px-2 py-0.5 rounded-full ${colors.bg}`}>
            <Text className={`text-xs font-medium ${colors.text}`}>
              {TYPE_LABELS[doc.type] ?? doc.type}
            </Text>
          </View>
        )}
      </View>

      {doc.subject && (
        <Text className="text-sm text-neutral-500 dark:text-neutral-400 mb-1">
          {doc.subject.name}
          {doc.professor ? ` • ${doc.professor}` : ''}
        </Text>
      )}

      <View className="flex-row items-center mt-1 gap-3">
        <Text className="text-xs text-neutral-400">▲ {doc.score}</Text>
        <Text className="text-xs text-neutral-400">↓ {doc.download_count}</Text>
        {doc.semester && (
          <Text className="text-xs text-neutral-400">{doc.semester}</Text>
        )}
      </View>
    </TouchableOpacity>
  );
}

function Section({
  title,
  documents,
  loading,
}: {
  title: string;
  documents: Document[];
  loading: boolean;
}) {
  return (
    <View className="mb-6">
      <Text className="text-lg font-bold text-neutral-900 dark:text-white px-4 mb-3">{title}</Text>
      {loading ? (
        <ActivityIndicator color="#4F46E5" />
      ) : documents.length === 0 ? (
        <Text className="text-neutral-400 text-center py-4">Nenhum documento ainda</Text>
      ) : (
        documents.map((doc) => <DocumentCard key={doc.id} doc={doc} />)
      )}
    </View>
  );
}

export default function HomeScreen() {
  const { profile } = useAuthStore();
  const {
    data: recentData = [],
    isLoading: loadingRecent,
    refetch,
  } = useRecentDocuments(profile?.institution_id ?? undefined);
  const { data: popularData = [], isLoading: loadingPopular } = usePopularDocuments();
  const [refreshing, setRefreshing] = useState(false);

  const recent = DEMO_MODE ? mockDocuments.slice(0, 3) : recentData;
  const popular = DEMO_MODE
    ? [...mockDocuments].sort((a, b) => b.score - a.score)
    : popularData;

  const onRefresh = async () => {
    setRefreshing(true);
    if (!DEMO_MODE) await refetch();
    else await new Promise((r) => setTimeout(r, 600));
    setRefreshing(false);
  };

  return (
    <FlatList
      className="flex-1 bg-neutral-50 dark:bg-neutral-950"
      data={[]}
      renderItem={null}
      keyExtractor={() => 'dummy'}
      ListHeaderComponent={
        <>
          <View className="px-4 pt-14 pb-4">
            <Text className="text-2xl font-bold text-neutral-900 dark:text-white">
              Olá{profile?.full_name ? `, ${profile.full_name.split(' ')[0]}` : ''} 👋
            </Text>
            <Text className="text-neutral-500 text-sm mt-1">
              Encontre provas e materiais de estudo
            </Text>
            {DEMO_MODE && (
              <View className="mt-3 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                <Text className="text-amber-700 text-xs font-medium">
                  🚧 Modo demo — dados de exemplo, Supabase não conectado
                </Text>
              </View>
            )}
          </View>

          <Section
            title="Recentes na sua faculdade"
            documents={recent}
            loading={DEMO_MODE ? false : loadingRecent}
          />
          <Section
            title="Mais populares"
            documents={popular}
            loading={DEMO_MODE ? false : loadingPopular}
          />
        </>
      }
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#4F46E5" />
      }
    />
  );
}
