import { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  ScrollView,
  Modal,
} from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useDocument } from '@/hooks/useDocuments';
import { useAuthStore } from '@/stores/authStore';
import { useReputation } from '@/hooks/useReputation';
import {
  incrementViewCount,
  incrementDownloadCount,
  voteDocument,
  getUserVote,
  getDownloadCountThisMonth,
} from '@/services/documents.service';
import { getDocumentSignedUrl } from '@/services/storage.service';
import { supabase } from '@/services/supabase';
import { formatRelativeDate, formatFileSize } from '@/utils/formatters';

const DOWNVOTE_REASONS = [
  'Arquivo ilegível',
  'Conteúdo errado',
  'Duplicado',
  'Outro',
];

const TYPE_LABELS: Record<string, string> = {
  prova: 'Prova',
  lista: 'Lista',
  resumo: 'Resumo',
  gabarito: 'Gabarito',
};

export default function DocumentScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user, profile } = useAuthStore();
  const { data: doc, isLoading, error } = useDocument(id);
  const reputation = useReputation(profile ?? { reputation: 0, plan: 'free' });

  const [userVote, setUserVote] = useState<1 | -1 | null>(null);
  const [score, setScore] = useState(0);
  const [downloading, setDownloading] = useState(false);
  const [showDownvoteModal, setShowDownvoteModal] = useState(false);

  useEffect(() => {
    if (!doc || !user) return;
    setScore(doc.score);
    incrementViewCount(id).catch(() => null);
    getUserVote(id, user.id).then(setUserVote).catch(() => null);
  }, [doc, user, id]);

  const handleVote = async (value: 1 | -1, reason?: string) => {
    if (!user) return;
    const newVote = userVote === value ? null : value;
    const delta = newVote ? value : -value;
    setScore((s) => s + delta);
    setUserVote(newVote);

    try {
      if (newVote === null) {
        await supabase.from('votes').delete().eq('document_id', id).eq('user_id', user.id);
      } else {
        await voteDocument(id, newVote, reason);
      }
    } catch {
      // Revert optimistic update on failure
      setScore((s) => s - delta);
      setUserVote(userVote);
    }
  };

  const handleDownload = async () => {
    if (!user || !doc) return;
    const downloadCount = await getDownloadCountThisMonth(user.id);
    if (!reputation.canDownload(downloadCount)) {
      Alert.alert(
        'Limite atingido',
        `Você atingiu seu limite de ${reputation.monthlyDownloadLimit} downloads este mês.`
      );
      return;
    }

    setDownloading(true);
    try {
      const url = await getDocumentSignedUrl(doc.file_path);
      await incrementDownloadCount(id);
      // In a real app: use expo-file-system to download, or expo-web-browser to open
      Alert.alert('Download', 'URL gerada com sucesso. Integrando com viewer...');
    } catch (err: any) {
      Alert.alert('Erro', err.message ?? 'Não foi possível baixar o arquivo.');
    } finally {
      setDownloading(false);
    }
  };

  if (isLoading) {
    return (
      <View className="flex-1 items-center justify-center bg-white dark:bg-neutral-950">
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  if (error || !doc) {
    return (
      <View className="flex-1 items-center justify-center bg-white dark:bg-neutral-950 px-6">
        <Ionicons name="alert-circle-outline" size={48} color="#EF4444" />
        <Text className="text-neutral-500 text-center mt-4">
          Documento não encontrado ou indisponível.
        </Text>
        <TouchableOpacity onPress={() => router.back()} className="mt-6">
          <Text className="text-primary-600 font-medium">← Voltar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <>
      <ScrollView className="flex-1 bg-white dark:bg-neutral-950">
        <View className="px-4 pt-4 pb-10">
          {/* Title */}
          <Text className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">
            {doc.title}
          </Text>

          {/* Type badge */}
          <View className="flex-row flex-wrap gap-2 mb-4">
            <View className="bg-primary-100 px-3 py-1 rounded-full">
              <Text className="text-primary-700 text-sm font-medium">
                {TYPE_LABELS[doc.type] ?? doc.type}
              </Text>
            </View>
            {doc.semester && (
              <View className="bg-neutral-100 dark:bg-neutral-800 px-3 py-1 rounded-full">
                <Text className="text-neutral-600 dark:text-neutral-300 text-sm">{doc.semester}</Text>
              </View>
            )}
          </View>

          {/* Metadata */}
          <View className="bg-neutral-50 dark:bg-neutral-900 rounded-xl p-4 mb-4">
            {doc.subject && (
              <View className="flex-row justify-between mb-2">
                <Text className="text-sm text-neutral-500">Matéria</Text>
                <Text className="text-sm font-medium text-neutral-900 dark:text-white">{doc.subject.name}</Text>
              </View>
            )}
            {doc.professor && (
              <View className="flex-row justify-between mb-2">
                <Text className="text-sm text-neutral-500">Professor</Text>
                <Text className="text-sm font-medium text-neutral-900 dark:text-white">{doc.professor}</Text>
              </View>
            )}
            {doc.uploader && (
              <View className="flex-row justify-between mb-2">
                <Text className="text-sm text-neutral-500">Enviado por</Text>
                <Text className="text-sm font-medium text-neutral-900 dark:text-white">@{doc.uploader.username}</Text>
              </View>
            )}
            <View className="flex-row justify-between mb-2">
              <Text className="text-sm text-neutral-500">Data</Text>
              <Text className="text-sm font-medium text-neutral-900 dark:text-white">{formatRelativeDate(doc.created_at)}</Text>
            </View>
            <View className="flex-row justify-between">
              <Text className="text-sm text-neutral-500">Visualizações</Text>
              <Text className="text-sm font-medium text-neutral-900 dark:text-white">{doc.view_count}</Text>
            </View>
          </View>

          {/* Vote + Download */}
          <View className="flex-row gap-3 mb-6">
            <View className="flex-row items-center bg-neutral-100 dark:bg-neutral-800 rounded-xl overflow-hidden">
              <TouchableOpacity
                className={`px-4 py-3 ${userVote === 1 ? 'bg-green-500' : ''}`}
                onPress={() => handleVote(1)}
              >
                <Text className={`text-base ${userVote === 1 ? 'text-white' : 'text-neutral-700 dark:text-neutral-300'}`}>▲</Text>
              </TouchableOpacity>
              <Text className="px-3 font-semibold text-neutral-900 dark:text-white">{score}</Text>
              <TouchableOpacity
                className={`px-4 py-3 ${userVote === -1 ? 'bg-red-500' : ''}`}
                onPress={() => setShowDownvoteModal(true)}
              >
                <Text className={`text-base ${userVote === -1 ? 'text-white' : 'text-neutral-700 dark:text-neutral-300'}`}>▼</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity
              className="flex-1 bg-primary-600 rounded-xl items-center justify-center py-3 flex-row gap-2"
              onPress={handleDownload}
              disabled={downloading}
            >
              {downloading ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <>
                  <Ionicons name="download-outline" size={18} color="#fff" />
                  <Text className="text-white font-semibold">Download</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>

      {/* Downvote reason modal */}
      <Modal visible={showDownvoteModal} transparent animationType="slide">
        <View className="flex-1 justify-end bg-black/50">
          <View className="bg-white dark:bg-neutral-900 rounded-t-3xl px-4 pt-6 pb-10">
            <Text className="text-lg font-bold text-neutral-900 dark:text-white mb-4">
              Por que você está avaliando negativamente?
            </Text>
            {DOWNVOTE_REASONS.map((reason) => (
              <TouchableOpacity
                key={reason}
                className="py-4 border-b border-neutral-100 dark:border-neutral-800"
                onPress={() => {
                  setShowDownvoteModal(false);
                  handleVote(-1, reason);
                }}
              >
                <Text className="text-base text-neutral-700 dark:text-neutral-300">{reason}</Text>
              </TouchableOpacity>
            ))}
            <TouchableOpacity
              className="mt-4 items-center"
              onPress={() => setShowDownvoteModal(false)}
            >
              <Text className="text-neutral-500">Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </>
  );
}
