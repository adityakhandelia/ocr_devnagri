import { useRef, useState } from 'react';
import { Header } from './components/Header';
import { PageNavigation } from './components/PageNavigation';
import { Sidebar } from './components/Sidebar';
import { SpeechView } from './components/SpeechView';
import { StatsCards } from './components/StatsCards';
import { TopBar } from './components/TopBar';
import { useDebateData } from './hooks/useDebateData';
import { Loader2, AlertCircle, SlidersHorizontal } from 'lucide-react';

function App() {
  const { data, loading, error } = useDebateData();
  const [currentPage, setCurrentPage] = useState(1);
  const transcriptRef = useRef<HTMLDivElement>(null);

  const scrollToTranscript = () => {
    transcriptRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f5f1eb]">
        <div className="flex flex-col items-center gap-4 text-slate-600">
          <Loader2 size={40} className="animate-spin" />
          <p>Loading parliamentary debate...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f5f1eb]">
        <div className="flex flex-col items-center gap-4 text-red-600">
          <AlertCircle size={40} />
          <p>{error || 'Failed to load debate data'}</p>
        </div>
      </div>
    );
  }

  const currentPageData = data.pages.find((p) => p.page_number === currentPage);

  return (
    <div className="flex min-h-screen bg-[#f5f1eb]">
      <Sidebar />

      <div className="flex-1 flex flex-col min-h-screen overflow-auto">
        <TopBar />

        <main className="flex-1">
          <Header data={data} onReadTranscript={scrollToTranscript} />

          <div className="max-w-6xl mx-auto px-6 py-8">
            <StatsCards data={data} />

            {/* Recent Proceedings heading */}
            <div ref={transcriptRef} className="mt-10 mb-6 flex items-end justify-between">
              <div>
                <h2 className="text-2xl font-serif font-bold text-[#1a3a5c]">Session Transcript</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Showing page {currentPage} of {data.total_pages}
                </p>
              </div>
              <button className="hidden sm:flex items-center gap-2 px-4 py-2 bg-white border border-[#e5e0d8] text-slate-600 text-sm rounded hover:bg-[#ebe6de] transition-colors">
                <SlidersHorizontal size={16} />
                Advanced Filter
              </button>
            </div>

            <PageNavigation
              currentPage={currentPage}
              totalPages={data.total_pages}
              onPageChange={setCurrentPage}
            />

            {currentPageData && (
              <div className="mt-6 bg-white border border-[#e5e0d8] rounded-lg p-6 md:p-10 shadow-sm">
                <SpeechView speeches={currentPageData.speeches} />
              </div>
            )}

            <div className="mt-6">
              <PageNavigation
                currentPage={currentPage}
                totalPages={data.total_pages}
                onPageChange={setCurrentPage}
              />
            </div>
          </div>
        </main>

        <footer className="bg-white border-t border-[#e5e0d8] mt-16">
          <div className="max-w-6xl mx-auto px-6 py-6 text-center text-slate-500 text-sm">
            <p className="font-medium text-[#1a3a5c] hindi-heading">देवनागरी विधान सभा चर्चा संग्रह</p>
            <p className="mt-1">Digitized from historical legislative records</p>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;
