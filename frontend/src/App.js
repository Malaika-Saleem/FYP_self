
import React, { useEffect, useState, useRef } from 'react';

const BACKEND = 'http://localhost:5000';

export default function App() {
  const [videos, setVideos] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
  const fileRef = useRef();

  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    const res = await fetch(`${BACKEND}/videos`);
    const data = await res.json();
    if (data.ok) setVideos(data.videos);
  };

  // chunked upload
  const uploadFile = async (file) => {
    const total = Math.ceil(file.size / CHUNK_SIZE);
    let uploaded = 0;
    for (let i = 0; i < total; i++) {
      const start = i * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);
      const form = new FormData();
      form.append('file', chunk);
      form.append('filename', file.name);
      form.append('chunk_index', i);
      form.append('total_chunks', total);

      const res = await fetch(`${BACKEND}/upload_chunk`, {
        method: 'POST',
        body: form,
      });
      const json = await res.json();
      if (!json.ok) {
        alert('Upload chunk failed');
        return;
      }
      uploaded++;
      setUploadProgress(Math.round((uploaded / total) * 100));
    }

    // ask server to merge
    const mergeRes = await fetch(`${BACKEND}/merge_chunks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: file.name }),
    });
    const mergeJson = await mergeRes.json();
    if (mergeJson.ok) {
      setUploadProgress(100);
      fetchVideos();
      alert('Upload complete!');
    } else {
      alert('Merge failed');
    }
  };

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (f) {
      setSelectedFile(f);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return alert('choose a file');
    setUploadProgress(0);
    await uploadFile(selectedFile);
  };

  return (
    <div style={{ padding: 20, fontFamily: 'Arial, sans-serif' }}>
      <h2>DetectifAI — Local Prototype</h2>

      <section style={{ marginBottom: 24 }}>
        <h3>Live Camera Feed</h3>
        <div>
          <img
            style={{ width: 640, height: 480, background: '#000' }}
            src={`${BACKEND}/video_feed`} 
            alt="camera"
          />
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3>Upload Large Video (Chunked)</h3>
        <input ref={fileRef} type="file" accept="video/*" onChange={handleFileChange} />
        <div style={{ marginTop: 8 }}>
          <button onClick={handleUpload}>Upload</button>
        </div>
        <div style={{ marginTop: 8 }}>Progress: {uploadProgress}%</div>
      </section>

      <section>
        <h3>Stored Videos</h3>
        {videos.length === 0 && <div>No videos yet</div>}
        <ul>
          {videos.map((v) => (
            <li key={v.name} style={{ marginBottom: 12 }}>
              <div>{v.name}</div>
              <video controls width={480} src={`${BACKEND}${v.url}`} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}