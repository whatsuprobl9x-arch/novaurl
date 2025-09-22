import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Modal Component
const Modal = ({ isOpen, onClose, children }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        {children}
      </div>
    </div>
  );
};

// Create URL Modal
const CreateURLModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    redirect_url: '',
    discord_webhook: '',
    custom_html: null
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleFileChange = (e) => {
    setFormData({
      ...formData,
      custom_html: e.target.files[0]
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('redirect_url', formData.redirect_url);
      formDataToSend.append('discord_webhook', formData.discord_webhook);
      
      if (formData.custom_html) {
        formDataToSend.append('custom_html', formData.custom_html);
      }

      const response = await axios.post(`${API}/urls`, formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const shortUrl = `${window.location.origin}/${response.data.short_code}`;
      setSuccess(shortUrl);
      onSuccess(response.data);
      
      // Reset form
      setFormData({
        redirect_url: '',
        discord_webhook: '',
        custom_html: null
      });
      
      // Reset file input
      const fileInput = document.getElementById('custom_html');
      if (fileInput) fileInput.value = '';
      
    } catch (error) {
      console.error('Error creating URL:', error);
      alert('Failed to create URL. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="create-url-modal">
        <h2>Create URL</h2>
        
        {!success ? (
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="redirect_url">Redirect URL:</label>
              <input
                type="url"
                id="redirect_url"
                name="redirect_url"
                value={formData.redirect_url}
                onChange={handleInputChange}
                placeholder="https://example.com"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="discord_webhook">Discord Webhook:</label>
              <input
                type="url"
                id="discord_webhook"
                name="discord_webhook"
                value={formData.discord_webhook}
                onChange={handleInputChange}
                placeholder="https://discord.com/api/webhooks/..."
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="custom_html">Custom Frontend (Optional):</label>
              <input
                type="file"
                id="custom_html"
                name="custom_html"
                accept=".html"
                onChange={handleFileChange}
              />
              <small>Upload an index.html file for custom loading page</small>
            </div>

            <div className="form-actions">
              <button type="button" onClick={onClose} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Creating...' : 'Create'}
              </button>
            </div>
          </form>
        ) : (
          <div className="success-message">
            <h3>LINK CREATED</h3>
            <p>CHECK YOUR WEBHOOK</p>
            <div className="created-url">
              <code>{success}</code>
            </div>
            <button onClick={onClose} className="btn-primary">
              Close
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
};

// Manage URLs Modal
const ManageURLsModal = ({ isOpen, onClose }) => {
  const [urls, setUrls] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchUrls();
    }
  }, [isOpen]);

  const fetchUrls = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/urls`);
      setUrls(response.data);
    } catch (error) {
      console.error('Error fetching URLs:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteUrl = async (shortCode) => {
    if (!window.confirm('Are you sure you want to delete this URL?')) {
      return;
    }

    try {
      await axios.delete(`${API}/urls/${shortCode}`);
      setUrls(urls.filter(url => url.short_code !== shortCode));
    } catch (error) {
      console.error('Error deleting URL:', error);
      alert('Failed to delete URL');
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="manage-urls-modal">
        <h2>Manage URLs</h2>
        
        {loading ? (
          <div className="loading">Loading...</div>
        ) : (
          <div className="urls-list">
            {urls.length === 0 ? (
              <p>No URLs created yet.</p>
            ) : (
              urls.map((url) => (
                <div key={url.id} className="url-item">
                  <div className="url-info">
                    <div className="short-url">
                      <code>{window.location.origin}/{url.short_code}</code>
                    </div>
                    <div className="redirect-url">
                      → {url.redirect_url}
                    </div>
                    <div className="url-stats">
                      Clicks: {url.click_count} | Created: {new Date(url.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <button 
                    onClick={() => deleteUrl(url.short_code)}
                    className="btn-danger"
                  >
                    Delete
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </Modal>
  );
};

// Main App Component
function App() {
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [manageModalOpen, setManageModalOpen] = useState(false);

  const handleURLCreated = (newUrl) => {
    console.log('URL created:', newUrl);
  };

  return (
    <div className="App">
      <div className="main-container">
        <header className="app-header">
          <h1 className="app-title">NOVAURL</h1>
          <p className="app-subtitle">Advanced URL Shortening & Tracking</p>
        </header>

        <div className="action-buttons">
          <button 
            className="action-btn create-btn"
            onClick={() => setCreateModalOpen(true)}
          >
            Create URL
          </button>
          
          <button 
            className="action-btn manage-btn"
            onClick={() => setManageModalOpen(true)}
          >
            Manage URL
          </button>
        </div>

        <div className="features">
          <div className="feature">
            <h3>🔗 Custom Short URLs</h3>
            <p>Generate unique short links with tracking</p>
          </div>
          <div className="feature">
            <h3>📊 Discord Integration</h3>
            <p>Real-time notifications via webhooks</p>
          </div>
          <div className="feature">
            <h3>🎨 Custom Frontend</h3>
            <p>Upload your own loading pages</p>
          </div>
          <div className="feature">
            <h3>📍 IP Tracking</h3>
            <p>Detailed visitor analytics</p>
          </div>
        </div>
      </div>

      <CreateURLModal 
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={handleURLCreated}
      />

      <ManageURLsModal 
        isOpen={manageModalOpen}
        onClose={() => setManageModalOpen(false)}
      />
    </div>
  );
}

export default App;