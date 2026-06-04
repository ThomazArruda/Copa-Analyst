import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '@/stores/authStore';
import { useReputation } from '@/hooks/useReputation';
import { isValidFileSize, isValidMimeType, isValidSemester } from '@/utils/validators';
import { formatFileSize } from '@/utils/formatters';
import { uploadDocument } from '@/services/storage.service';
import { createDocument, getUploadCountToday } from '@/services/documents.service';
import type { DocumentType } from '@/types/app.types';

const TYPE_OPTIONS: { label: string; value: DocumentType }[] = [
  { label: 'Prova', value: 'prova' },
  { label: 'Lista', value: 'lista' },
  { label: 'Resumo', value: 'resumo' },
  { label: 'Gabarito', value: 'gabarito' },
];

interface SelectedFile {
  uri: string;
  name: string;
  size: number;
  mimeType: string;
}

export default function UploadScreen() {
  const { user, profile } = useAuthStore();
  const reputation = useReputation(
    profile ?? { reputation: 0, plan: 'free' }
  );

  const [file, setFile] = useState<SelectedFile | null>(null);
  const [title, setTitle] = useState('');
  const [subjectName, setSubjectName] = useState('');
  const [professor, setProfessor] = useState('');
  const [semester, setSemester] = useState('');
  const [docType, setDocType] = useState<DocumentType>('prova');
  const [uploading, setUploading] = useState(false);

  const pickFile = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: ['application/pdf', 'image/jpeg', 'image/png'],
      copyToCacheDirectory: true,
    });

    if (result.canceled) return;
    const asset = result.assets[0];

    if (!isValidMimeType(asset.mimeType ?? '')) {
      Alert.alert('Tipo inválido', 'Apenas PDF, JPG e PNG são aceitos.');
      return;
    }
    if (!isValidFileSize(asset.size ?? 0)) {
      Alert.alert('Arquivo grande', `O arquivo deve ter no máximo 20 MB. Tamanho: ${formatFileSize(asset.size ?? 0)}`);
      return;
    }

    setFile({
      uri: asset.uri,
      name: asset.name,
      size: asset.size ?? 0,
      mimeType: asset.mimeType ?? 'application/pdf',
    });
    if (!title) setTitle(asset.name.replace(/\.[^/.]+$/, ''));
  };

  const handleUpload = async () => {
    if (!file || !title.trim() || !subjectName.trim() || !semester.trim()) {
      Alert.alert('Campos obrigatórios', 'Preencha todos os campos obrigatórios.');
      return;
    }
    if (!isValidSemester(semester)) {
      Alert.alert('Semestre inválido', 'Use o formato AAAA.N (ex: 2024.1)');
      return;
    }
    if (!user) return;

    // Check daily upload limit
    const uploadedToday = await getUploadCountToday(user.id);
    if (!reputation.canUploadToday(uploadedToday)) {
      Alert.alert('Limite atingido', 'Você atingiu o limite de 5 uploads por dia no plano gratuito.');
      return;
    }

    setUploading(true);
    try {
      const documentId = crypto.randomUUID();
      const filePath = await uploadDocument(user.id, documentId, file.uri, file.mimeType);

      // For MVP: use a placeholder subject_id (in production, fetch/create subject)
      await createDocument({
        uploader_id: user.id,
        subject_id: documentId, // placeholder — real flow fetches subject by name
        title: title.trim(),
        type: docType,
        professor: professor.trim() || undefined,
        semester: semester.trim(),
        file_path: filePath,
        file_size: file.size,
        mime_type: file.mimeType,
      });

      Alert.alert('✅ Publicado!', 'Seu documento foi enviado com sucesso. +10 pontos de reputação!');
      setFile(null);
      setTitle('');
      setSubjectName('');
      setProfessor('');
      setSemester('');
      setDocType('prova');
    } catch (err: any) {
      Alert.alert('Erro ao publicar', err.message ?? 'Tente novamente.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <ScrollView
      className="flex-1 bg-neutral-50 dark:bg-neutral-950"
      contentContainerClassName="px-4 pt-14 pb-10"
      keyboardShouldPersistTaps="handled"
    >
      <Text className="text-2xl font-bold text-neutral-900 dark:text-white mb-6">Enviar material</Text>

      {/* File picker */}
      <TouchableOpacity
        className={`rounded-xl border-2 border-dashed py-10 items-center justify-center mb-6 ${
          file ? 'border-primary-400 bg-primary-50' : 'border-neutral-300 dark:border-neutral-600'
        }`}
        onPress={pickFile}
        activeOpacity={0.7}
      >
        {file ? (
          <>
            <Ionicons name="document-text" size={40} color="#4F46E5" />
            <Text className="mt-2 text-primary-600 font-medium text-base">{file.name}</Text>
            <Text className="text-sm text-neutral-400 mt-1">{formatFileSize(file.size)}</Text>
            <Text className="text-xs text-neutral-400 mt-1 underline">Trocar arquivo</Text>
          </>
        ) : (
          <>
            <Ionicons name="cloud-upload-outline" size={40} color="#9CA3AF" />
            <Text className="mt-2 text-neutral-500 font-medium">Selecionar arquivo</Text>
            <Text className="text-xs text-neutral-400 mt-1">PDF, JPG ou PNG • máx. 20 MB</Text>
          </>
        )}
      </TouchableOpacity>

      {/* Type selector */}
      <Text className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">Tipo *</Text>
      <View className="flex-row flex-wrap gap-2 mb-4">
        {TYPE_OPTIONS.map((opt) => (
          <TouchableOpacity
            key={opt.value}
            className={`px-4 py-2 rounded-full border ${
              docType === opt.value
                ? 'bg-primary-600 border-primary-600'
                : 'bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
            }`}
            onPress={() => setDocType(opt.value)}
            testID={`type-${opt.value}`}
          >
            <Text className={`text-sm font-medium ${docType === opt.value ? 'text-white' : 'text-neutral-700 dark:text-neutral-300'}`}>
              {opt.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">Título *</Text>
      <TextInput
        className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl px-4 py-3 mb-4 text-base text-neutral-900 dark:text-white"
        placeholder="Ex: Prova 1 – Cálculo I"
        placeholderTextColor="#9CA3AF"
        value={title}
        onChangeText={setTitle}
      />

      <Text className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">Matéria *</Text>
      <TextInput
        className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl px-4 py-3 mb-4 text-base text-neutral-900 dark:text-white"
        placeholder="Ex: Cálculo I"
        placeholderTextColor="#9CA3AF"
        value={subjectName}
        onChangeText={setSubjectName}
        testID="input-subject"
      />

      <Text className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">Semestre *</Text>
      <TextInput
        className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl px-4 py-3 mb-4 text-base text-neutral-900 dark:text-white"
        placeholder="Ex: 2024.1"
        placeholderTextColor="#9CA3AF"
        value={semester}
        onChangeText={setSemester}
        testID="input-semester"
      />

      <Text className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">Professor (opcional)</Text>
      <TextInput
        className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl px-4 py-3 mb-8 text-base text-neutral-900 dark:text-white"
        placeholder="Ex: Prof. João Silva"
        placeholderTextColor="#9CA3AF"
        value={professor}
        onChangeText={setProfessor}
      />

      <TouchableOpacity
        className={`rounded-xl py-4 items-center ${
          file && title && subjectName && semester && !uploading
            ? 'bg-primary-600'
            : 'bg-neutral-300 dark:bg-neutral-700'
        }`}
        onPress={handleUpload}
        disabled={uploading || !file || !title || !subjectName || !semester}
      >
        {uploading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text className="text-white font-semibold text-base">Publicar</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}
