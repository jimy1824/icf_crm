import Sidebar from './Sidebar.jsx';
import Topbar from './Topbar.jsx';
import CommandPalette from '../search/CommandPalette.jsx';

export default function Shell({ children }) {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
