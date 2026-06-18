import { useState, useEffect } from 'react';
import type { DebateData } from '../types';

export function useDebateData() {
  const [data, setData] = useState<DebateData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
// test
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/debates.json`)
      .then((res) => {
        if (!res.ok) {
          throw new Error('Failed to load debate data');
        }
        return res.json();
      })
      .then((data: DebateData) => {
        setData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return { data, loading, error };
}
