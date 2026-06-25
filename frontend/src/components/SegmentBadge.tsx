import { Info, Heading1, Megaphone, MessageSquare, Users, BookOpen } from 'lucide-react';
import type { SegmentType } from '../types';
import { getSegmentStyle } from '../lib/segmentStyles';

interface SegmentBadgeProps {
  type: SegmentType;
  subtype?: string | null;
  size?: 'sm' | 'md';
}

const ICONS: Record<string, React.ComponentType<{ size?: number }>> = {
  Info,
  Heading: Heading1,
  Megaphone,
  MessageSquare,
  Users,
  BookOpen,
};

export function SegmentBadge({ type, subtype, size = 'md' }: SegmentBadgeProps) {
  const style = getSegmentStyle(type);
  const Icon = ICONS[style.icon];
  const padding = size === 'sm' ? 'px-2 py-0.5' : 'px-2.5 py-1';
  const textSize = size === 'sm' ? 'text-[10px]' : 'text-xs';
  const iconSize = size === 'sm' ? 10 : 12;

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium uppercase tracking-wider ${padding} ${textSize}`}
      style={{
        backgroundColor: style.bgColor,
        color: style.textColor,
        border: `1px solid ${style.borderColor}`,
      }}
    >
      {Icon && <Icon size={iconSize} />}
      <span>{subtype || style.label}</span>
    </span>
  );
}
