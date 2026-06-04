import { useState, useCallback } from 'react';
import * as DocumentPicker from 'expo-document-picker';
import { useAuthStore } from '@/stores/authStore';
import { useReputation } from '@/hooks/useReputation';
import { uploadDocument } from '@/services/storage.service';
import { createDocument, getUploadCountToday } from '@/services/documents.service';
import { isValidFileSize, isValidMimeType, isValidSemester } from '@/utils/validators';
import type { DocumentType } from '@/types/app.types';

export interface UploadFormState {
  title: string;
  subjectId: string;
  type: DocumentType;
  professor: string;
  semester: string;
}

interface UploadFile {
  uri: string;
  name: string;
  size: number;
  mimeType: string;
}

interface UseUploadReturn {
  file: UploadFile | null;
  progress: 'idle' | 'picking' | 'uploading' | 'success' | 'error';
  error: string | null;
  pickFile: () => Promise<{ success: boolean; error?: string }>;
  upload: (form: UploadFormState) => Promise<{ success: boolean; error?: string }>;
  reset: () => void;
}

export const useUpload = (): UseUploadReturn => {
  const { user, profile } = useAuthStore();
  const reputation = useReputation(profile ?? { reputation: 0, plan: 'free' });
  const [file, setFile] = useState<UploadFile | null>(null);
  const [progress, setProgress] = useState<UseUploadReturn['progress']>('idle');
  const [error, setError] = useState<string | null>(null);

  const pickFile = useCallback(async () => {
    setProgress('picking');
    setError(null);
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'image/jpeg', 'image/png'],
        copyToCacheDirectory: true,
      });

      if (result.canceled) {
        setProgress('idle');
        return { success: false };
      }

      const asset = result.assets[0];

      if (!isValidMimeType(asset.mimeType ?? '')) {
        const msg = 'Apenas PDF, JPG e PNG são aceitos.';
        setError(msg);
        setProgress('error');
        return { success: false, error: msg };
      }

      if (!isValidFileSize(asset.size ?? 0)) {
        const msg = 'O arquivo deve ter no máximo 20 MB.';
        setError(msg);
        setProgress('error');
        return { success: false, error: msg };
      }

      setFile({
        uri: asset.uri,
        name: asset.name,
        size: asset.size ?? 0,
        mimeType: asset.mimeType ?? 'application/pdf',
      });
      setProgress('idle');
      return { success: true };
    } catch (err: any) {
      const msg = err.message ?? 'Erro ao selecionar arquivo.';
      setError(msg);
      setProgress('error');
      return { success: false, error: msg };
    }
  }, []);

  const upload = useCallback(
    async (form: UploadFormState) => {
      if (!file || !user) return { success: false, error: 'Arquivo ou usuário inválido.' };

      if (!isValidSemester(form.semester)) {
        return { success: false, error: 'Semestre inválido. Use o formato AAAA.N (ex: 2024.1)' };
      }

      const uploadedToday = await getUploadCountToday(user.id);
      if (!reputation.canUploadToday(uploadedToday)) {
        return {
          success: false,
          error: `Limite de ${reputation.dailyUploadLimit} uploads por dia atingido.`,
        };
      }

      setProgress('uploading');
      setError(null);
      try {
        const documentId = Math.random().toString(36).substring(2);
        const filePath = await uploadDocument(user.id, documentId, file.uri, file.mimeType);

        await createDocument({
          uploader_id: user.id,
          subject_id: form.subjectId,
          title: form.title.trim(),
          type: form.type,
          professor: form.professor.trim() || undefined,
          semester: form.semester.trim(),
          file_path: filePath,
          file_size: file.size,
          mime_type: file.mimeType,
        });

        setProgress('success');
        return { success: true };
      } catch (err: any) {
        const msg = err.message ?? 'Erro ao publicar documento.';
        setError(msg);
        setProgress('error');
        return { success: false, error: msg };
      }
    },
    [file, user, reputation]
  );

  const reset = useCallback(() => {
    setFile(null);
    setProgress('idle');
    setError(null);
  }, []);

  return { file, progress, error, pickFile, upload, reset };
};
