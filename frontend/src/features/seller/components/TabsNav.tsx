interface Tab {
  id: string;
  label: string;
  badge?: number;
  badgeVariant?: 'default' | 'warning' | 'danger';
}

interface TabsNavProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export default function TabsNav({ tabs, activeTab, onTabChange }: TabsNavProps) {
  return (
    <div className="border-b border-gray-200 mb-6">
      <nav className="flex gap-1" aria-label="Tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`
              px-4 py-3 text-sm font-medium border-b-2 transition-colors
              ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }
            `}
          >
            <span>{tab.label}</span>
            {tab.badge !== undefined && tab.badge > 0 && (
              <span
                className={`
                  ml-2 px-2 py-0.5 text-xs font-medium rounded-full
                  ${
                    tab.badgeVariant === 'danger'
                      ? 'bg-red-100 text-red-700'
                      : tab.badgeVariant === 'warning'
                      ? 'bg-orange-100 text-orange-700'
                      : 'bg-gray-100 text-gray-700'
                  }
                `}
              >
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}
