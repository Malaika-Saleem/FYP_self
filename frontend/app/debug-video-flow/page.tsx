'use client'

import { useState } from 'react'

export default function DebugVideoFlow() {
  const [videoId, setVideoId] = useState('')
  const [results, setResults] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const testEndpoint = async (endpoint: string) => {
    try {
      setLoading(true)
      const response = await fetch(endpoint)
      const data = await response.json()
      console.log(`${endpoint}:`, response.status, data)
      return { status: response.status, data }
    } catch (error) {
      console.error(`Error testing ${endpoint}:`, error)
      return { status: 'ERROR', error: error.message }
    } finally {
      setLoading(false)
    }
  }

  const testAllEndpoints = async () => {
    if (!videoId) {
      alert('Please enter a video ID')
      return
    }

    const endpoints = [
      `/api/video/status/${videoId}`,
      `/api/video/results/${videoId}`,
      `/api/video/keyframes/${videoId}`,
      `/api/video/faces/${videoId}`,
      `/api/video/compressed/${videoId}`
    ]

    const results = {}
    for (const endpoint of endpoints) {
      results[endpoint] = await testEndpoint(endpoint)
      await new Promise(resolve => setTimeout(resolve, 500)) // Small delay between requests
    }

    setResults(results)
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Debug Video Flow</h1>
      
      <div className="mb-6">
        <label className="block mb-2 font-medium">Video ID:</label>
        <input
          type="text"
          value={videoId}
          onChange={(e) => setVideoId(e.target.value)}
          className="border rounded px-3 py-2 w-full max-w-md"
          placeholder="Enter video ID to test"
        />
        <button
          onClick={testAllEndpoints}
          disabled={loading}
          className="ml-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Testing...' : 'Test All Endpoints'}
        </button>
      </div>

      {results && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold">Endpoint Test Results</h2>
          {Object.entries(results).map(([endpoint, result]: [string, any]) => (
            <div key={endpoint} className="border rounded p-4">
              <h3 className="font-bold text-lg mb-2">{endpoint}</h3>
              <div className={`p-2 rounded ${result.status === 200 ? 'bg-green-100' : 'bg-red-100'}`}>
                <p><strong>Status:</strong> {result.status}</p>
                <pre className="mt-2 text-sm overflow-auto max-h-40">
                  {JSON.stringify(result.data || result.error, null, 2)}
                </pre>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 p-4 bg-gray-100 rounded">
        <h3 className="font-bold mb-2">Instructions:</h3>
        <ol className="list-decimal list-inside space-y-1 text-sm">
          <li>Upload a video using the dashboard</li>
          <li>Copy the video ID from the upload response</li>
          <li>Paste it here and test all endpoints</li>
          <li>Check browser console for detailed logs</li>
        </ol>
      </div>
    </div>
  )
}
