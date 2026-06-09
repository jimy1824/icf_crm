import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  BarChart3, Building2, ChevronLeft, ChevronRight, CreditCard, FileText,
  LayoutDashboard, ScrollText, Settings, ShieldCheck, Ticket, Users,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext.jsx';

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/tenants', label: 'Tenants', icon: Building2, roles: ['super_admin', 'support'] },
  { to: '/plans', label: 'Plans', icon: Settings, roles: ['super_admin'] },
  { to: '/billing', label: 'Billing', icon: CreditCard, roles: ['super_admin'] },
  { to: '/support', label: 'Support', icon: Ticket, roles: ['super_admin', 'support'] },
  { to: '/employees', label: 'Employees', icon: Users, roles: ['super_admin'] },
  { to: '/audit', label: 'Audit Log', icon: ScrollText },
  { to: '/analytics', label: 'Analytics', icon: BarChart3, roles: ['super_admin', 'support'] },
];

export default function Sidebar() {
  const { user } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`${collapsed ? 'w-[64px]' : 'w-[220px]'} flex-shrink-0 bg-gray-900 text-gray-300 flex flex-col
        h-full transition-[width] duration-200 ease-in-out z-10 overflow-hidden`}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-white/5 flex-shrink-0">
        <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
          <ShieldCheck className="w-4 h-4 text-white" />
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold text-white whitespace-nowrap">ICF Super Panel</span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto overflow-x-hidden">
        {NAV.map(({ to, label, icon: Icon, roles, exact }) => {
          if (roles && !roles.includes(user?.role)) return null;
          return (
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
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </NavLink>
          );
        })}
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
