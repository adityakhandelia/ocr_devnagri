import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PageNavigationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function PageNavigation({ currentPage, totalPages, onPageChange }: PageNavigationProps) {
  return (
    <div className="flex items-center justify-between bg-white border border-[#e5e0d8] rounded-lg p-3">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        className="flex items-center gap-2 px-4 py-2 rounded-md bg-[#f5f1eb] hover:bg-[#e5e0d8] text-[#1a3a5c] disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
      >
        <ChevronLeft size={18} />
        <span>Previous Page</span>
      </button>

      <div className="flex flex-col items-center">
        <span className="text-xs uppercase tracking-wider text-slate-500">Page</span>
        <span className="text-lg font-semibold text-[#1a3a5c]">
          {currentPage} <span className="text-slate-400">/</span> {totalPages}
        </span>
      </div>

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className="flex items-center gap-2 px-4 py-2 rounded-md bg-[#1a3a5c] text-white hover:bg-[#0f2439] disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
      >
        <span>Next Page</span>
        <ChevronRight size={18} />
      </button>
    </div>
  );
}
