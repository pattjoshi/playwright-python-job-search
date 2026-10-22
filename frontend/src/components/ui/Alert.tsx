import styles from "./Alert.module.css";

/** A red message box; renders nothing when there is no message. */
export function Alert({ message, className }: { message: string | null | undefined; className?: string }) {
  if (!message) return null;
  return (
    <div role="alert" className={[styles.alert, className].filter(Boolean).join(" ")}>
      {message}
    </div>
  );
}
