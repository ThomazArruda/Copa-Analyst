import { useState, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useDocumentSearch } from '@/hooks/useDocuments';
import { useFilterStore } from '@/stores/filterStore';
import type { Document } from '@/types/app.types';

const TYPE_OPTIONS = [
  { label: 'Todos', value: undefined },
  { label: 'Provas', value: 'prova' as const },
  { label: 'Listas', value: 'lista' as const },
  { label: 'Resumos', value: 'resumo' as const },
  { label: 'Gabaritos', value: 'gabarito' as const },
];

const TYPE_LABELS: Record<string, string> = {
  prova: 'Prova',
  lista: 'Lista',
  resumo: 'Resumo',
  gabarito: 'Gabarito',
};

export default function SearchScreen() {
  const [query, setQuery] = useState('');
  const { type, setFilter } = useFilterStore();
  const { data: results = [], isLoading } = useDocumentSearch({ query, type });

  const renderDoc = useCallback(
    ({ item }: { item: Document }) => (
      <TouchableOpacity
        className="bg-white dark:bg-neutral-800 mx-4 mb-3 p-4 rounded-xl border border-neutral-100 dark:border-neutral-700"
        onPress={() => router.push(`/document/${item.id}`)}
        activeOpacity={0.7}
      >
        <Text className="font-semibold text-neutral-900 dark:text-white" numberOfLines={2}>
          {item.title}
        </Text>
        {item.subject && (
          <Text className="text-sm text-neutral-500 mt-1">{item.subject.name}</Text>
        )}
        <View className="flex-row items-center mt-2 gap-3">
          {item.type && (
            <Text className="text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 px-2 py-0.5 rounded-full">
              {TYPE_LABELS[item.type] ?? item.type}
            </Text>
          )}
          <Text className="text-xs text-neutral-400">▲ {item.score}</Text>
          <Text className="text-xs text-neutral-400">↓ {item.download_count}</Text>
        </View>
      </TouchableOpacity>
    ),
    []
  );

  return (
    <View className="flex-1 bg-neutral-50 dark:bg-neutral-950">
      {/* Header */}
      <View className="px-4 pt-14 pb-3">
        <Text className="text-2xl font-bold text-neutral-900 dark:text-white mb-3">Buscar</Text>

        {/* Search input */}
        <View className="flex-row items-center bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl px-3 py-2">
          <Ionicons name="search-outline" size={18} color="#9CA3AF" />
          <TextInput
            className="flex-1 ml-2 text-base text-neutral-900 dark:text-white"
            placeholder="Matéria, professor ou instituição..."
            placeholderTextColor="#9CA3AF"
            value={query}
            onChangeText={setQuery}
            returnKeyType="search"
            autoCapitalize="none"
          />
          {query.length > 0 && (
            <TouchableOpacity onPress={() => setQuery('')}>
              <Ionicons name="close-circle" size={18} color="#9CA3AF" />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Type filters */}
      <View className="px-4 mb-3">
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={TYPE_OPTIONS}
          keyExtractor={(item) => item.label}
          renderItem={({ item }) => (
            <TouchableOpacity
              className={`mr-2 px-4 py-2 rounded-full border ${
                type === item.value
                  ? 'bg-primary-600 border-primary-600'
                  : 'bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
              }`}
              onPress={() => setFilter({ type: item.value })}
            >
              <Text
                className={`text-sm font-medium ${
                  type === item.value ? 'text-white' : 'text-neutral-700 dark:text-neutral-300'
                }`}
              >
                {item.label}
              </Text>
            </TouchableOpacity>
          )}
        />
      </View>

      {/* Results */}
      {isLoading ? (
        <ActivityIndicator className="mt-10" color="#4F46E5" />
      ) : query.length === 0 ? (
        <View className="flex-1 items-center justify-center">
          <Ionicons name="search" size={48} color="#D1D5DB" />
          <Text className="text-neutral-400 mt-3">Digite para buscar documentos</Text>
        </View>
      ) : (
        <FlatList
          data={results}
          renderItem={renderDoc}
          keyExtractor={(item) => item.id}
          contentContainerClassName="pb-10"
          ListEmptyComponent={
            <View className="flex-1 items-center justify-center pt-20">
              <Text className="text-neutral-400">Nenhum resultado para "{query}"</Text>
            </View>
          }
        />
      )}
    </View>
  );
}
