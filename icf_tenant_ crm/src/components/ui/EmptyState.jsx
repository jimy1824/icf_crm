export default function EmptyState({ icon: Icon, title, subtitle, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {Icon && (
        <div className="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
          <Icon className="w-7 h-7 text-gray-400 dark:text-gray-500" />
        </div>
      )}
      <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">{title}</p>
      {subtitle && <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 max-w-xs">{subtitle}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
