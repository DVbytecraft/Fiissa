import { useEffect, useState } from "react";

/**
 * Retarde la mise à jour d'une valeur pour éviter des requêtes API à chaque frappe.
 * Usage : const debouncedSearch = useDebounce(search, 350);
 */
export function useDebounce<T>(value: T, delayMs = 350): T {
  const [debounced, setDebounced] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
