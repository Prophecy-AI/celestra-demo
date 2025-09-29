'use client';

import { useState } from 'react';

interface HCP {
  id: string;
  name: string;
  specialty: string;
  location: string;
  lastPrescription: string;
  patientVolume: number;
  tier: string;
}

interface HCPTableViewProps {
  clusterName?: string;
  onBack?: () => void;
  data?: any[];
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

export default function HCPTableView({ clusterName, onBack, data }: HCPTableViewProps) {
  const [hcps] = useState<HCP[]>(mockHCPs);
  
  // Use actual data if provided, otherwise fall back to mock data
  const displayData = data || hcps;
  const isRealData = !!data;

  return (
    <>
      <div>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            {onBack && (
              <button
                onClick={onBack}
                className="p-2 text-gray-500 hover:text-gray-700 transition-colors"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            )}
            <span className="text-lg font-semibold text-gray-900">
              {clusterName ? `${clusterName} - ` : ''}{displayData.length.toLocaleString()} {isRealData ? 'Records' : 'HCPs'}
            </span>
          </div>
        </div>
        
        <div className="overflow-x-auto border border-gray-200 rounded-lg">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                {isRealData && displayData.length > 0 ? (
                  // Dynamic headers for real CSV data
                  Object.keys(displayData[0]).map((header, idx) => (
                    <th
                      key={idx}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {header}
                    </th>
                  ))
                ) : (
                  // Fixed headers for mock data
                  <>
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
                  </>
                )}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {isRealData ? (
                // Render real CSV data
                displayData.map((row, rowIdx) => (
                  <tr key={rowIdx} className="hover:bg-gray-50">
                    {Object.keys(row).map((header, colIdx) => (
                      <td
                        key={colIdx}
                        className="px-6 py-4 text-sm text-gray-900"
                      >
                        {row[header]}
                      </td>
                    ))}
                  </tr>
                ))
              ) : (
                // Render mock HCP data
                hcps.map((hcp) => (
                  <tr
                    key={hcp.id}
                    className="hover:bg-gray-50"
                  >
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
                          : hcp.tier === 'Tier 2'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {hcp.tier}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
