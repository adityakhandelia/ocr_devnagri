import type { SegmentType } from '../types';
import { getSegmentStyle, SEGMENT_STYLES } from '../lib/segmentStyles';

interface EntityFilterProps {
  selected: SegmentType[];
  onChange: (types: SegmentType[]) => void;
  counts: Record<string, number>;
}

export function EntityFilter({ selected, onChange, counts }: EntityFilterProps) {
  const types = Object.keys(SEGMENT_STYLES) as SegmentType[];

  const toggle = (type: SegmentType) => {
    if (selected.includes(type)) {
      onChange(selected.filter((t) => t !== type));
    } else {
      onChange([...selected, type]);
    }
  };

  const selectAll = () => {
    onChange([...types]);
  };

  const selectNone = () => {
    onChange([]);
  };

  return (
    <div className="bg-white border border-[#e5e0d8] rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-700">Filter by Entity Type</h3>
        <div className="flex gap-2 text-xs">
          <button
            onClick={selectAll}
            className="text-[#1a3a5c] hover:underline font-medium"
          >
            All
          </button>
          <span className="text-slate-300">|</span>
          <button
            onClick={selectNone}
            className="text-slate-500 hover:underline"
          >
            None
          </button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {types.map((type) => {
          const style = getSegmentStyle(type);
          const isSelected = selected.includes(type);
          const count = counts[type] || 0;

          return (
            <button
              key={type}
              onClick={() => toggle(type)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                isSelected ? 'ring-2 ring-offset-1' : 'opacity-60 hover:opacity-80'
              }`}
              style={{
                backgroundColor: style.bgColor,
                color: style.textColor,
                border: `1px solid ${style.borderColor}`,
                boxShadow: isSelected ? `0 0 0 2px ${style.color}` : undefined,
              }}
            >
              <span>{style.label}</span>
              <span
                className="ml-1 px-1.5 py-0.5 rounded-full text-[10px]"
                style={{ backgroundColor: 'rgba(0,0,0,0.08)' }}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
