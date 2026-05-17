'use client';

import { useQuery } from '@tanstack/react-query';
import { getCreators, getVideos, getJobs, getQueueStatus } from '@/lib/api';
import { Users, Video, Scissors, Clock } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  sub?: string;
}

function StatCard({ label, value, icon, sub }: StatCardProps) {
  return (
    <div className="card p-6 flex items-start gap-4">
      <div className="p-3 bg-brand-50 rounded-lg text-brand-600">{icon}</div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: creatorsData } = useQuery({
    queryKey: ['creators'],
    queryFn: () => getCreators().then((r) => r.data),
  });

  const { data: videosData } = useQuery({
    queryKey: ['videos'],
    queryFn: () => getVideos().then((r) => r.data),
  });

  const { data: jobsData } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => getJobs().then((r) => r.data),
  });

  const { data: queueData } = useQuery({
    queryKey: ['queue-status'],
    queryFn: () => getQueueStatus().then((r) => r.data),
    refetchInterval: 15_000,
  });

  const creators = creatorsData?.items ?? creatorsData ?? [];
  const videos = videosData?.items ?? videosData ?? [];
  const jobs = jobsData ?? [];
  const queuedJobs =
    (queueData?.queued_jobs?.ingestion ?? 0) +
    (queueData?.queued_jobs?.transcription ?? 0) +
    (queueData?.queued_jobs?.rendering ?? 0) +
    (queueData?.queued_jobs?.publishing ?? 0);

  const today = new Date().toISOString().slice(0, 10);
  const videosToday = videos.filter(
    (v: any) => v.created_at?.slice(0, 10) === today
  ).length;

  const publishedJobs = jobs.filter((j: any) => j.status === 'published').length;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Creators"
          value={creators.length}
          icon={<Users size={20} />}
          sub="active monitored creators"
        />
        <StatCard
          label="Videos Ingested Today"
          value={videosToday}
          icon={<Video size={20} />}
          sub={`${videos.length} total videos`}
        />
        <StatCard
          label="Published Clips"
          value={publishedJobs}
          icon={<Scissors size={20} />}
          sub={`${jobs.length} total jobs`}
        />
        <StatCard
          label="Jobs in Queue"
          value={queuedJobs}
          icon={<Clock size={20} />}
          sub="across all queues"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Queue Depths
          </h2>
          {queueData ? (
            <dl className="space-y-2">
              {Object.entries(queueData.queued_jobs ?? {}).map(
                ([queue, count]) => (
                  <div
                    key={queue}
                    className="flex justify-between text-sm"
                  >
                    <dt className="text-gray-500 capitalize">{queue}</dt>
                    <dd className="font-medium text-gray-900">
                      {count as number}
                    </dd>
                  </div>
                )
              )}
            </dl>
          ) : (
            <p className="text-sm text-gray-400">Loading queue data...</p>
          )}
        </div>

        <div className="card p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            Recent Publishing Jobs
          </h2>
          {jobs.length === 0 ? (
            <p className="text-sm text-gray-400">No jobs yet.</p>
          ) : (
            <ul className="space-y-2">
              {jobs.slice(0, 5).map((job: any) => (
                <li
                  key={job.id}
                  className="flex justify-between text-sm"
                >
                  <span className="text-gray-600 font-mono text-xs truncate max-w-[160px]">
                    {job.id}
                  </span>
                  <span
                    className={`text-xs font-medium ${
                      job.status === 'published'
                        ? 'text-green-600'
                        : job.status === 'failed'
                        ? 'text-red-500'
                        : 'text-gray-500'
                    }`}
                  >
                    {job.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
