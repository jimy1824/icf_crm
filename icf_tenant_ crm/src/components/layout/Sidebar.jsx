import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  BarChart2, Bell, BookOpen, Building2, Calculator,
  ChevronDown, ChevronLeft, ChevronRight, ChevronUp,
  CreditCard, FileText, Globe, LayoutDashboard, Map,
  MessageSquare, Palette, Phone, Shield, Target, Ticket, Users, Video,
} from 'lucide-react';
import { setSidebarCollapsed } from '../../store/uiSlice.js';
import { useAuth } from '../../hooks/useAuth.js';

const NAV = [
  { label: 'Dashboard',       path: '/',              icon: LayoutDashboard },
  { label: 'Kanban',          path: '/kanban',         icon: LayoutDashboard },
  { label: 'Leads & Clients',  path: '/leads',          icon: Users },
  { label: 'Campaigns',       path: '/campaigns',      icon: Target },
  { label: 'Communications',  path: '/communications', icon: MessageSquare },
  { label: 'Calls',           path: '/calls',          icon: Phone },
  { label: 'Meetings',        path: '/meetings',       icon: Video },
  { label: 'Calculators',     path: '/calculators',    icon: Calculator },
  { label: 'Analytics',       path: '/analytics',      icon: BarChart2 },
];

const ADMIN_NAV = [
  { label: 'Territories',     path: '/territories',    icon: Map },
  { label: 'Team',            path: '/users',          icon: Users },
];

const COMPANY_NAV = [
  { label: 'Overview',        path: '/company',              icon: Building2 },
  { label: 'Employees',       path: '/company/employees',    icon: Users },
  { label: 'Territories',     path: '/company/territories',  icon: Map },
  { label: 'Permissions',     path: '/company/permissions',  icon: Shield },
  { label: 'Billing',         path: '/company/billing',      icon: CreditCard },
  { label: 'Time Zone',       path: '/company/timezone',     icon: Globe },
  { label: 'Notifications',   path: '/company/notifications',icon: Bell },
  { label: 'Branding',        path: '/company/branding',     icon: Palette },
  { label: 'Support',         path: '/company/support',      icon: Ticket },
];

const BOTTOM_NAV = [
  { label: 'Documents',       path: '/documents',      icon: FileText },
  { label: 'Search',          path: '/search',         icon: BookOpen },
];

function NavItem({ path, icon: Icon, label, collapsed }) {
  return (
    <NavLink
      to={path}
      end={path === '/'}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group
         ${isActive
           ? 'bg-brand-600 text-white shadow-sm'
           : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100'
         }`
      }
      title={collapsed ? label : undefined}
    >
      <Icon className="w-4.5 h-4.5 flex-shrink-0" style={{ width: 18, height: 18 }} />
      {!collapsed && <span className="truncate">{label}</span>}
    </NavLink>
  );
}

function CollapsibleSection({ title, items, collapsed, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);

  if (collapsed) {
    return (
      <>
        {items.map((n) => <NavItem key={n.path} {...n} collapsed={collapsed} />)}
      </>
    );
  }

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 pt-4 pb-1 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
      >
        <span>{title}</span>
        {open
          ? <ChevronUp className="w-3 h-3" />
          : <ChevronDown className="w-3 h-3" />}
      </button>
      {open && items.map((n) => <NavItem key={n.path} {...n} collapsed={collapsed} />)}
    </>
  );
}

export default function Sidebar() {
  const collapsed = useSelector((s) => s.ui.sidebarCollapsed);
  const dispatch = useDispatch();
  const { isFirmAdmin, isTeamLead } = useAuth();
  const showAdmin = isFirmAdmin() || isTeamLead();

  return (
    <aside
      className={`relative flex flex-col h-full bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800
                  shadow-sidebar transition-all duration-200 flex-shrink-0
                  ${collapsed ? 'w-16' : 'w-56'}`}
    >
      {/* Logo */}
      <div className={`flex items-center h-14 border-b border-gray-100 dark:border-gray-800 flex-shrink-0 ${collapsed ? 'justify-center px-2' : 'px-4 gap-2.5'}`}>
        <div className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center flex-shrink-0">
          <Building2 className="w-4.5 h-4.5 text-white" style={{ width: 18, height: 18 }} />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="text-sm font-bold text-gray-900 dark:text-white truncate">ICF Advisor</p>
            <p className="text-[10px] text-gray-400 truncate">CRM Platform</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
        {NAV.map((n) => <NavItem key={n.path} {...n} collapsed={collapsed} />)}

        {showAdmin && (
          <CollapsibleSection title="Admin" items={ADMIN_NAV} collapsed={collapsed} defaultOpen />
        )}

        {showAdmin && (
          <CollapsibleSection title="Company" items={COMPANY_NAV} collapsed={collapsed} defaultOpen={false} />
        )}

        <CollapsibleSection title="Tools" items={BOTTOM_NAV} collapsed={collapsed} defaultOpen />
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => dispatch(setSidebarCollapsed(!collapsed))}
        className="absolute -right-3 top-16 w-6 h-6 rounded-full bg-white dark:bg-gray-800 border
                   border-gray-200 dark:border-gray-700 flex items-center justify-center shadow-sm
                   hover:bg-gray-50 dark:hover:bg-gray-700 z-10 transition-colors"
      >
        {collapsed
          ? <ChevronRight className="w-3 h-3 text-gray-500" />
          : <ChevronLeft  className="w-3 h-3 text-gray-500" />}
      </button>
    </aside>
  );
}
