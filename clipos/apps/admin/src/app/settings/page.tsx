'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSettings, updateSetting } from '@/lib/api';
import { useState } from 'react';
import { Save } from 'lucide-react';

export default function SettingsPage() {
  const qc = useQueryClient();
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});

  const { data, isLoading, error } = useQuery({
    queryKey: ['settings'],
    queryFn: () => getSettings().then((r) => r.data),
  });

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: any }) =>
      updateSetting(key, value),
    onSuccess: (_data, { key }) => {
      setSaved((s) => ({ ...s, [key]: true }));
      setTimeout(() => setSaved((s) => ({ ...s, [key]: false })), 2000);
      qc.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const settings = data?.items ?? data ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        System Settings
      </h1>

      {isLoading ? (
        <p className="text-sm text-gray-400">Loading settings...</p>
      ) : error ? (
        <p className="text-sm text-red-500">Failed to load settings.</p>
      ) : settings.length === 0 ? (
        <div className="card p-8 text-center text-gray-400">
          <p>No settings configured yet.</p>
          <p className="text-xs mt-1">
            Settings are seeded via the seed script or API.
          </p>
        </div>
      ) : (
        <div className="card divide-y divide-gray-100">
          {settings.map((s: any) => {
            const currentVal =
              edits[s.key] ??
              (typeof s.value === 'object'
                ? JSON.stringify(s.value, null, 2)
                : String(s.value ?? ''));

            return (
              <div key={s.id ?? s.key} className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-800 mb-1">
                      {s.key}
                    </label>
                    {s.description && (
                      <p className="text-xs text-gray-500 mb-2">
                        {s.description}
                      </p>
                    )}
                    <textarea
                      className="w-full text-sm font-mono border border-gray-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                      rows={3}
                      value={currentVal}
                      onChange={(e) =>
                        setEdits((prev) => ({ ...prev, [s.key]: e.target.value }))
                      }
                    />
                  </div>
                  <div className="flex flex-col items-end gap-2 pt-6">
                    <button
                      onClick={() => {
                        let parsed: any = edits[s.key];
                        try {
                          parsed = JSON.parse(edits[s.key] ?? currentVal);
                        } catch {
                          parsed = edits[s.key] ?? currentVal;
                        }
                        updateMutation.mutate({ key: s.key, value: parsed });
                      }}
                      disabled={
                        updateMutation.isPending ||
                        edits[s.key] === undefined ||
                        edits[s.key] === currentVal
                      }
                      className="btn-primary"
                    >
                      <Save size={14} />
                      {saved[s.key] ? 'Saved!' : 'Save'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
