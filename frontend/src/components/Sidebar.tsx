import { LayoutDashboard, Star, BookOpen, Users, FileText, Gavel, Menu, Archive } from 'lucide-react';

interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  count?: number;
}

function NavItem({ icon, label, active, count }: NavItemProps) {
  return (
    <a
      href="#"
      className={`
        flex items-center justify-between px-4 py-3 rounded-lg text-sm font-medium transition-colors
        ${active
          ? 'bg-[#b91c3a] text-white'
          : 'text-slate-300 hover:bg-white/10 hover:text-white'
        }
      `}
    >
      <div className="flex items-center gap-3">
        {icon}
        <span>{label}</span>
      </div>
      {count !== undefined && (
        <span className={`text-xs ${active ? 'text-white/80' : 'text-slate-400'}`}>
          {count}
        </span>
      )}
    </a>
  );
}

export function Sidebar() {
  return (
    <aside className="w-64 bg-[#1a3a5c] text-white flex flex-col h-screen sticky top-0 overflow-y-auto">
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[#c9a23f] rounded flex items-center justify-center">
            <Menu size={20} className="text-[#1a3a5c]" />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-widest text-slate-300">भारतीय</div>
            <div className="text-lg font-bold leading-tight hindi-heading">विधान सभा चर्चा</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-6">
        <div>
          <div className="px-4 text-[10px] uppercase tracking-widest text-slate-400 mb-2">Overview</div>
          <div className="space-y-1">
            <NavItem icon={<LayoutDashboard size={18} />} label="Dashboard" active />
            <NavItem icon={<Star size={18} />} label="Featured Sessions" />
          </div>
        </div>

        <div>
          <div className="px-4 text-[10px] uppercase tracking-widest text-slate-400 mb-2">Browse</div>
          <div className="space-y-1">
            <NavItem icon={<BookOpen size={18} />} label="All Transcripts" />
            <NavItem icon={<Users size={18} />} label="Members" count={12} />
            <NavItem icon={<FileText size={18} />} label="Bills & Legislation" />
            <NavItem icon={<Gavel size={18} />} label="Committees" />
          </div>
        </div>

        <div>
          <div className="px-4 text-[10px] uppercase tracking-widest text-slate-400 mb-2">Filter by Chamber</div>
          <div className="space-y-1">
            <NavItem icon={<Archive size={18} />} label="All Chambers" count={1} />
            <NavItem icon={<span className="w-2 h-2 rounded-full bg-emerald-400" />} label="House Chamber" count={1} />
          </div>
        </div>
      </nav>

      {/* User */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-slate-600 flex items-center justify-center">
            <Users size={18} />
          </div>
          <div>
            <div className="text-sm font-medium">Researcher</div>
            <div className="text-xs text-slate-400">Uttar Pradesh Assembly</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
