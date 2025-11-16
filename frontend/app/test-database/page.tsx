'use client'

import { useState } from 'react'

export default function TestDatabase() {
  const [results, setResults] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const testDatabaseContents = async () => {
    setLoading(true)
    const endpoints = [
      { name: 'Backend Health', url: 'http://localhost:5000/api/health' },
      { name: 'List Videos (Direct)', url: 'http://localhost:5000/api/videos' },
      { name: 'V2 Upload Test', url: '/api/video/upload', method: 'POST', test: true }
    ]

    const results = {}
    
    for (const endpoint of endpoints) {
      try {
        let response
        if (endpoint.method === 'POST') {
          // Skip POST test for now
          results[endpoint.name] = { status: 'SKIPPED', message: 'POST endpoint - need actual file' }
          continue
        }
        
        response = await fetch(endpoint.url)
        const data = await response.json()
        
        results[endpoint.name] = {
          status: response.status,
          data: data
        }
      } catch (error) {
        results[endpoint.name] = {
          status: 'ERROR',
          error: error.message
        }
      }
    }

    setResults(results)
    setLoading(false)
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Database Integration Test</h1>
      
      <div className="mb-6">
        <button
          onClick={testDatabaseContents}
          disabled={loading}
          className="px-6 py-3 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? 'Testing Database...' : 'Test Database Integration'}
        </button>
      </div>

      {results && (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold">Database Test Results</h2>
          {Object.entries(results).map(([name, result]: [string, any]) => (
            <div key={name} className="border rounded p-4">
              <h3 className="font-bold text-lg mb-2">{name}</h3>
              <div className={`p-3 rounded ${
                result.status === 200 ? 'bg-green-100' : 
                result.status === 'SKIPPED' ? 'bg-yellow-100' :
                'bg-red-100'
              }`}>
                <p><strong>Status:</strong> {result.status}</p>
                {result.data && (
                  <pre className="mt-2 text-sm overflow-auto max-h-60 bg-white p-2 rounded border">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                )}
                {result.error && (
                  <p className="mt-2 text-red-600"><strong>Error:</strong> {result.error}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 p-4 bg-blue-50 rounded border">
        <h3 className="font-bold mb-2">What This Tests:</h3>
        <ul className="list-disc list-inside space-y-1 text-sm">
          <li>✅ Backend health and database status</li>
          <li>🗄️ Any existing videos in MongoDB</li>
          <li>🔌 API connectivity and response format</li>
          <li>📊 Database integration working properly</li>
        </ul>
        
        <div className="mt-4">
          <h4 className="font-semibold">Expected Results:</h4>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
            <li>Health check should show <code>database_enabled: true</code></li>
            <li>Videos endpoint may show empty list if no uploads yet</li>
            <li>All endpoints should return JSON (not HTML errors)</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
