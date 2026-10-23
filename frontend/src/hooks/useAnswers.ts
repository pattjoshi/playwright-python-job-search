"use client";

import { useCallback, useEffect, useState } from "react";

import { answersApi } from "@/lib/api/endpoints";
import type { Answer, AnswerInput } from "@/lib/types";

/** The Answer Bank's questions: load, add, edit, approve, delete, and the bulk actions. */
export function useAnswers() {
  const [items, setItems] = useState<Answer[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    answersApi.list()
      .then((body) => !cancelled && setItems(body.answers))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const reload = useCallback(async () => {
    try {
      setItems((await answersApi.list()).answers);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  const replace = useCallback((answer: Answer) => {
    setItems((current) => (current ?? []).map((item) => (item.id === answer.id ? answer : item)));
    return answer;
  }, []);

  const create = useCallback(async (input: AnswerInput) => {
    const { answer } = await answersApi.create(input);
    setItems((current) => [...(current ?? []), answer]);
    return answer;
  }, []);

  const update = useCallback(async (id: number, input: AnswerInput) => replace((await answersApi.update(id, input)).answer), [replace]);
  const approve = useCallback(async (id: number) => replace((await answersApi.approve(id)).answer), [replace]);

  const remove = useCallback(async (id: number) => {
    await answersApi.remove(id);
    setItems((current) => (current ?? []).filter((item) => item.id !== id));
  }, []);

  return { items, error, reload, create, update, approve, remove };
}

export type AnswersApi = ReturnType<typeof useAnswers>;
