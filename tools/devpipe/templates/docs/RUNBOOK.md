# Runbook

Operations for <<project name>>. Every command here is literal and was run when written.

## 1. Environment

<<operating systems, runtimes and tools with versions (see design/STACK.md); how to install each>>

Steps that need administrator rights are in `setup-prerequisites.sh`; run that once.

## 2. Build, run, install

```sh
<<commands>>
```

## 3. Configuration

| Setting | Where | Default | Meaning |
|---|---|---|---|
| <<name>> | <<file or environment variable>> | <<value>> | <<one line>> |

Secrets: <<where they live; never in the repository>>.

## 4. Logs

<<where logs go and how to read them>>

## 5. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| <<what you see>> | <<why>> | <<command or change>> |

## 6. Working with the pipeline

- Current state: `HANDOFF.md`, `python3 tools/devpipe/run.py status`.
- Run a phase: `python3 tools/devpipe/run.py run --phase N` (commits locally on `phase/NN`, never pushes).
- A blocked ticket leaves `.tickets/.work/<id>/RESCUE.md`; fix it, set `status: todo`, run again.
- Check artifacts: `python3 tools/devpipe/run.py lint all`.

## 7. Release and rollback

<<how a release is cut, and how to go back>>
