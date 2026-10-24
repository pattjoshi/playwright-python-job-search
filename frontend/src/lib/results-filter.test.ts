import { describe, expect, it } from "vitest";

import type { Job } from "@/lib/types";

import { companyKey, filterJobs, NO_FILTER, postedAgo } from "./results-filter";

const job = (title: string, company: string, score: number | null, hours_ago: number | null) =>
  ({ title, company, location: "Pune", score, hours_ago, source: "naukri", job_id: title }) as Job;
const jobs = [job("QA Engineer", "Acme Pvt Ltd", 92, 20), job("SDET", "Beta", 70, 2), job("Python Developer", "Gamma", null, null)];

describe("result filters", () => {
  it("matches company names loosely, like the backend", () => {
    expect(companyKey("Acme Technologies Pvt. Ltd.")).toBe("acme");
    expect(companyKey("ACME")).toBe("acme");
  });

  it("filters by score, posted time, words and hidden companies", () => {
    expect(filterJobs(jobs, { ...NO_FILTER, minScore: 80 }, []).shown.map((j) => j.title)).toEqual(["QA Engineer"]);
    expect(filterJobs(jobs, { ...NO_FILTER, maxHours: 6 }, []).shown.map((j) => j.title)).toEqual(["SDET", "Python Developer"]);
    expect(filterJobs(jobs, { ...NO_FILTER, query: "beta sdet" }, []).shown.map((j) => j.title)).toEqual(["SDET"]);
    const hidden = filterJobs(jobs, NO_FILTER, ["acme"]);
    expect(hidden.shown.map((j) => j.company)).toEqual(["Beta", "Gamma"]);
    expect(hidden.left_out).toBe(1);
  });

  it("sorts by best match, newest or company", () => {
    expect(filterJobs(jobs, NO_FILTER, []).shown.map((j) => j.title)).toEqual(["QA Engineer", "SDET", "Python Developer"]);
    expect(filterJobs(jobs, { ...NO_FILTER, sort: "newest" }, []).shown.map((j) => j.title)).toEqual(["SDET", "QA Engineer", "Python Developer"]);
    expect(filterJobs(jobs, { ...NO_FILTER, sort: "company" }, []).shown[0].company).toBe("Acme Pvt Ltd");
  });

  it("says when a job was posted", () => {
    expect(postedAgo(0.5)).toBe("just now");
    expect(postedAgo(3)).toBe("3 hours ago");
    expect(postedAgo(72)).toBe("3 days ago");
    expect(postedAgo(null)).toBe("");
  });
});
