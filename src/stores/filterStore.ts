import { create } from 'zustand';
import type { DocumentFilter } from '@/types/app.types';

interface FilterState extends DocumentFilter {
  setFilter: (filter: Partial<DocumentFilter>) => void;
  clearFilters: () => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  institutionId: undefined,
  courseId: undefined,
  subjectId: undefined,
  type: undefined,
  semester: undefined,
  query: undefined,
  setFilter: (filter) => set((state) => ({ ...state, ...filter })),
  clearFilters: () =>
    set({
      institutionId: undefined,
      courseId: undefined,
      subjectId: undefined,
      type: undefined,
      semester: undefined,
      query: undefined,
    }),
}));
