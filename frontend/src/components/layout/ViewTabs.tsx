interface ViewTabsProps {
  tabs: string[];
  activeTab: string;
  onChange: (tab: string) => void;
}

export function ViewTabs({ tabs, activeTab, onChange }: ViewTabsProps) {
  return (
    <div className="flex gap-4 px-4 border-b border-glass-border">
      {tabs.map(tab => (
        <button
          key={tab}
          onClick={() => onChange(tab)}
          className={`
            px-5 py-3 text-base font-medium relative transition-colors duration-normal
            ${activeTab === tab ? 'text-accent-blue' : 'text-text-secondary hover:text-text-primary'}
          `}
        >
          {tab}
          <div className={`
            absolute bottom-[-1px] left-0 right-0 h-[2px] bg-accent-blue transition-transform duration-normal origin-left
            ${activeTab === tab ? 'scale-x-100' : 'scale-x-0'}
          `} />
        </button>
      ))}
    </div>
  );
}
