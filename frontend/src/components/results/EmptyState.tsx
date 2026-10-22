import { Card } from "@/components/ui/Card";

import styles from "./EmptyState.module.css";

export function EmptyState() {
  return (
    <Card className={styles.empty}>
      <h2>Your matches will appear here</h2>
      <p>Upload your resume and press Start. Jobs are ranked by how well they fit your skills and experience.</p>
      <div className={styles.how}>
        <div><b>1 · Resume</b><span>Keywords, skills and experience are read automatically.</span></div>
        <div><b>2 · Search</b><span>LinkedIn, Naukri and Indeed, filtered to recent posts.</span></div>
        <div><b>3 · Rank</b><span>Every job gets a match score with matching and missing skills.</span></div>
      </div>
    </Card>
  );
}
