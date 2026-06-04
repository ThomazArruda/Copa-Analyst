import { useQuery } from '@tanstack/react-query';
import * as documentsService from '@/services/documents.service';
import type { DocumentFilter } from '@/types/app.types';

export const useDocumentSearch = (filter: DocumentFilter) => {
  return useQuery({
    queryKey: ['documents', 'search', filter],
    queryFn: () => documentsService.getDocumentsByFilter(filter),
    enabled: !!(filter.query || filter.subjectId || filter.type || filter.institutionId),
  });
};

export const useDocument = (id: string) => {
  return useQuery({
    queryKey: ['documents', id],
    queryFn: () => documentsService.getDocumentById(id),
    enabled: !!id,
  });
};

export const useRecentDocuments = (institutionId?: string) => {
  return useQuery({
    queryKey: ['documents', 'recent', institutionId],
    queryFn: () => documentsService.getRecentDocuments(institutionId),
  });
};

export const usePopularDocuments = () => {
  return useQuery({
    queryKey: ['documents', 'popular'],
    queryFn: () => documentsService.getPopularDocuments(),
  });
};
