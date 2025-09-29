type Props = { connected?: boolean };

export default function Header({ connected = false }: Props) {
  return (
    <header className="bg-white border-b border-gray-200 px-8 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full ${connected ? 'bg-green-500 status-pulse' : 'bg-red-500'}`}
          />
          <span className="text-xs text-gray-600">
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <div className="flex items-center space-x-4">
          <div className="text-right">
            <div className="text-sm font-medium text-gray-900">Demo Environment</div>
            <div className="text-xs text-gray-500">Celestra HCP Targeting Platform</div>
          </div>
          <div className="h-8 w-8 bg-gray-900 rounded-full flex items-center justify-center">
            <span className="text-white text-sm font-medium">D</span>
          </div>
        </div>
      </div>
    </header>
  );
}
