import { User, FileText, Info, Users, ScrollText } from 'lucide-react';
import type { Segment } from '../types';

interface SpeechViewProps {
  segments: Segment[];
}

/**
 * Render inline markdown-style emphasis in Hindi text.
 * Supports **bold** and *italic* / *highlighted* markers.
 */
function InlineMarkdown({ text }: { text: string }) {
  if (!text) return null;

  const boldParts = text.split(/(\*\*.*?\*\*)/g);

  return (
    <>
      {boldParts.map((part, idx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          const inner = part.slice(2, -2);
          return (
            <strong key={idx} className="font-bold text-slate-900 bg-amber-100 px-1 rounded">
              {inner}
            </strong>
          );
        }

        const italicParts = part.split(/(\*[^*]+\*)/g);
        return italicParts.map((subPart, subIdx) => {
          const key = `${idx}-${subIdx}`;
          if (subPart.startsWith('*') && subPart.endsWith('*')) {
            const inner = subPart.slice(1, -1);
            return (
              <em key={key} className="not-italic font-semibold text-slate-900 bg-amber-50 px-1 rounded border-b-2 border-amber-300">
                {inner}
              </em>
            );
          }
          return <span key={key}>{subPart}</span>;
        });
      })}
    </>
  );
}

export function SpeechView({ segments }: SpeechViewProps) {
  if (!segments || segments.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <FileText size={48} className="mx-auto mb-4 opacity-50" />
        <p>No content available for this page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {segments.map((segment, index) => {
        const key = `${segment.type}-${segment.start_index}-${index}`;

        // Metadata: page header/footer info
        if (segment.type === 'metadata') {
          return (
            <div key={key} className="flex items-start gap-2 text-xs text-slate-500 border-b border-slate-100 pb-2">
              <Info size={14} className="mt-0.5 flex-shrink-0" />
              <span className="hindi-text"><InlineMarkdown text={segment.text} /></span>
            </div>
          );
        }

        // Headings: centered, bold
        if (segment.type === 'heading') {
          return (
            <div key={key} className="text-center py-4">
              <h2 className="text-xl md:text-2xl font-bold text-slate-900 hindi-heading">
                <InlineMarkdown text={segment.text} />
              </h2>
            </div>
          );
        }

        // Announcements: chair/clerk/bill notices
        if (segment.type === 'announcement') {
          return (
            <div key={key} className="bg-amber-50 border-l-4 border-amber-400 p-4 my-4">
              <div className="flex items-center gap-2 text-amber-800 text-sm font-semibold mb-1">
                <ScrollText size={16} />
                <span className="uppercase tracking-wide">
                  {segment.subtype || 'Announcement'}
                </span>
              </div>
              <p className="text-slate-800 hindi-text leading-relaxed">
                <InlineMarkdown text={segment.text} />
              </p>
            </div>
          );
        }

        // Member lists
        if (segment.type === 'member_list') {
          return (
            <div key={key} className="bg-slate-50 border border-slate-200 rounded p-4 my-4">
              <div className="flex items-center gap-2 text-slate-600 text-sm font-semibold mb-2">
                <Users size={16} />
                <span>Members</span>
              </div>
              <p className="text-slate-800 hindi-text leading-relaxed">
                <InlineMarkdown text={segment.text} />
              </p>
            </div>
          );
        }

        // Narrative / stage directions
        if (segment.type === 'narrative') {
          const isStageDirection = segment.text.startsWith('(') && segment.text.endsWith(')');
          return (
            <p
              key={key}
              className={`text-slate-700 hindi-text leading-relaxed ${isStageDirection ? 'italic text-slate-600' : ''}`}
            >
              <InlineMarkdown text={segment.text} />
            </p>
          );
        }

        // Speech block
        return (
          <article key={key} className="py-4 border-b border-slate-100 last:border-b-0">
            <div className="flex items-start gap-3 mb-3 pb-2 border-b border-slate-200">
              <div className="flex-shrink-0 w-9 h-9 rounded-full bg-slate-800 text-white flex items-center justify-center">
                <User size={18} />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-lg hindi-heading">
                  {segment.speaker || 'Unknown Speaker'}
                </h3>
              </div>
            </div>

            <div className="hindi-text text-slate-800 leading-relaxed pl-12">
              <p><InlineMarkdown text={segment.text} /></p>
            </div>
          </article>
        );
      })}
    </div>
  );
}
