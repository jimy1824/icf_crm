import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Bell, Calendar, ChevronLeft, ChevronRight, FileText,
  LayoutDashboard, LogOut, MessageSquare, Settings, Shield, Target, User,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext.jsx';
import { useQuery } from '@tanstack/react-query';
import { getNotifications } from '../../api/portal.js';

const STATUS_LABELS = {
  new: 'New Lead',
  contacted: 'Contacted',
  qualified: 'Qualified',
  in_discussion: 'In Discussion',
  proposal_sent: 'Proposal Sent',
  prospect: 'Prospect',
  client: 'Active Client',
  former_client: 'Former Client',
};

const STATUS_COLORS = {
  client: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  prospect: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  former_client: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
};

function StatusBadge({ status }) {
  const label = STATUS_LABELS[status] ?? status ?? 'Lead';
  const color = STATUS_COLORS[status] ?? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${color}`}>
      {label}
    </span>
  );
}

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/advisor', label: 'My Advisor', icon: User },
  { to: '/messages', label: 'Messages', icon: MessageSquare },
  { to: '/meetings', label: 'Meetings', icon: Calendar },
  { to: '/goals', label: 'Goals', icon: Target },
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/notifications', label: 'Notifications', icon: Bell, badge: true },
  { to: '/profile', label: 'Profile', icon: User },
  { to: '/preferences', label: 'Preferences', icon: Settings },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  // Fetch unread notification count
  const { data: notifData } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: () => getNotifications({ is_read: false }),
    refetchInterval: 60_000,
  });
  const unreadCount = notifData?.count ?? notifData?.results?.length ?? 0;

  function handleLogout() {
    logout();
    navigate('/login');
  }

  const initials = `${user?.first_name?.[0] ?? ''}${user?.last_name?.[0] ?? ''}`.toUpperCase() || 'U';

  return (
    <aside
      className={`${collapsed ? 'w-[64px]' : 'w-[240px]'} flex-shrink-0 bg-gray-900 text-gray-300 flex flex-col
        h-full transition-[width] duration-200 ease-in-out z-10 overflow-hidden`}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-white/5 flex-shrink-0">
        <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
          <Shield className="w-4 h-4 text-white" />
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold text-white whitespace-nowrap">ICF Client Portal</span>
        )}
      </div>

      {/* User identity */}
      {!collapsed && user && (
        <div className="px-4 py-3 border-b border-white/5 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
              {initials}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user.first_name} {user.last_name}
              </p>
              <div className="mt-0.5">
                <StatusBadge status={user.status} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto overflow-x-hidden">
        {NAV.map(({ to, label, icon: Icon, exact, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 mx-2 px-3 py-2.5 rounded-lg text-sm font-medium
               transition-colors duration-150 mb-0.5 ${
                 isActive
                   ? 'bg-brand-600 text-white'
                   : 'text-gray-400 hover:bg-white/5 hover:text-white'
               }`
            }
          >
            <div className="relative flex-shrink-0">
              <Icon className="w-4 h-4" />
              {badge && unreadCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 bg-red-500 text-white text-[8px] font-bold rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </div>
            {!collapsed && <span className="truncate flex-1">{label}</span>}
            {!collapsed && badge && unreadCount > 0 && (
              <span className="ml-auto bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </NavLink>
        ))}

        {/* Divider */}
        <div className="border-t border-white/5 mx-2 my-2" />

        {/* Sign out */}
        <button
          onClick={handleLogout}
          title={collapsed ? 'Sign Out' : undefined}
          className="flex items-center gap-3 w-full mx-2 px-3 py-2.5 rounded-lg text-sm font-medium
                     text-gray-400 hover:bg-white/5 hover:text-red-400 transition-colors duration-150"
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {!collapsed && <span>Sign Out</span>}
        </button>
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-white/5 p-3 flex-shrink-0">
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center justify-center w-full py-2 rounded-lg text-gray-500
                     hover:bg-white/5 hover:text-white transition-colors duration-150"
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && <span className="ml-2 text-xs">Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
