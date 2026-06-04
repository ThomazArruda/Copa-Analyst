import * as FileSystem from 'expo-file-system';
import { supabase } from '@/services/supabase';
import { decode } from 'base64-arraybuffer';

const DOCUMENTS_BUCKET = 'documents';
const AVATARS_BUCKET = 'avatars';

export const uploadDocument = async (
  userId: string,
  documentId: string,
  fileUri: string,
  mimeType: string
): Promise<string> => {
  const filePath = `${userId}/${documentId}`;
  const base64 = await FileSystem.readAsStringAsync(fileUri, {
    encoding: 'base64',
  });
  const arrayBuffer = decode(base64);

  const { error } = await supabase.storage
    .from(DOCUMENTS_BUCKET)
    .upload(filePath, arrayBuffer, { contentType: mimeType, upsert: false });

  if (error) throw error;
  return filePath;
};

export const getDocumentSignedUrl = async (filePath: string): Promise<string> => {
  const { data, error } = await supabase.storage
    .from(DOCUMENTS_BUCKET)
    .createSignedUrl(filePath, 3600); // 1 hour
  if (error) throw error;
  return data.signedUrl;
};

export const uploadAvatar = async (
  userId: string,
  fileUri: string,
  mimeType: string
): Promise<string> => {
  const ext = mimeType === 'image/png' ? 'png' : 'jpg';
  const filePath = `${userId}/avatar.${ext}`;
  const base64 = await FileSystem.readAsStringAsync(fileUri, {
    encoding: 'base64',
  });
  const arrayBuffer = decode(base64);

  const { error } = await supabase.storage
    .from(AVATARS_BUCKET)
    .upload(filePath, arrayBuffer, { contentType: mimeType, upsert: true });

  if (error) throw error;

  const { data } = supabase.storage.from(AVATARS_BUCKET).getPublicUrl(filePath);
  return data.publicUrl;
};
