import { BookOpen, Users, FileText, Activity } from 'lucide-react';
import type { DebateData } from '../types';

interface StatsCardsProps {
  data: DebateData;
}

function StatCard({
  icon,
  value,
  label,
  sublabel,
}: {
  icon: React.ReactNode;
  value: string | number;
  label: string;
  sublabel: string;
}) {
  return (
    <div className="bg-white border border-[#e5e0d8] p-6 flex items-start gap-4">
      <div className="text-slate-400 mt-1">{icon}</div>
      <div>
        <div className="text-3xl font-serif font-bold text-[#1a3a5c]">{value}</div>
        <div className="text-sm font-medium text-slate-700">{label}</div>
        <div className="text-xs text-slate-500 mt-1">{sublabel}</div>
      </div>
    </div>
  );
}

export function StatsCards({ data }: StatsCardsProps) {
  // Count total speeches (non-narrative blocks)
  const totalSpeeches = data.pages.reduce(
    (acc, page) => acc + page.speeches.filter((s) => s.type === 'speech').length,
    0
  );

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-[#e5e0d8] border border-[#e5e0d8]">
      <StatCard
        icon={<BookOpen size={24} />}
        value={data.total_pages}
        label="Pages Transcribed"
        sublabel="From scanned PDF"
      />
      <StatCard
        icon={<Users size={24} />}
        value={data.speakers.length}
        label="Speakers on Record"
        sublabel="Active in this session"
      />
      <StatCard
        icon={<FileText size={24} />}
        value={totalSpeeches}
        label="Speeches Captured"
        sublabel="Questions and debates"
      />
      <StatCard
        icon={<Activity size={24} />}
        value={`${Math.round((data.total_pages / 88) * 100)}%`}
        label="Volume Complete"
        sublabel="Of full PDF archive"
      />
    </div>
  );
}
