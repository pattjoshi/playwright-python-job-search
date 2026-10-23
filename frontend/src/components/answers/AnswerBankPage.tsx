"use client";

import { Plus, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnswers } from "@/hooks/useAnswers";
import { answersApi } from "@/lib/api/endpoints";
import type { Answer, AnswerInput } from "@/lib/types";
import { useConfig } from "@/providers/ConfigProvider";
import { useSearchSession } from "@/providers/SearchSessionProvider";

import { AnswerFormDialog } from "./AnswerFormDialog";
import { AnswerGroup } from "./AnswerGroup";
import { AnswersEmpty } from "./AnswersEmpty";
import { type AnswerTab, AnswersToolbar } from "./AnswersToolbar";
import { CATEGORIES, countByStatus, firstTab, matchesSearch } from "./meta";
import { TryQuestionCard } from "./TryQuestionCard";

const EMPTY_TAB: Record<AnswerTab, string> = {
  needs_answer: "Nothing needs your answer right now.",
  needs_review: "No AI drafts waiting for review.",
  answered: "No answers yet.",
  all: "No questions match.",
};

/** The Answer Bank: questions forms ask, your answers, AI drafts to review, and new questions to answer. */
export function AnswerBankPage() {
  const { config } = useConfig();
  const { resumeApi } = useSearchSession();
  const { items, error, reload, create, update, approve, remove } = useAnswers();
  const [chosenTab, setTab] = useState<AnswerTab | null>(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [editing, setEditing] = useState<Answer | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const counts = useMemo(() => countByStatus(items ?? []), [items]);
  const tab = chosenTab ?? firstTab(counts);
  const groups = useMemo(() => {
    const shown = (items ?? []).filter((item) =>
      (tab === "all" || item.status === tab) && (!category || item.category === category) && matchesSearch(item, query));
    return CATEGORIES.map((c) => ({ ...c, items: shown.filter((item) => item.category === c.id) })).filter((g) => g.items.length);
  }, [items, tab, category, query]);
  const canFill = config.has_api_key && !!resumeApi.resume;

  const openForm = (item: Answer | null) => {
    setEditing(item);
    setFormOpen(true);
  };

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    try {
      await action();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const fillFromResume = () => run(async () => {
    const { filled } = await answersApi.fillFromResume();
    await reload();
    if (!filled) {
      toast("Your resume doesn't answer any of the open questions");
      return;
    }
    toast.success(`Filled ${filled} answer${filled === 1 ? "" : "s"} from your resume`, { description: "Check them in Needs review." });
    setTab("needs_review");
  });

  const addStarters = () => run(async () => {
    const { added } = await answersApi.addStarters();
    await reload();
    toast.success(`Added ${added} common questions`);
    setTab(null);
    if (canFill) await fillFromResume();
  });

  const save = async (input: AnswerInput) => {
    if (editing) {
      await update(editing.id, input);
      toast.success("Question saved");
    } else {
      await create(input);
      toast.success("Question added");
    }
  };

  const saveAnswer = async (item: Answer, answer: string) => {
    try {
      await update(item.id, { answer });
      toast.success(answer ? "Answer saved" : "Answer cleared");
    } catch (err) {
      toast.error((err as Error).message);
    }
  };

  const approveDraft = async (item: Answer) => {
    try {
      await approve(item.id);
      toast.success("Answer approved");
    } catch (err) {
      toast.error((err as Error).message);
    }
  };

  const destroy = async (item: Answer) => {
    try {
      await remove(item.id);
      toast("Question deleted");
    } catch (err) {
      toast.error((err as Error).message);
    }
  };

  return (
    <>
      <PageHeader
        title="Answer Bank"
        description="Your answers to the questions application forms ask. Auto-apply reuses them, and adds questions it can't answer here for you."
        actions={
          <>
            <Button
              variant="outline" onClick={fillFromResume} disabled={busy || !canFill}
              title={canFill ? undefined : "Needs your resume on the Search jobs page and an OpenAI key"}
            >
              <Sparkles /> Fill from resume
            </Button>
            <Button onClick={() => openForm(null)}><Plus /> Add question</Button>
          </>
        }
      />
      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}
      {!items && !error ? <Skeleton className="h-64" /> : null}
      {items && !items.length ? <AnswersEmpty busy={busy} canFill={canFill} onStarters={addStarters} onAdd={() => openForm(null)} /> : null}
      {items?.length ? (
        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="min-w-0">
            <AnswersToolbar
              tab={tab} onTab={setTab} counts={counts} query={query} onQuery={setQuery} category={category} onCategory={setCategory}
            />
            <div className="grid grid-cols-1 gap-6">
              {groups.map((group) => (
                <AnswerGroup
                  key={group.id} label={group.label} items={group.items}
                  onSave={saveAnswer} onApprove={approveDraft} onEdit={openForm} onDelete={destroy}
                />
              ))}
              {!groups.length ? <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">{EMPTY_TAB[tab]}</p> : null}
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4 lg:sticky lg:top-20">
            <TryQuestionCard onDone={reload} />
          </div>
        </div>
      ) : null}
      <AnswerFormDialog open={formOpen} onOpenChange={setFormOpen} item={editing} onSave={save} />
    </>
  );
}
