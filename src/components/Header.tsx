export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200 px-8 py-4">
      <div className="flex items-center justify-end">
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
