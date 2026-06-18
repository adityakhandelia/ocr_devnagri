import { BookOpen, Calendar, Users, ArrowRight } from 'lucide-react';
import type { DebateData } from '../types';

interface HeaderProps {
  data: DebateData;
  onReadTranscript?: () => void;
}

export function Header({ data, onReadTranscript }: HeaderProps) {
  return (
    <div className="relative bg-gradient-to-br from-[#1a3a5c] to-[#0f2439] text-white overflow-hidden">
      {/* Decorative pattern overlay */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(circle at 2px 2px, white 1px, transparent 0)`,
          backgroundSize: '32px 32px'
        }} />
      </div>

      <div className="relative max-w-6xl mx-auto px-6 py-12">
        {/* Breadcrumb labels */}
        <div className="flex items-center gap-4 text-xs uppercase tracking-widest text-[#c9a23f] mb-6">
          <span>Featured Session</span>
          <span className="text-white/30">————</span>
          <span>House · Legislative Assembly</span>
        </div>

        <h1 className="text-3xl md:text-5xl font-serif font-bold hindi-heading mb-6 max-w-3xl leading-tight">
          {data.session_title}
        </h1>

        <p className="text-slate-300 text-lg max-w-2xl mb-8 leading-relaxed">
          Official proceedings of the Uttar Pradesh Legislative Assembly from {data.date}.
          This volume contains {data.total_pages} pages of recorded debates, questions, and legislative business.
        </p>

        <div className="flex flex-wrap items-center gap-8 mb-8">
          <div className="flex items-center gap-2 text-slate-200">
            <Calendar size={18} />
            <span>{data.date}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-200">
            <Users size={18} />
            <span>{data.speakers.length} Speakers</span>
          </div>
          <div className="flex items-center gap-2 text-slate-200">
            <BookOpen size={18} />
            <span>{data.total_pages} Pages</span>
          </div>
          <div className="text-slate-400 text-sm">
            Ref: {data.pdf_name}
          </div>
        </div>

        {onReadTranscript && (
          <button
            onClick={onReadTranscript}
            className="inline-flex items-center gap-2 bg-[#b91c3a] hover:bg-[#9c1830] text-white px-6 py-3 rounded font-medium transition-colors"
          >
            Read Full Transcript
            <ArrowRight size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
