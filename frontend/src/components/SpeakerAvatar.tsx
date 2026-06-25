import { User } from 'lucide-react';

interface SpeakerAvatarProps {
  name: string;
  size?: 'sm' | 'md' | 'lg';
}

function getInitials(name: string): string {
  // For Hindi/Unicode names, take the first character or first two characters
  const clean = name.replace(/^(श्री\s+|श्रीमती\s+|माननीय\s+|डा०\s+|प्रो०\s+|स्व०\s+)/, '');
  if (!clean) return '?';
  // Try to get first meaningful character
  const parts = clean.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return clean.slice(0, 2).toUpperCase();
}

function stringToColor(str: string): string {
  const colors = [
    '#1e3a5f',
    '#3730a3',
    '#7c2d12',
    '#14532d',
    '#701a75',
    '#164e63',
    '#881337',
    '#1e40af',
  ];
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

export function SpeakerAvatar({ name, size = 'md' }: SpeakerAvatarProps) {
  const initials = getInitials(name);
  const bgColor = stringToColor(name);

  const dimensions = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-14 h-14 text-base',
  };

  return (
    <div
      className={`${dimensions[size]} rounded-full flex items-center justify-center font-bold text-white shadow-sm flex-shrink-0`}
      style={{ backgroundColor: bgColor }}
      title={name}
    >
      {initials === '?' ? <User size={size === 'lg' ? 24 : 16} /> : initials}
    </div>
  );
}
