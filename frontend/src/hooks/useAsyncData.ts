'use client'

import { useCallback, useEffect, useState } from 'react'

interface AsyncDataState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

// Simulated network delay + real error handling, so loading/error UI can be
// built and tested before the real backend is wired in. Once the backend
// is ready, replace the `loader` you pass in with a real fetch call —
// this hook's loading/error/retry behavior does not need to change.
export function useAsyncData<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<AsyncDataState<T>>({ data: null, loading: true, error: null })
  const [attempt, setAttempt] = useState(0)

  const retry = useCallback(() => setAttempt(a => a + 1), [])

  useEffect(() => {
    let cancelled = false
    setState(s => ({ ...s, loading: true, error: null }))

    loader()
      .then(data => { if (!cancelled) setState({ data, loading: false, error: null }) })
      .catch(err => { if (!cancelled) setState({ data: null, loading: false, error: err instanceof Error ? err.message : 'Something went wrong.' }) })

    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt, ...deps])

  return { ...state, retry }
}

// Wraps mock data in a Promise with an artificial delay, so the UI behaves
// exactly as it will once real fetch calls are swapped in. Change USE_ERROR
// to true temporarily to preview the error state during development.
const USE_ERROR = false

export function delayedMock<T>(value: T, ms = 200): Promise<T> {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (USE_ERROR) reject(new Error('Could not reach the server. Please check your connection.'))
      else resolve(value)
    }, ms)
  })
}