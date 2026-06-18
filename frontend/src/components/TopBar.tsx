import { Search, Bell, Calendar } from 'lucide-react';

export function TopBar() {
  return (
    <header className="h-16 bg-[#f5f1eb] border-b border-[#e5e0d8] flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Search transcripts, members, speeches..."
            className="w-full pl-10 pr-4 py-2 bg-white border border-[#ddd8cf] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]/20"
          />
        </div>
      </div>

      <div className="flex items-center gap-6 ml-6">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <Calendar size={16} />
          <span>7 March 1952</span>
        </div>
        <button className="relative p-2 text-slate-600 hover:bg-[#e5e0d8] rounded-lg transition-colors">
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
        </button>
      </div>
    </header>
  );
}
