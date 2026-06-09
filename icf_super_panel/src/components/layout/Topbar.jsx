import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, ChevronDown, LogOut, Moon, Search, Sun, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext.jsx';
import { useTheme } from '../../context/ThemeContext.jsx';
import CommandPalette from '../search/CommandPalette.jsx';

function Avatar({ user }) {
  const initials = `${user?.first_name?.[0] ?? ''}${user?.last_name?.[0] ?? ''}`.toUpperCase() || 'U';
  return (
    <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
      {initials}
    </div>
  );
}

export default function Topbar() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [cmdOpen, setCmdOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate('/login');
  }

  useEffect(() => {
    function handler(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCmdOpen((o) => !o);
      }
    }
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <>
      <header className="h-16 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between px-6 flex-shrink-0 z-10">
        {/* Left — Search trigger */}
        <button
          onClick={() => setCmdOpen(true)}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700
                     text-sm text-gray-400 hover:border-gray-300 hover:text-gray-500
                     transition-colors duration-150 bg-gray-50 dark:bg-gray-800 hover:bg-white dark:hover:bg-gray-700 min-w-[200px]"
        >
          <Search className="w-3.5 h-3.5" />
          <span className="flex-1 text-left">Search…</span>
          <span className="flex items-center gap-0.5 text-xs text-gray-400">
            <kbd className="px-1 py-0.5 bg-white dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 text-[10px] font-medium">⌘</kbd>
            <kbd className="px-1 py-0.5 bg-white dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 text-[10px] font-medium">K</kbd>
          </span>
        </button>

        {/* Right */}
        <div className="flex items-center gap-2">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-gray-200 transition-colors"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Notifications */}
          <button className="relative p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-gray-200 transition-colors">
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-red-500" />
          </button>

          {/* User menu */}
          <div className="relative">
            <button
              onClick={() => setUserOpen((o) => !o)}
              className="flex items-center gap-2.5 pl-2 pr-3 py-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800
                         transition-colors duration-150"
            >
              <Avatar user={user} />
              <div className="text-left hidden sm:block">
                <p className="text-sm font-medium text-gray-900 dark:text-white leading-none">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-xs text-gray-400 mt-0.5 capitalize">
                  {user?.role?.replace('_', ' ')}
                </p>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
            </button>

            {userOpen && (
              <>
                <div className="fixed inset-0 z-20" onClick={() => setUserOpen(false)} />
                <div className="absolute right-0 top-full mt-2 w-48 bg-white dark:bg-gray-900 rounded-xl shadow-modal border border-gray-100 dark:border-gray-700 z-30 overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{user?.first_name} {user?.last_name}</p>
                    <p className="text-xs text-gray-400 truncate">{user?.email}</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-red-600
                               hover:bg-red-50 transition-colors text-left"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
    </>
  );
}
