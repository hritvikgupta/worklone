import React from 'react';
import { SkillLibrary } from '@/src/components/SkillLibrary';

export function SkillLibraryPage() {
  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="w-full animate-in slide-in-from-bottom-4 duration-300">
        <SkillLibrary />
      </div>
    </div>
  );
}
