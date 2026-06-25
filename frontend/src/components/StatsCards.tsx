import { BookOpen, Users, Activity, MessageSquare } from 'lucide-react';
import type { DebateData } from '../types';

interface StatsCardsProps {
  data: DebateData;
}

function StatCard({
  icon,
  value,
  label,
  sublabel,
  accent,
}: {
  icon: React.ReactNode;
  value: string | number;
  label: string;
  sublabel: string;
  accent: string;
}) {
  return (
    <div className="bg-white border border-[#e5e0d8] p-5 flex items-start gap-4 hover:shadow-sm transition-shadow">
      <div className="mt-1" style={{ color: accent }}>{icon}</div>
      <div>
        <div className="text-3xl font-serif font-bold text-[#1a3a5c]">{value}</div>
        <div className="text-sm font-medium text-slate-700">{label}</div>
        <div className="text-xs text-slate-500 mt-1">{sublabel}</div>
      </div>
    </div>
  );
}

export function StatsCards({ data }: StatsCardsProps) {
  const totalSpeeches = data.segment_counts?.speech || 0;
  const totalHeadings = data.segment_counts?.heading || 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-[#e5e0d8] border border-[#e5e0d8]">
      <StatCard
        icon={<BookOpen size={24} />}
        value={data.total_pages}
        label="Pages Transcribed"
        sublabel={`${data.total_words?.toLocaleString() || 0} total words`}
        accent="#1a3a5c"
      />
      <StatCard
        icon={<Users size={24} />}
        value={data.speakers.length}
        label="Speakers on Record"
        sublabel="Active in this session"
        accent="#3730a3"
      />
      <StatCard
        icon={<MessageSquare size={24} />}
        value={totalSpeeches}
        label="Speeches Captured"
        sublabel={`${totalHeadings} headings / sections`}
        accent="#14532d"
      />
      <StatCard
        icon={<Activity size={24} />}
        value={`${Math.round((data.total_pages / 88) * 100)}%`}
        label="Volume Complete"
        sublabel="Of full PDF archive"
        accent="#7c2d12"
      />
    </div>
  );
}
