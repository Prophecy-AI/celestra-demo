'use client';

import { useState, useEffect } from 'react';

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [searchMode, setSearchMode] = useState<'natural' | 'filters'>('natural');
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  
  const [filters, setFilters] = useState({
    specialty: '',
    location: '',
    tier: '',
    patientVolumeMin: '',
    patientVolumeMax: '',
    lastPrescriptionDays: ''
  });

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (searchMode === 'natural' && !query.trim()) return;
    
    setIsSearching(true);
    setTimeout(() => {
      setIsSearching(false);
      onClose();
    }, 2000);
  };

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      document.documentElement.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
      document.documentElement.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
      document.documentElement.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed top-0 left-0 w-full h-full bg-black bg-opacity-50 flex items-center justify-center z-[9999] p-4"
      style={{ 
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 9999
      }}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Search HCPs</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="mb-6">
            <div className="flex items-center space-x-1 mb-4">
              <button
                onClick={() => setSearchMode('natural')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  searchMode === 'natural'
                    ? 'bg-black text-white'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`}
              >
                Natural Language
              </button>
              <button
                onClick={() => setSearchMode('filters')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  searchMode === 'filters'
                    ? 'bg-black text-white'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`}
              >
                Direct Filters
              </button>
            </div>
            
            {searchMode === 'natural' ? (
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Natural Language Search</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Describe the healthcare professionals you're looking for in plain English
                </p>
              </div>
            ) : (
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Filter Search</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Use specific filters to find healthcare professionals
                </p>
              </div>
            )}
          </div>
          
          <form onSubmit={handleSearch} className="space-y-6">
            <div className="min-h-[160px]">
              {searchMode === 'natural' ? (
                <div className="h-full">
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Example: Doctors who have not prescribed Mounjaro in the last 3 months"
                    className="w-full h-36 px-4 py-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-black focus:border-transparent resize-none text-sm"
                  />
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Specialty</label>
                    <select
                      value={filters.specialty}
                      onChange={(e) => handleFilterChange('specialty', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-black focus:border-transparent text-sm"
                    >
                      <option value="">All Specialties</option>
                      <option value="endocrinology">Endocrinology</option>
                      <option value="internal-medicine">Internal Medicine</option>
                      <option value="family-medicine">Family Medicine</option>
                      <option value="cardiology">Cardiology</option>
                      <option value="oncology">Oncology</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                    <input
                      type="text"
                      value={filters.location}
                      onChange={(e) => handleFilterChange('location', e.target.value)}
                      placeholder="City, State"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-black focus:border-transparent text-sm"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Tier</label>
                    <select
                      value={filters.tier}
                      onChange={(e) => handleFilterChange('tier', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-black focus:border-transparent text-sm"
                    >
                      <option value="">All Tiers</option>
                      <option value="tier-1">Tier 1</option>
                      <option value="tier-2">Tier 2</option>
                      <option value="tier-3">Tier 3</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Min Patient Volume</label>
                    <input
                      type="number"
                      value={filters.patientVolumeMin}
                      onChange={(e) => handleFilterChange('patientVolumeMin', e.target.value)}
                      placeholder="0"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-black focus:border-transparent text-sm"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Max Patient Volume</label>
                    <input
                      type="number"
                      value={filters.patientVolumeMax}
                      onChange={(e) => handleFilterChange('patientVolumeMax', e.target.value)}
                      placeholder="1000"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-black focus:border-transparent text-sm"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Days Since Last Prescription</label>
                    <select
                      value={filters.lastPrescriptionDays}
                      onChange={(e) => handleFilterChange('lastPrescriptionDays', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-black focus:border-transparent text-sm"
                    >
                      <option value="">Any Time</option>
                      <option value="30">Last 30 days</option>
                      <option value="60">Last 60 days</option>
                      <option value="90">Last 90 days</option>
                      <option value="180">Last 6 months</option>
                      <option value="365">Last year</option>
                    </select>
                  </div>
                </div>
              )}
            </div>
            
            <div className="flex justify-between pt-4 border-t border-gray-200">
              <button
                type="button"
                onClick={onClose}
                className="px-6 py-2 text-gray-700 bg-gray-100 text-sm font-medium rounded-md hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSearching || (searchMode === 'natural' && !query.trim())}
                className="px-6 py-2 bg-black text-white text-sm font-medium rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSearching ? 'Searching...' : 'Search HCPs'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
