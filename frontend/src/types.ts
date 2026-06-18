export interface Speech {
  speaker: string | null;
  text: string;
  type: 'speech' | 'narrative' | 'heading';
}

export interface Page {
  page_number: number;
  image: string;
  speeches: Speech[];
}

export interface DebateData {
  pdf_name: string;
  date: string;
  session_title: string;
  total_pages: number;
  speakers: string[];
  pages: Page[];
}
