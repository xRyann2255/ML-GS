"""Fetch GitLab pipeline and job info via REST API.

Replaces fetch-pipeline.ps1 + gitlab-auth.ps1 — uses PAT auth instead of SAML.

Usage: fetch_pipeline.py --args-file path/to/args.json

Args JSON:
  {
    "project_id": 117719,
    "pipeline_id": 0,
    "ref": "main",
    "include_trace": false,
    "out_dir": ""
  }
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
from gitlab_auth import get_gitlab_headers, gitlab_api, GITLAB_BASE  # noqa: E402


def fetch_pipeline(project_id, pipeline_id=0, ref="main", include_trace=False,
                   out_dir="", gitlab_base=GITLAB_BASE):
    headers = get_gitlab_headers()
    api_base = f"/projects/{project_id}"

    # Resolve output dir
    if not out_dir:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                  "..", "..", ".."))
        out_dir = os.path.join(repo_root, "workspace", "tmp")
    os.makedirs(out_dir, exist_ok=True)

    # Get pipeline
    if pipeline_id == 0:
        print(f"Fetching latest pipeline for ref={ref} ...")
        pipelines = gitlab_api(f"{api_base}/pipelines?ref={ref}&per_page=1",
                               headers=headers, base=gitlab_base)
        if not pipelines:
            print(f"WARNING: No pipelines found for ref={ref}")
            return
        pipeline_id = pipelines[0]["id"]

    print(f"Pipeline ID: {pipeline_id}")
    pipeline = gitlab_api(f"{api_base}/pipelines/{pipeline_id}",
                          headers=headers, base=gitlab_base)

    pipeline_file = os.path.join(out_dir, f"gitlab-pipeline-{pipeline_id}.json")
    with open(pipeline_file, "w", encoding="utf-8") as f:
        json.dump(pipeline, f, indent=2, ensure_ascii=False)
    print(f"Pipeline status: {pipeline.get('status')}")
    print(f"Saved: {pipeline_file}")

    # Get jobs
    print("Fetching jobs ...")
    jobs = gitlab_api(f"{api_base}/pipelines/{pipeline_id}/jobs?per_page=100",
                      headers=headers, base=gitlab_base)

    jobs_file = os.path.join(out_dir, f"gitlab-pipeline-{pipeline_id}-jobs.json")
    with open(jobs_file, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"Jobs: {len(jobs)}")
    print(f"Saved: {jobs_file}")

    for job in jobs:
        status = job.get("status", "?")
        reason = f" ({job['failure_reason']})" if job.get("failure_reason") else ""
        runner = (f" runner={job['runner']['description']}"
                  if job.get("runner") else "")
        print(f"  [{status}] {job.get('name', '?')}{reason}{runner}")

        # Download trace for failed jobs
        if include_trace and status == "failed":
            print("    Downloading trace ...")
            try:
                trace = gitlab_api(f"{api_base}/jobs/{job['id']}/trace",
                                   headers=headers, base=gitlab_base)
                trace_file = os.path.join(out_dir,
                                          f"gitlab-job-{job['id']}-trace.txt")
                text = trace if isinstance(trace, str) else json.dumps(trace)
                with open(trace_file, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"    Saved: {trace_file}")
            except Exception as e:
                print(f"    WARNING: Could not download trace: {e}")

    # Summary
    failed = [j for j in jobs if j.get("status") == "failed"]
    if failed:
        print(f"\n{len(failed)} failed job(s):")
        for j in failed:
            print(f"  - {j.get('name')}: {j.get('failure_reason')}")
    else:
        print("\nAll jobs passed.")


def main():
    parser = argparse.ArgumentParser(description="GitLab Pipeline Fetch")
    parser.add_argument("--args-file", required=True)
    args = parser.parse_args()

    with open(args.args_file, encoding="utf-8") as f:
        a = json.load(f)

    fetch_pipeline(
        project_id=int(a["project_id"]),
        pipeline_id=int(a.get("pipeline_id", 0) or 0),
        ref=a.get("ref", "main") or "main",
        include_trace=bool(a.get("include_trace", False)),
        out_dir=a.get("out_dir", "") or "",
        gitlab_base=a.get("gitlab_base", GITLAB_BASE) or GITLAB_BASE,
    )


if __name__ == "__main__":
    main()
