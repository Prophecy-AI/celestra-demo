'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';
import HCPTableView from '@/components/HCPTableView';

interface Cluster {
  id: string;
  name: string;
  description: string;
  size: number;
}

const mockClusters: Cluster[] = [
  {
    id: '1',
    name: 'High-Volume Endocrinologists',
    description: 'Endocrinologists with 300+ patients and recent Mounjaro prescriptions',
    size: 45
  },
  {
    id: '2',
    name: 'Tier 1 Non-Prescribers',
    description: 'Tier 1 doctors who have not prescribed Mounjaro in 90+ days',
    size: 23
  },
  {
    id: '3',
    name: 'Urban Family Medicine',
    description: 'Family medicine practitioners in metropolitan areas',
    size: 67
  },
  {
    id: '4',
    name: 'Recent Cardiology Adopters',
    description: 'Cardiologists who started prescribing within the last 6 months',
    size: 32
  },
  {
    id: '5',
    name: 'High-Value Internal Medicine',
    description: 'Internal medicine doctors with Tier 1 status and high patient volumes',
    size: 89
  },
  {
    id: '6',
    name: 'West Coast Specialists',
    description: 'Specialty practitioners located in California, Oregon, and Washington',
    size: 156
  }
];

export default function ClustersPage() {
  const [selectedClusters, setSelectedClusters] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<'list' | 'table'>('list');
  const [selectedClusterForView, setSelectedClusterForView] = useState<Cluster | null>(null);

  const toggleSelection = (id: string) => {
    setSelectedClusters(prev => 
      prev.includes(id) 
        ? prev.filter(clusterId => clusterId !== id)
        : [...prev, id]
    );
  };

  const selectAll = () => {
    setSelectedClusters(mockClusters.map(cluster => cluster.id));
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

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl mx-auto">
            {viewMode === 'list' ? (
              <>
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-4">
                    <span className="text-lg font-semibold text-gray-900">
                      {mockClusters.length} clusters
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
                      disabled={selectedClusters.length === 0}
                      className="px-4 py-2 bg-black text-white text-sm font-medium rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Delete Selected ({selectedClusters.length})
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
                            checked={selectedClusters.length === mockClusters.length}
                            onChange={selectedClusters.length === mockClusters.length ? clearSelection : selectAll}
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
                      {mockClusters.map((cluster) => (
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
                            {cluster.description}
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
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
