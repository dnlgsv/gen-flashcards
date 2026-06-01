import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export function useModels() {
  return useQuery({
    queryKey: ["models"],
    queryFn: () => api.getModels(),
    staleTime: 60_000, // don't re-fetch more than once per minute
    retry: 2,
    refetchOnWindowFocus: false,
  })
}
