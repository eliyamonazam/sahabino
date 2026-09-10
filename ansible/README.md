# ansible

Deployment automation for the Sahabino stack.

## What it does

`playbook.yml` runs four idempotent steps against its target host, in order:

1. Checks whether Docker and the Docker Compose plugin are installed
   (`docker --version` / `docker compose version`); if either is missing,
   installs both via Docker's official apt repository. This install step
   only supports Debian/Ubuntu targets (`ansible_facts.os_family ==
   "Debian"`) - on anything else, the playbook fails with a clear message
   asking for Docker to be installed manually rather than silently doing
   nothing or guessing at a different package manager.
2. Ensures `.env` exists at the repo root, copying it from `.env.example`
   if it's missing - the same logic `scripts/setup.sh` already uses, just
   expressed as an idempotent Ansible task instead of a shell `if`.
3. Installs the repo's local git hooks by running
   `scripts/install-git-hooks.sh`.
4. Brings the stack up with `docker compose up -d --build`.

## Running it

```bash
ansible-playbook -i ansible/inventory.ini ansible/playbook.yml
```

## Target: localhost for now, a real host later

There's no real remote server available yet (a sanctions-related access
issue, unrelated to the project itself), so `inventory.ini` currently
targets `localhost` with `ansible_connection=local` - Ansible runs every
task as a local subprocess instead of connecting over SSH. This isn't a
placeholder that skips real testing: the playbook has actually been run
this way against this machine (see Validation below), exercising the real
`.env`/git-hooks/`docker compose up` logic, just not the Docker-install
block (Docker was already present).

To point this at a real remote host once one is available, only
`inventory.ini` needs to change - the playbook itself is host-agnostic:

```ini
[sahabino]
your-server-hostname-or-ip ansible_user=deploy
```

(plus whatever SSH key/`become` settings that host needs - see Ansible's
own docs for the connection variables that apply to your setup). At that
point the Docker-install block, which is a no-op today because Docker is
already present on this machine, would actually run and get exercised for
the first time on a genuinely bare target.

## Validation

Run today from inside a disposable `docker:27-cli` container (Alpine-based,
ships the Docker CLI and Compose v2 plugin, extended with `apk add
ansible`) with this repo and the host's Docker socket both bind-mounted in,
so `docker compose` inside that container talks to the exact same Docker
Engine - and therefore the exact same already-running containers - as the
host does. This deliberately avoids running `ansible-playbook` against the
real stack from a context that could plausibly do something destructive by
accident.

The stack had been running continuously since Day 7 collecting real data
for later analysis, so the hard constraint for this test was: prove
running the playbook can't lose any of that data. The result has one
important nuance worth being explicit about rather than glossing over:

- **`postgres` and `kafka` - where all the actual data lives - are never
  touched.** Both use a fixed `image:` (not `build:`), so `docker compose
  build` never re-resolves them and `docker compose up -d` never has a
  reason to recreate them. Verified across three separate playbook runs
  today: their container IDs and start timestamps (checked with `docker
  inspect`, not just `docker compose ps`'s coarser "Up X hours") stayed
  byte-identical throughout, and every row in `apps`, `app_stats_snapshots`,
  `reviews`, and `network_metrics` was still present and unchanged
  afterward.
- **The stateless application services (`app-list-api-fastapi`,
  `app-list-api-django`, `playstore-scraper`, `storage-consumer`) *do* get
  recreated on every run that passes `--build`, even when no source file
  changed.** This isn't a config-drift bug in this repo: BuildKit embeds a
  fresh build timestamp in the image config on every build, so even a
  100%-cache-hit build (confirmed directly - `docker compose build
  storage-consumer` on its own showed every layer as `CACHED` and finished
  in under 2 seconds) still produces a new image ID, which is what makes
  `docker compose up -d` correctly recreate the container - its own logic
  ("has the image this container should be running actually changed?") is
  working exactly as designed. Recreating a stateless service - it holds no
  local state, and picks back up immediately - isn't data loss, and is
  arguably the whole point of a deploy playbook: it means a real code
  change would actually get rolled out on the next run. `network-analyzer`
  behaved the same way here since nothing prevents `up -d` from starting it
  too (it just runs `analyzer/main.py` once and exits, same as
  `docker compose run --rm` would, since the dedup-by-`source_file` check
  makes reprocessing the same pcaps a no-op either way).

In short: the "should be a safe no-op" framing this was originally tested
against holds fully for the two services that actually hold state, and the
brief restart of the stateless ones is expected, harmless deploy behavior
rather than the kind of disruption the no-destructive-testing constraint
was protecting against.
