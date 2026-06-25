import { useMemo, useRef, useState } from 'react';
import { Header } from './components/Header';
import { PageNavigation } from './components/PageNavigation';
import { Sidebar } from './components/Sidebar';
import { SegmentView } from './components/SegmentView';
import { StatsCards } from './components/StatsCards';
import { TopBar } from './components/TopBar';
import { EntityFilter } from './components/EntityFilter';
import { useDebateData } from './hooks/useDebateData';
import { Loader2, AlertCircle, SlidersHorizontal, BookOpen } from 'lucide-react';
import type { SegmentType } from './types';

const ALL_SEGMENT_TYPES: SegmentType[] = [
  'metadata',
  'heading',
  'announcement',
  'speech',
  'member_list',
  'narrative',
];

function App() {
  const { data, loading, error } = useDebateData();
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedTypes, setSelectedTypes] = useState<SegmentType[]>(ALL_SEGMENT_TYPES);
  const [showFilters, setShowFilters] = useState(false);
  const transcriptRef = useRef<HTMLDivElement>(null);

  const scrollToTranscript = () => {
    transcriptRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const currentPageData = data?.pages.find((p) => p.page_number === currentPage);

  const filteredSegments = useMemo(() => {
    if (!currentPageData) return [];
    return currentPageData.segments.filter((seg) => selectedTypes.includes(seg.type));
  }, [currentPageData, selectedTypes]);

  const pageCounts = useMemo(() => {
    if (!currentPageData) return {};
    const counts: Record<string, number> = {};
    currentPageData.segments.forEach((seg) => {
      counts[seg.type] = (counts[seg.type] || 0) + 1;
    });
    return counts;
  }, [currentPageData]);

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

  return (
    <div className="flex min-h-screen bg-[#f5f1eb]">
      <Sidebar />

      <div className="flex-1 flex flex-col min-h-screen overflow-auto">
        <TopBar />

        <main className="flex-1">
          <Header data={data} onReadTranscript={scrollToTranscript} />

          <div className="max-w-6xl mx-auto px-6 py-8">
            <StatsCards data={data} />

            {/* Session Transcript heading */}
            <div ref={transcriptRef} className="mt-10 mb-6 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
              <div>
                <h2 className="text-2xl font-serif font-bold text-[#1a3a5c]">Session Transcript</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Showing page {currentPage} of {data.total_pages}
                  {currentPageData && (
                    <span className="ml-2">
                      · {currentPageData.page_type.replace('_', ' ')}
                      · {currentPageData.total_words.toLocaleString()} words
                    </span>
                  )}
                </p>
              </div>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-[#e5e0d8] text-slate-600 text-sm rounded hover:bg-[#ebe6de] transition-colors"
              >
                <SlidersHorizontal size={16} />
                {showFilters ? 'Hide Filters' : 'Entity Filters'}
              </button>
            </div>

            {showFilters && (
              <div className="mb-6">
                <EntityFilter
                  selected={selectedTypes}
                  onChange={setSelectedTypes}
                  counts={pageCounts}
                />
              </div>
            )}

            <PageNavigation
              currentPage={currentPage}
              totalPages={data.total_pages}
              onPageChange={setCurrentPage}
            />

            {currentPageData && (
              <div className="mt-6 bg-white border border-[#e5e0d8] rounded-lg p-6 md:p-10 shadow-sm">
                {filteredSegments.length === 0 ? (
                  <div className="text-center py-12 text-slate-500">
                    <BookOpen size={48} className="mx-auto mb-4 opacity-50" />
                    <p>No segments match the selected filters.</p>
                    <button
                      onClick={() => setSelectedTypes(ALL_SEGMENT_TYPES)}
                      className="mt-3 text-[#1a3a5c] hover:underline text-sm"
                    >
                      Show all entities
                    </button>
                  </div>
                ) : (
                  <SegmentView segments={filteredSegments} />
                )}
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
