'use client';

import { useState, useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';
import HCPTableView from '@/components/HCPTableView';

interface Cluster {
  id: string;
  name: string;
  description?: string;
  size: number;
  filename?: string;
  data?: any[];
}

const hardcodedClusters: Cluster[] = [
  {
    id: '1',
    name: 'High-Volume Rheumatologists',
    description: 'Rheumatologists treating 200+ autoimmune patients with recent JAK inhibitor prescriptions',
    size: 342
  },
  {
    id: '2',
    name: 'Academic Immunology Centers',
    description: 'Immunologists at major academic medical centers specializing in complex autoimmune disorders',
    size: 87
  }
];

export default function ClustersPage() {
  const [selectedClusters, setSelectedClusters] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<'list' | 'table'>('list');
  const [selectedClusterForView, setSelectedClusterForView] = useState<Cluster | null>(null);
  const [savedClusters, setSavedClusters] = useState<Cluster[]>([]);

  // Load saved clusters from sessionStorage (shared with Explore page)
  useEffect(() => {
    const loadSavedClusters = () => {
      const saved = sessionStorage.getItem('savedClusters');
      if (saved) {
        try {
          setSavedClusters(JSON.parse(saved));
        } catch (e) {
          console.error('Failed to load saved clusters:', e);
        }
      }
    };

    // Load on mount
    loadSavedClusters();

    // Listen for storage changes from other tabs/pages
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'savedClusters') {
        loadSavedClusters();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // Combine hardcoded and saved clusters
  const allClusters = [...hardcodedClusters, ...savedClusters];
  
  // Count how many selected clusters can actually be deleted (only saved ones)
  const deletableSelectedCount = selectedClusters.filter(id => id.startsWith('saved-')).length;

  const toggleSelection = (id: string) => {
    setSelectedClusters(prev => 
      prev.includes(id) 
        ? prev.filter(clusterId => clusterId !== id)
        : [...prev, id]
    );
  };

  const selectAll = () => {
    setSelectedClusters(allClusters.map(cluster => cluster.id));
  };

  const clearSelection = () => {
    setSelectedClusters([]);
  };

  const handleViewCluster = (cluster: Cluster) => {
    setSelectedClusterForView(cluster);
    setViewMode('table');
  };

  const handleBackToList = () => {
    setViewMode('list');
    setSelectedClusterForView(null);
  };

  const handleDeleteSelected = () => {
    // Only delete saved clusters (hardcoded ones cannot be deleted)
    const deletableClusters = selectedClusters.filter(id => id.startsWith('saved-'));
    
    if (deletableClusters.length === 0) {
      alert('Only saved clusters can be deleted. Hardcoded clusters cannot be removed.');
      return;
    }
    
    // Filter out selected saved clusters
    const updatedSavedClusters = savedClusters.filter(cluster => !deletableClusters.includes(cluster.id));
    setSavedClusters(updatedSavedClusters);
    
    // Update sessionStorage
    sessionStorage.setItem('savedClusters', JSON.stringify(updatedSavedClusters));
    
    // Clear selection
    setSelectedClusters([]);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header connected={true} />
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl mx-auto">
            {viewMode === 'list' ? (
              <>
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-4">
                    <span className="text-lg font-semibold text-gray-900">
                      {allClusters.length} clusters
                    </span>
                    {selectedClusters.length > 0 && (
                      <span className="text-sm text-gray-500">
                        {selectedClusters.length} selected
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-3">
                    {selectedClusters.length > 0 && (
                      <button
                        onClick={clearSelection}
                        className="text-sm text-gray-500 hover:text-gray-700"
                      >
                        Clear selection
                      </button>
                    )}
                    <button
                      onClick={handleDeleteSelected}
                      disabled={deletableSelectedCount === 0}
                      className="px-4 py-2 bg-black text-white text-sm font-medium rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Delete Selected ({deletableSelectedCount})
                    </button>
                  </div>
                </div>
                
                <div className="overflow-x-auto border border-gray-200 rounded-lg">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="w-12 px-6 py-3">
                          <input
                            type="checkbox"
                            checked={selectedClusters.length === allClusters.length}
                            onChange={selectedClusters.length === allClusters.length ? clearSelection : selectAll}
                            className="h-4 w-4 text-black border-gray-300 rounded focus:ring-black"
                          />
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Name
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Description
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Size
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {allClusters.map((cluster) => (
                        <tr
                          key={cluster.id}
                          className={`hover:bg-gray-50 ${selectedClusters.includes(cluster.id) ? 'bg-blue-50' : ''}`}
                        >
                          <td className="px-6 py-4">
                            <input
                              type="checkbox"
                              checked={selectedClusters.includes(cluster.id)}
                              onChange={() => toggleSelection(cluster.id)}
                              className="h-4 w-4 text-black border-gray-300 rounded focus:ring-black"
                            />
                          </td>
                          <td className="px-6 py-4 text-sm font-medium text-gray-900">
                            {cluster.name}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500 max-w-md">
                            {cluster.description || 'No description'}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            {cluster.size} HCPs
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500">
                            <div className="flex space-x-2">
                              <button 
                                onClick={() => handleViewCluster(cluster)}
                                className="text-gray-600 hover:text-gray-900"
                              >
                                View
                              </button>
                              <button className="text-gray-600 hover:text-gray-900">
                                Analyze
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <HCPTableView 
                clusterName={selectedClusterForView?.name}
                onBack={handleBackToList}
                data={selectedClusterForView?.data}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
