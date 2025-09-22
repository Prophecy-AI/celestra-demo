import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';

const mockAnalytics = {
  totalHCPs: 1247,
  tier1HCPs: 342,
  tier2HCPs: 905,
  avgPatientVolume: 287,
  topSpecialties: [
    { name: 'Endocrinology', count: 156, percentage: 12.5 },
    { name: 'Internal Medicine', count: 298, percentage: 23.9 },
    { name: 'Family Medicine', count: 387, percentage: 31.0 },
    { name: 'Cardiology', count: 89, percentage: 7.1 }
  ],
  prescriptionTrends: [
    { month: 'Jan', prescriptions: 1250 },
    { month: 'Feb', prescriptions: 1180 },
    { month: 'Mar', prescriptions: 1320 },
    { month: 'Apr', prescriptions: 1280 },
    { month: 'May', prescriptions: 1450 },
    { month: 'Jun', prescriptions: 1380 }
  ]
};

export default function AnalyticsPage() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl mx-auto space-y-6">
            <div className="mb-6">
              <h2 className="text-2xl font-semibold text-gray-900">Analytics Dashboard</h2>
              <p className="text-gray-500 mt-1">Insights and trends from your HCP data</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="text-sm font-medium text-gray-500">Total HCPs</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">{mockAnalytics.totalHCPs.toLocaleString()}</div>
                <div className="text-sm text-green-600 mt-2">+12% from last month</div>
              </div>
              
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="text-sm font-medium text-gray-500">Tier 1 HCPs</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">{mockAnalytics.tier1HCPs.toLocaleString()}</div>
                <div className="text-sm text-blue-600 mt-2">{((mockAnalytics.tier1HCPs / mockAnalytics.totalHCPs) * 100).toFixed(1)}% of total</div>
              </div>
              
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="text-sm font-medium text-gray-500">Tier 2 HCPs</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">{mockAnalytics.tier2HCPs.toLocaleString()}</div>
                <div className="text-sm text-blue-600 mt-2">{((mockAnalytics.tier2HCPs / mockAnalytics.totalHCPs) * 100).toFixed(1)}% of total</div>
              </div>
              
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="text-sm font-medium text-gray-500">Avg Patient Volume</div>
                <div className="text-3xl font-bold text-gray-900 mt-2">{mockAnalytics.avgPatientVolume}</div>
                <div className="text-sm text-green-600 mt-2">+8% from last quarter</div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Specialties</h3>
                <div className="space-y-4">
                  {mockAnalytics.topSpecialties.map((specialty, index) => (
                    <div key={specialty.name} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="text-sm font-medium text-gray-900">{specialty.name}</div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <div className="text-sm text-gray-500">{specialty.count} HCPs</div>
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-black h-2 rounded-full"
                            style={{ width: `${specialty.percentage}%` }}
                          ></div>
                        </div>
                        <div className="text-sm text-gray-500 w-12 text-right">{specialty.percentage}%</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Prescription Trends</h3>
                <div className="space-y-4">
                  {mockAnalytics.prescriptionTrends.map((trend, index) => (
                    <div key={trend.month} className="flex items-center justify-between">
                      <div className="text-sm font-medium text-gray-900">{trend.month} 2024</div>
                      <div className="flex items-center space-x-3">
                        <div className="text-sm text-gray-500">{trend.prescriptions.toLocaleString()}</div>
                        <div className="w-32 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-black h-2 rounded-full"
                            style={{ width: `${(trend.prescriptions / 1500) * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Insights</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="p-4 bg-blue-50 rounded-lg">
                  <div className="text-sm font-medium text-blue-900">Geographic Distribution</div>
                  <div className="text-xs text-blue-700 mt-1">
                    45% of HCPs are concentrated in metropolitan areas with populations over 1M
                  </div>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <div className="text-sm font-medium text-green-900">Prescription Patterns</div>
                  <div className="text-xs text-green-700 mt-1">
                    Tier 1 HCPs show 23% higher prescription rates for new diabetes medications
                  </div>
                </div>
                <div className="p-4 bg-yellow-50 rounded-lg">
                  <div className="text-sm font-medium text-yellow-900">Opportunity Analysis</div>
                  <div className="text-xs text-yellow-700 mt-1">
                    187 high-volume HCPs have not prescribed target medication in 90+ days
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
