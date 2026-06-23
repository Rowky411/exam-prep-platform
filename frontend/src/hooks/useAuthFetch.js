import { useAuth } from '@clerk/clerk-react'

export default function useAuthFetch() {
  const { getToken } = useAuth()
  return async (url, options = {}) => {
    const token = await getToken()
    return fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    })
  }
}
