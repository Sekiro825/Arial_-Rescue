import React, { useEffect, useState } from 'react';
import "../assets/style.css"; // Ensure this path is correct
import backgroundImage from '../assets/background.jpg'; // Import your background image

const DriveContent = () => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Replace with your actual API key and Folder ID
  const API_KEY = 'AIzaSyDTU7Eo3qmmZhaGfctKllk2bR826NJL3Rk';
  const FOLDER_ID = '1QeHWVbsJh2KKK57rJbDqzpi4xxsXjJRC';

  useEffect(() => {
    const fetchDriveFiles = async () => {
      setLoading(true);
      setError(null);
      try {
        const query = `'${FOLDER_ID}' in parents and (mimeType='image/jpeg' or mimeType='image/png' or mimeType='image/gif' or mimeType='text/plain')`;

        const res = await fetch(
          `https://www.googleapis.com/drive/v3/files?q=${encodeURIComponent(query)}&key=${API_KEY}&fields=files(id,name,mimeType,thumbnailLink,webContentLink)`
        );

        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(`Failed to fetch files: ${res.status} - ${errorData.error.message}`);
        }

        const data = await res.json();
        setFiles(data.files || []);
      } catch (err) {
        console.error('Error fetching files:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDriveFiles();
  }, []);

  if (loading) {
    return <p>Loading files...</p>;
  }

  if (error) {
    return <p>Error loading files: {error}</p>;
  }

  return (
    <div className="drive-content">
      <h2>Drive Content</h2>
      <div className="file-grid">
        {files.length === 0 ? (
          <p>No files found in this folder.</p>
        ) : (
          files.map((file) => (
            <div key={file.id} className="file-item">
              {file.mimeType.startsWith('image/') ? (
                <div className="image-container">
                  {file.webContentLink ? (
                    <a href={file.webContentLink} target="_blank" rel="noopener noreferrer">
                      <img
                        src={file.thumbnailLink ? file.thumbnailLink.replace('s220', 's0') : `https://drive.google.com/uc?id=${file.id}`}
                        alt={file.name}
                        className="drive-image"
                      />
                    </a>
                  ) : (
                    <img
                      src={file.thumbnailLink ? file.thumbnailLink.replace('s220', 's0') : `https://drive.google.com/uc?id=${file.id}`}
                      alt={file.name}
                      className="drive-image"
                    />
                  )}
                  <p className="file-name">{file.name}</p>
                </div>
              ) : file.mimeType === 'text/plain' ? (
                <div className="text-file-container">
                  <a
                    href={`https://drive.google.com/uc?id=${file.id}&export=download`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-file-link"
                  >
                    📄 {file.name}
                  </a>
                </div>
              ) : (
                <div className="unknown-file">
                  <p>Unknown File: {file.name}</p>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default DriveContent;