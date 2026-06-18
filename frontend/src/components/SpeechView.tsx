import { User, FileText } from 'lucide-react';
import type { Speech } from '../types';

interface SpeechViewProps {
  speeches: Speech[];
}

interface GroupedBlock {
  speaker: string | null;
  type: 'speech' | 'narrative' | 'heading';
  paragraphs: string[];
}

/**
 * Render inline markdown-style emphasis in Hindi text.
 * Supports **bold** and *italic* / *highlighted* markers.
 */
function InlineMarkdown({ text }: { text: string }) {
  if (!text) return null;

  // Split on **bold** first, then on *italic*
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

export function SpeechView({ speeches }: SpeechViewProps) {
  if (!speeches || speeches.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <FileText size={48} className="mx-auto mb-4 opacity-50" />
        <p>No content available for this page.</p>
      </div>
    );
  }

  // Group consecutive blocks by same speaker and same type
  const blocks: GroupedBlock[] = [];

  speeches.forEach((speech) => {
    const lastBlock = blocks[blocks.length - 1];

    if (
      lastBlock &&
      lastBlock.speaker === speech.speaker &&
      lastBlock.type === speech.type
    ) {
      lastBlock.paragraphs.push(speech.text);
    } else {
      blocks.push({
        speaker: speech.speaker,
        type: speech.type,
        paragraphs: [speech.text],
      });
    }
  });

  return (
    <div className="space-y-6">
      {blocks.map((block, index) => {
        // Headings: centered, bold, not italic
        if (block.type === 'heading') {
          return (
            <div key={index} className="text-center py-4">
              {block.paragraphs.map((para, i) => (
                <h2
                  key={i}
                  className="text-xl md:text-2xl font-bold text-slate-900 hindi-heading"
                >
                  <InlineMarkdown text={para} />
                </h2>
              ))}
            </div>
          );
        }

        // Narrative / stage directions
        if (block.type === 'narrative' || !block.speaker) {
          return (
            <div
              key={index}
              className="text-slate-700 hindi-text leading-relaxed"
            >
              {block.paragraphs.map((para, i) => {
                const isStageDirection =
                  para.startsWith('(') && para.endsWith(')');
                return (
                  <p
                    key={i}
                    className={`
                      ${i > 0 ? 'mt-3' : ''}
                      ${isStageDirection ? 'italic text-slate-600' : ''}
                    `}
                  >
                    <InlineMarkdown text={para} />
                  </p>
                );
              })}
            </div>
          );
        }

        // Speech block
        return (
          <article key={index} className="py-4">
            <div className="flex items-start gap-3 mb-3 pb-2 border-b border-slate-200">
              <div className="flex-shrink-0 w-9 h-9 rounded-full bg-slate-800 text-white flex items-center justify-center">
                <User size={18} />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-lg hindi-heading">
                  {block.speaker}
                </h3>
              </div>
            </div>

            <div className="hindi-text text-slate-800 space-y-4 leading-relaxed pl-12">
              {block.paragraphs.map((para, i) => (
                <p key={i}>
                  <InlineMarkdown text={para} />
                </p>
              ))}
            </div>
          </article>
        );
      })}
    </div>
  );
}
