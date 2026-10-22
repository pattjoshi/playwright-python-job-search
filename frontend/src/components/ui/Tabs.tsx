import styles from "./Tabs.module.css";

export interface TabItem {
  id: string;
  name: string;
  count?: number;
}

interface TabsProps {
  tabs: TabItem[];
  selected: string;
  onSelect: (id: string) => void;
  className?: string;
}

export function Tabs({ tabs, selected, onSelect, className }: TabsProps) {
  return (
    <div className={[styles.tabs, className].filter(Boolean).join(" ")} role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id} type="button" role="tab" className={styles.tab}
          aria-selected={tab.id === selected} onClick={() => onSelect(tab.id)}
        >
          {tab.name}
          {tab.count !== undefined ? <span className={styles.count}>{tab.count}</span> : null}
        </button>
      ))}
    </div>
  );
}
