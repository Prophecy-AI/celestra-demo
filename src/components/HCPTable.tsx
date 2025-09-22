'use client';

import { useState } from 'react';

interface HCPTableProps {
  onOpenSearch: () => void;
}

interface HCP {
  id: string;
  name: string;
  specialty: string;
  location: string;
  lastPrescription: string;
  patientVolume: number;
  tier: string;
}

const mockHCPs: HCP[] = [
  {
    id: '1',
    name: 'Dr. Sarah Johnson',
    specialty: 'Endocrinology',
    location: 'New York, NY',
    lastPrescription: '2024-06-15',
    patientVolume: 450,
    tier: 'Tier 1'
  },
  {
    id: '2',
    name: 'Dr. Michael Chen',
    specialty: 'Internal Medicine',
    location: 'Los Angeles, CA',
    lastPrescription: '2024-05-20',
    patientVolume: 320,
    tier: 'Tier 2'
  },
  {
    id: '3',
    name: 'Dr. Emily Rodriguez',
    specialty: 'Family Medicine',
    location: 'Chicago, IL',
    lastPrescription: '2024-04-10',
    patientVolume: 280,
    tier: 'Tier 2'
  },
  {
    id: '4',
    name: 'Dr. James Wilson',
    specialty: 'Cardiology',
    location: 'Houston, TX',
    lastPrescription: '2024-07-22',
    patientVolume: 520,
    tier: 'Tier 1'
  },
  {
    id: '5',
    name: 'Dr. Lisa Thompson',
    specialty: 'Endocrinology',
    location: 'Phoenix, AZ',
    lastPrescription: '2024-08-05',
    patientVolume: 380,
    tier: 'Tier 1'
  },
  {
    id: '6',
    name: 'Dr. Robert Martinez',
    specialty: 'Internal Medicine',
    location: 'Philadelphia, PA',
    lastPrescription: '2024-03-28',
    patientVolume: 295,
    tier: 'Tier 2'
  },
  {
    id: '7',
    name: 'Dr. Jennifer Davis',
    specialty: 'Family Medicine',
    location: 'San Antonio, TX',
    lastPrescription: '2024-09-10',
    patientVolume: 410,
    tier: 'Tier 1'
  },
  {
    id: '8',
    name: 'Dr. David Anderson',
    specialty: 'Oncology',
    location: 'San Diego, CA',
    lastPrescription: '2024-02-14',
    patientVolume: 180,
    tier: 'Tier 3'
  },
  {
    id: '9',
    name: 'Dr. Maria Garcia',
    specialty: 'Endocrinology',
    location: 'Dallas, TX',
    lastPrescription: '2024-08-30',
    patientVolume: 465,
    tier: 'Tier 1'
  },
  {
    id: '10',
    name: 'Dr. Christopher Lee',
    specialty: 'Cardiology',
    location: 'San Jose, CA',
    lastPrescription: '2024-07-08',
    patientVolume: 340,
    tier: 'Tier 2'
  },
  {
    id: '11',
    name: 'Dr. Amanda White',
    specialty: 'Internal Medicine',
    location: 'Austin, TX',
    lastPrescription: '2024-06-25',
    patientVolume: 385,
    tier: 'Tier 1'
  },
  {
    id: '12',
    name: 'Dr. Kevin Brown',
    specialty: 'Family Medicine',
    location: 'Jacksonville, FL',
    lastPrescription: '2024-04-18',
    patientVolume: 225,
    tier: 'Tier 3'
  },
  {
    id: '13',
    name: 'Dr. Rachel Taylor',
    specialty: 'Endocrinology',
    location: 'Fort Worth, TX',
    lastPrescription: '2024-09-02',
    patientVolume: 490,
    tier: 'Tier 1'
  },
  {
    id: '14',
    name: 'Dr. Steven Miller',
    specialty: 'Oncology',
    location: 'Columbus, OH',
    lastPrescription: '2024-01-30',
    patientVolume: 155,
    tier: 'Tier 3'
  },
  {
    id: '15',
    name: 'Dr. Nicole Thomas',
    specialty: 'Cardiology',
    location: 'Charlotte, NC',
    lastPrescription: '2024-08-12',
    patientVolume: 375,
    tier: 'Tier 2'
  },
  {
    id: '16',
    name: 'Dr. Brian Jackson',
    specialty: 'Internal Medicine',
    location: 'Indianapolis, IN',
    lastPrescription: '2024-05-15',
    patientVolume: 310,
    tier: 'Tier 2'
  },
  {
    id: '17',
    name: 'Dr. Michelle Harris',
    specialty: 'Family Medicine',
    location: 'Seattle, WA',
    lastPrescription: '2024-07-28',
    patientVolume: 420,
    tier: 'Tier 1'
  },
  {
    id: '18',
    name: 'Dr. Daniel Clark',
    specialty: 'Endocrinology',
    location: 'Denver, CO',
    lastPrescription: '2024-06-08',
    patientVolume: 445,
    tier: 'Tier 1'
  },
  {
    id: '19',
    name: 'Dr. Laura Lewis',
    specialty: 'Oncology',
    location: 'Washington, DC',
    lastPrescription: '2024-03-12',
    patientVolume: 190,
    tier: 'Tier 3'
  },
  {
    id: '20',
    name: 'Dr. Mark Robinson',
    specialty: 'Cardiology',
    location: 'Boston, MA',
    lastPrescription: '2024-09-15',
    patientVolume: 510,
    tier: 'Tier 1'
  }
];

export default function HCPTable({ onOpenSearch }: HCPTableProps) {
  const [selectedHCPs, setSelectedHCPs] = useState<string[]>([]);
  const [hcps] = useState<HCP[]>(mockHCPs);

  const toggleSelection = (id: string) => {
    setSelectedHCPs(prev => 
      prev.includes(id) 
        ? prev.filter(hcpId => hcpId !== id)
        : [...prev, id]
    );
  };

  const selectAll = () => {
    setSelectedHCPs(hcps.map(hcp => hcp.id));
  };

  const clearSelection = () => {
    setSelectedHCPs([]);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={onOpenSearch}
            className="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200 transition-colors flex items-center space-x-2"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            <span>Filter</span>
          </button>
          <span className="text-lg font-semibold text-gray-900">
            {hcps.length.toLocaleString()} results
          </span>
          {selectedHCPs.length > 0 && (
            <span className="text-sm text-gray-500">
              {selectedHCPs.length} selected
            </span>
          )}
        </div>
        <div className="flex items-center space-x-3">
          {selectedHCPs.length > 0 && (
            <button
              onClick={clearSelection}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear selection
            </button>
          )}
          <button
            disabled={selectedHCPs.length === 0}
            className="px-4 py-2 bg-black text-white text-sm font-medium rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save as Cluster ({selectedHCPs.length})
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
                  checked={selectedHCPs.length === hcps.length}
                  onChange={selectedHCPs.length === hcps.length ? clearSelection : selectAll}
                  className="h-4 w-4 text-black border-gray-300 rounded focus:ring-black"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Specialty
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Location
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Prescription
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Patient Volume
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tier
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {hcps.map((hcp) => (
              <tr
                key={hcp.id}
                className={`hover:bg-gray-50 ${selectedHCPs.includes(hcp.id) ? 'bg-blue-50' : ''}`}
              >
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={selectedHCPs.includes(hcp.id)}
                    onChange={() => toggleSelection(hcp.id)}
                    className="h-4 w-4 text-black border-gray-300 rounded focus:ring-black"
                  />
                </td>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">
                  {hcp.name}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {hcp.specialty}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {hcp.location}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {hcp.lastPrescription}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {hcp.patientVolume.toLocaleString()}
                </td>
                <td className="px-6 py-4 text-sm">
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                    hcp.tier === 'Tier 1' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {hcp.tier}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
