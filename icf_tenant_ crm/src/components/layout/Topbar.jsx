import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { Bell, LogOut, Moon, Search, Sun, User } from 'lucide-react';
import { logoutAction } from '../../store/authSlice.js';
import { toggleTheme, setCommandPalette } from '../../store/uiSlice.js';
import { useAuth } from '../../hooks/useAuth.js';

export default function Topbar() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useAuth();
  const theme = useSelector((s) => s.ui.theme);
  const notifCount = useSelector((s) => s.ui.notificationCount);

  useEffect(() => {
    function onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        dispatch(setCommandPalette(true));
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [dispatch]);

  const initials = user
    ? `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase() || user.email?.[0]?.toUpperCase()
    : '?';

  return (
    <header className="h-14 flex items-center justify-between px-5 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
      {/* Search trigger */}
      <button
        onClick={() => dispatch(setCommandPalette(true))}
        className="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300
                   bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg
                   px-3 py-1.5 w-64 transition-colors"
      >
        <Search className="w-3.5 h-3.5 flex-shrink-0" />
        <span className="flex-1 text-left">Search anything…</span>
        <kbd className="text-[10px] bg-gray-100 dark:bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded font-mono">⌘K</kbd>
      </button>

      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <button
          onClick={() => dispatch(toggleTheme())}
          className="btn-ghost p-2 rounded-xl"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark'
            ? <Sun  className="w-4.5 h-4.5" style={{ width: 18, height: 18 }} />
            : <Moon className="w-4.5 h-4.5" style={{ width: 18, height: 18 }} />}
        </button>

        {/* Notifications */}
        <button
          onClick={() => navigate('/notifications')}
          className="btn-ghost p-2 rounded-xl relative"
          title="Notifications"
        >
          <Bell className="w-4.5 h-4.5" style={{ width: 18, height: 18 }} />
          {notifCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-danger-500" />
          )}
        </button>

        {/* User avatar */}
        <div className="flex items-center gap-2 pl-2 border-l border-gray-100 dark:border-gray-800 ml-1">
          <div className="w-8 h-8 rounded-xl bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-bold text-brand-700 dark:text-brand-300">{initials}</span>
          </div>
          <div className="hidden sm:block">
            <p className="text-xs font-semibold text-gray-800 dark:text-gray-200 leading-none">
              {user?.first_name} {user?.last_name}
            </p>
            <p className="text-[10px] text-gray-400 mt-0.5 capitalize">{user?.role?.replace(/_/g, ' ')}</p>
          </div>
          <button
            onClick={() => dispatch(logoutAction())}
            className="btn-ghost p-1.5 ml-1"
            title="Sign out"
          >
            <LogOut className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>
    </header>
  );
}
