import { useQuery } from '@tanstack/react-query';
import { Shield, Check } from 'lucide-react';
import { getRoles, getPermissions } from '../../api/company.js';
import PageHeader from '../../components/ui/PageHeader.jsx';

const ROLE_COLORS = {
  tenant_admin: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  team_lead: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  advisor: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
};

const PERMISSION_GROUPS = {
  'Leads': ['leads.view_own', 'leads.view_all', 'leads.create', 'leads.edit', 'leads.assign', 'leads.delete'],
  'Clients / Financials': ['financials.view', 'financials.edit', 'documents.view', 'documents.upload'],
  'Campaigns': ['campaigns.view', 'campaigns.manage'],
  'Communications': ['communications.view', 'communications.send'],
  'Analytics': ['analytics.view_own', 'analytics.view_firm'],
  'Users / Admin': ['users.manage', 'users.invite', 'territories.manage', 'billing.view'],
};

export default function CompanyPermissionsPage() {
  const { data: roles, isLoading: rolesLoading } = useQuery({
    queryKey: ['company-roles'],
    queryFn: getRoles,
  });

  const { data: allPerms, isLoading: permsLoading } = useQuery({
    queryKey: ['company-permissions'],
    queryFn: getPermissions,
  });

  const isLoading = rolesLoading || permsLoading;

  const roleList = roles ?? [];
  const permList = allPerms ?? [];

  // Build lookup: role slug → Set of permission codenames
  const rolePermMap = {};
  for (const role of roleList) {
    rolePermMap[role.slug] = new Set((role.permissions ?? []).map((p) => p.codename));
  }

  return (
    <div>
      <PageHeader
        title="Roles &amp; Permissions"
        subtitle="View which capabilities each role grants"
        icon={Shield}
      />

      {isLoading ? (
        <div className="card p-6 mt-5">
          <div className="skeleton h-6 w-1/3 rounded mb-4" />
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton h-4 rounded w-full" />)}
          </div>
        </div>
      ) : (
        <div className="card overflow-hidden mt-5">
          {/* Role header chips */}
          <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex items-center gap-3 flex-wrap">
            <span className="text-xs text-gray-500 font-medium">Roles:</span>
            {roleList.map((role) => (
              <span
                key={role.id}
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${ROLE_COLORS[role.slug] ?? 'bg-gray-100 text-gray-700'}`}
              >
                {role.name}
              </span>
            ))}
          </div>

          {/* Permission matrix */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-700">
                  <th className="text-left px-5 py-3 text-gray-500 font-semibold w-64">Permission</th>
                  {roleList.map((role) => (
                    <th key={role.id} className="text-center px-4 py-3 text-gray-500 font-semibold whitespace-nowrap">
                      {role.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
                {Object.entries(PERMISSION_GROUPS).map(([groupName, codenames]) => {
                  // filter to only codenames that exist in the DB
                  const existing = codenames.filter((c) => permList.some((p) => p.codename === c));
                  if (existing.length === 0) return null;
                  return (
                    <>
                      <tr key={groupName} className="bg-gray-50/80 dark:bg-gray-800/30">
                        <td colSpan={roleList.length + 1} className="px-5 py-2 font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                          {groupName}
                        </td>
                      </tr>
                      {existing.map((codename) => (
                        <tr key={codename} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/40">
                          <td className="px-5 py-2.5 text-gray-700 dark:text-gray-200 font-mono">
                            {codename}
                          </td>
                          {roleList.map((role) => (
                            <td key={role.id} className="px-4 py-2.5 text-center">
                              {rolePermMap[role.slug]?.has(codename) ? (
                                <Check className="w-4 h-4 text-green-500 mx-auto" />
                              ) : (
                                <span className="text-gray-200 dark:text-gray-700">—</span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>

          {roleList.length === 0 && (
            <div className="px-5 py-10 text-center text-sm text-gray-400">
              No roles found. Roles are seeded when the first tenant admin is created.
            </div>
          )}
        </div>
      )}

      <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
        <p className="text-xs text-blue-700 dark:text-blue-300">
          Permissions are managed by the platform. Role assignments are done in the Employees tab.
          Contact your ICF account manager to request changes to role capabilities.
        </p>
      </div>
    </div>
  );
}
