import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api/client";
import type { SuggestItem } from "./types";

type LookupResult = { exists: boolean; acclib?: string };

export function useAccountSuggest(clientId?: number | string) {
  const [itemsByUid, setItems] = useState<Record<string, SuggestItem[]>>({});
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const clear = useCallback((uid: string) => {
    setItems((s) => ({ ...s, [uid]: [] }));
  }, []);

  const onChange = useCallback(
    (uid: string, value: string, onLookup: (res: LookupResult) => void) => {
      const t = timers.current[uid];
      if (t) clearTimeout(t);

      timers.current[uid] = setTimeout(async () => {
        if (!clientId) return;

        // 1) Suggest pour dropdown
        if (value && value.length >= 2) {
          const resp = await api.get("/api/accounts/suggest", {
            params: { client_id: clientId, q: value, limit: 10 },
          });
          setItems((s) => ({ ...s, [uid]: resp.data?.items || [] }));
        } else {
          setItems((s) => ({ ...s, [uid]: [] }));
        }

        // 2) Lookup pour auto-remplir acclib
        const res = await api.get("/api/accounts/lookup", {
          params: { client_id: clientId, accnum: value },
        });
        onLookup({ exists: !!res.data?.exists, acclib: res.data?.acclib });
      }, 300);
    },
    [clientId]
  );

  useEffect(() => {
    // cleanup on unmount
    return () => {
      Object.values(timers.current).forEach(clearTimeout);
    };
  }, []);

  return { itemsByUid, onChange, clear };
}
