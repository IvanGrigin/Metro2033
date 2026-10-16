"""Kling generations from a scene's pack, with measurements. Spends the user's credits: run only after the critic agreed
the prompts and the user said yes to this batch.
    python3 storyboard/tools/kling_gen.py submit 1 1.02 1.22 1.28   # one omni_ref_video job per shot, Blender clip as 视频1
    python3 storyboard/tools/kling_gen.py submit 1/seq seq01_1.02-1.07  # a multi-shot chunk from kling_seq.py
    python3 storyboard/tools/kling_gen.py fetch                      # finished jobs: download, write the ledger row
Jobs live in storyboard/kling/jobs.json; every finished job is one row in storyboard/kling/LEDGER.csv."""
import csv, json, math, os, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KL = os.path.join(ROOT, "kling")
JOBS = os.path.join(KL, "jobs.json")
MODEL, RES = "kling-video-v4_0", "720p"
FLOOR = int(os.environ.get("KLING_FLOOR", "0"))  # never let the balance drop below this (the user's daily cap)
PER_SEC = 11  # credits per output second, measured on seq01 (151 for 14 s out + 14 s in)  # critic: 720p for the trial; 1080p is the user's call


def kling(*a):
    r = subprocess.run(["kling", *a], capture_output=True, text=True)
    out = json.loads(r.stdout or "{}")
    if not out.get("ok"):
        sys.exit(f"kling {a[0]} failed: {r.stdout[-800:]} {r.stderr[-800:]}")
    return out["body"]


def credits():
    return kling("account")["availableRemainCredits"]


def submit(where, shots):
    n, _, sub = where.partition("/")  # "1" = per-shot pack, "1/seq" = multi-shot chunks
    n, d = int(n), os.path.join(KL, f"s{int(n):03d}", sub)
    rows = {r.get("shot") or r["chunk"]: r for r in json.load(open(os.path.join(d, "prompts.json")))}
    jobs = json.load(open(JOBS)) if os.path.exists(JOBS) else []
    for sid in shots:
        r = rows[sid]
        sec = r.get("duration") or max(3, math.ceil(r["seconds"] - 0.01))  # output as long as the reference (min 3 s): timing 1:1
        attempt = 1 + sum(j["shot"] == sid for j in jobs)
        before = credits()
        if before - sec * PER_SEC < FLOOR:
            sys.exit(f"{sid}: ~{sec * PER_SEC} credits would take the balance {before} below the cap floor {FLOOR}; not sent")
        b = kling("omni_ref_video", "--model", MODEL, "--video", os.path.join(d, r["clip"]),
                  "--duration", str(sec), "--resolution", RES, "--enable_audio", "false", "--keepOriginalSound", "false",
                  "--imageCount", "1", *(["--elements", json.dumps(r["elements"])] if r.get("elements") else []),
                  "--prompt", r["prompt"])
        jobs.append({"scene": n, "shot": sid, "attempt": attempt, "seconds": sec, "id": b["generationId"],
                     "consumed": b.get("creditsConsumed"), "before": before, "after": credits(), "t0": time.time(),
                     "input": r["clip"], "note": r.get("note", ""), "done": False})
        print(sid, "submitted", b["generationId"], "credits", b.get("creditsConsumed"), flush=True)
        json.dump(jobs, open(JOBS, "w"), ensure_ascii=False, indent=1)


def fetch():
    jobs = json.load(open(JOBS))
    with open(os.path.join(KL, "LEDGER.csv"), "a", newline="") as f:
        w = csv.writer(f)
        for j in jobs:
            if j["done"]:
                continue
            b = kling("query_tasks", j["id"])
            st = str(b.get("status", "")).upper()
            if st not in ("COMPLETED", "PARTIAL_COMPLETED", "SUCCEED", "FAILED", "CANCELLED"):
                print(j["shot"], st, flush=True)
                continue
            out = ""
            work = next((x for x in b.get("works", []) if x.get("contentType") == "video"), None)
            if work:
                gd = os.path.join(KL, f's{j["scene"]:03d}', "gen")
                os.makedirs(gd, exist_ok=True)
                out = os.path.join(gd, f'{j["shot"]}_a{j["attempt"]}.mp4')
                urllib.request.urlretrieve(work.get("urlWithoutWatermark") or work["url"], out)
            mins = ((b.get("finishTime") or 0) - (b.get("createTime") or 0)) / 60000
            spent = j["before"] - j["after"]
            w.writerow([time.strftime("%Y-%m-%d"), time.strftime("%H:%M"), j["scene"], j["shot"], j["attempt"],
                        "cli omni_ref_video", MODEL, f"{RES} audio off", j["seconds"], j["before"], j["after"], spent,
                        round(mins, 1), j["input"], os.path.relpath(out, ROOT) if out else "", "",
                        f'{st}; creditsConsumed {j["consumed"]}; id {j["id"]}; {j["note"]}'])
            j["done"] = True
            print(j["shot"], st, out, "spent", spent, flush=True)
    json.dump(jobs, open(JOBS, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    if sys.argv[1] == "submit":
        submit(sys.argv[2], sys.argv[3:])
    else:
        fetch()
