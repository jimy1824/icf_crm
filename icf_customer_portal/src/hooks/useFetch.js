import { useQuery } from '@tanstack/react-query';

/**
 * Lightweight wrapper around useQuery for simple GET fetches.
 *
 * @param {string|string[]} queryKey  - TanStack Query key
 * @param {Function} fetchFn          - async function returning data
 * @param {object}   options          - extra useQuery options
 */
export function useFetch(queryKey, fetchFn, options = {}) {
  return useQuery({
    queryKey: Array.isArray(queryKey) ? queryKey : [queryKey],
    queryFn: fetchFn,
    ...options,
  });
}
