import { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  FlatList,
} from 'react-native';
import { router } from 'expo-router';
import { supabase } from '@/services/supabase';
import { useAuthStore } from '@/stores/authStore';
import type { Institution, Course } from '@/types/app.types';

type Step = 'institution' | 'course' | 'semester';

const SEMESTERS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'];

export default function OnboardingScreen() {
  const { user } = useAuthStore();
  const [step, setStep] = useState<Step>('institution');
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedInstitution, setSelectedInstitution] = useState<Institution | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [selectedSemester, setSelectedSemester] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    supabase
      .from('institutions')
      .select('*')
      .order('name')
      .then(({ data }) => {
        setInstitutions(data ?? []);
        setLoading(false);
      });
  }, []);

  const handleSelectInstitution = async (inst: Institution) => {
    setSelectedInstitution(inst);
    setLoading(true);
    const { data } = await supabase
      .from('courses')
      .select('*')
      .eq('institution_id', inst.id)
      .order('name');
    setCourses(data ?? []);
    setLoading(false);
    setStep('course');
  };

  const handleSelectCourse = (course: Course) => {
    setSelectedCourse(course);
    setStep('semester');
  };

  const handleFinish = async () => {
    if (!selectedSemester || !user) return;
    setSaving(true);
    try {
      const { error } = await supabase.from('profiles').upsert({
        id: user.id,
        username: user.email!.split('@')[0],
        institution_id: selectedInstitution?.id ?? null,
        course_id: selectedCourse?.id ?? null,
        semester: parseInt(selectedSemester, 10),
      });
      if (error) throw error;
      router.replace('/(tabs)');
    } catch (err: any) {
      Alert.alert('Erro', err.message);
    } finally {
      setSaving(false);
    }
  };

  const renderHeader = () => (
    <View className="px-6 pt-16 pb-4">
      <Text className="text-2xl font-bold text-neutral-900 dark:text-white">
        {step === 'institution' && 'Qual é sua faculdade?'}
        {step === 'course' && 'Qual é seu curso?'}
        {step === 'semester' && 'Qual semestre você está?'}
      </Text>
      <Text className="text-neutral-500 mt-1">
        {step === 'institution' && 'Personalizamos o feed para você'}
        {step === 'course' && `${selectedInstitution?.acronym ?? selectedInstitution?.name}`}
        {step === 'semester' && `${selectedCourse?.name}`}
      </Text>
    </View>
  );

  if (loading) {
    return (
      <View className="flex-1 items-center justify-center bg-white dark:bg-neutral-950">
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  if (step === 'semester') {
    return (
      <View className="flex-1 bg-white dark:bg-neutral-950">
        {renderHeader()}
        <FlatList<Institution | Course>
          data={SEMESTERS}
          keyExtractor={(item) => item}
          contentContainerClassName="px-6 pb-10"
          renderItem={({ item }) => (
            <TouchableOpacity
              className={`border rounded-xl px-4 py-4 mb-3 ${
                selectedSemester === item
                  ? 'border-primary-600 bg-primary-50'
                  : 'border-neutral-200 dark:border-neutral-700'
              }`}
              onPress={() => setSelectedSemester(item)}
            >
              <Text className="text-base text-neutral-900 dark:text-white">
                {item}º semestre
              </Text>
            </TouchableOpacity>
          )}
          ListFooterComponent={
            <TouchableOpacity
              className={`rounded-xl py-4 items-center mt-4 ${
                selectedSemester ? 'bg-primary-600' : 'bg-neutral-300'
              }`}
              onPress={handleFinish}
              disabled={!selectedSemester || saving}
            >
              {saving ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text className="text-white font-semibold text-base">Continuar</Text>
              )}
            </TouchableOpacity>
          }
        />
      </View>
    );
  }

  const data: (Institution | Course)[] = step === 'institution' ? institutions : courses;

  return (
    <View className="flex-1 bg-white dark:bg-neutral-950">
      {renderHeader()}
      <FlatList<Institution | Course>
        data={data}
        keyExtractor={(item) => item.id}
        contentContainerClassName="px-6 pb-10"
        renderItem={({ item }) => (
          <TouchableOpacity
            className="border border-neutral-200 dark:border-neutral-700 rounded-xl px-4 py-4 mb-3"
            onPress={() =>
              step === 'institution'
                ? handleSelectInstitution(item as Institution)
                : handleSelectCourse(item as unknown as Course)
            }
          >
            <Text className="text-base font-medium text-neutral-900 dark:text-white">
              {step === 'institution'
                ? `${(item as Institution).acronym ? `[${(item as Institution).acronym}] ` : ''}${item.name}`
                : item.name}
            </Text>
            {step === 'institution' && (item as Institution).city && (
              <Text className="text-sm text-neutral-500 mt-0.5">
                {(item as Institution).city} — {(item as Institution).state}
              </Text>
            )}
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <Text className="text-center text-neutral-400 mt-10">
            {step === 'course' ? 'Nenhum curso cadastrado' : 'Nenhuma instituição encontrada'}
          </Text>
        }
      />
    </View>
  );
}
