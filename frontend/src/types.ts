export type SegmentType =
  | 'metadata'
  | 'heading'
  | 'announcement'
  | 'speech'
  | 'member_list'
  | 'narrative';

export interface MemberEntry {
  name: string;
  honorific: string;
}

export interface Segment {
  type: SegmentType;
  start_index: number;
  end_index: number;
  text: string;
  subtype?: string | null;
  speaker?: string | null;
  speaker_range?: [number, number];
  members?: MemberEntry[];
}

export interface Page {
  page_number: number;
  image: string;
  thumbnail: string;
  page_type: string;
  total_words: number;
  segment_stats: Record<string, number>;
  segments: Segment[];
}

export interface DebateData {
  pdf_name: string;
  date: string;
  session_title: string;
  total_pages: number;
  total_words: number;
  speakers: string[];
  segment_counts: Record<string, number>;
  pages: Page[];
}
