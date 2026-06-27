#!/usr/bin/env node
/**
 * STDD-OMP version checker — manual upgrade helper.
 *
 * Checks:
 * 1. Local skill version (`references/VERSION`)
 * 2. Latest GitHub release version (requires `STDD_OMP_GITHUB_REPO` or `--repo`)
 * 3. Local OMP version (`omp --version`)
 * 4. OMP compatibility requirement (`references/OMP_COMPATIBILITY`)
 *
 * Exit codes:
 *   0  all green
 *   1  runtime error
 *   2  local skill behind remote
 *   3  OMP version incompatible
 *
 * Usage:
 *   node scripts/check-version.mjs
 *   node scripts/check-version.mjs --repo owner/repo
 *   STDD_OMP_GITHUB_REPO=owner/repo node scripts/check-version.mjs
 */
import {
  readLocalVersion,
  checkRemote,
  readOmpVersion,
  readOmpCompatibility,
  checkOmpCompatibility,
} from './orchestrate.mjs';

function compareVersions(local, remote) {
  if (!local || !remote) return 'unknown';
  if (local === remote) return 'synced';
  const parts = [local, remote].map((v) => v.split('.').map(Number));
  for (let i = 0; i < Math.max(parts[0].length, parts[1].length); i++) {
    const a = parts[0][i] || 0;
    const b = parts[1][i] || 0;
    if (a > b) return 'ahead';
    if (a < b) return 'behind';
  }
  return 'synced';
}

function parseArgs(argv) {
  const args = argv.slice(2);
  const opts = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--repo') opts.githubRepo = args[++i];
  }
  return opts;
}

async function main() {
  const opts = parseArgs(process.argv);
  const githubRepo = opts.githubRepo || process.env.STDD_OMP_GITHUB_REPO || process.env.STDD_OMP_REPO;

  const localVersion = readLocalVersion();
  const remote = await checkRemote(githubRepo);
  const syncStatus = remote.version ? compareVersions(localVersion, remote.version) : 'unknown';

  const ompVersion = readOmpVersion();
  const ompRequirement = readOmpCompatibility();
  const ompCompat = checkOmpCompatibility(ompVersion, ompRequirement);

  console.log('STDD-OMP version check');
  console.log('======================');
  console.log(`Skill (local) : ${localVersion || 'unknown'}`);
  console.log(`GitHub repo   : ${remote.repo || 'not configured'}`);
  console.log(`GitHub latest : ${remote.version || remote.error || 'unknown'}`);
  console.log(`Sync status   : ${syncStatus}`);
  console.log(`OMP (local)   : ${ompVersion || 'not detected'}`);
  console.log(`OMP required  : ${ompRequirement}`);
  console.log(`OMP compatible: ${ompCompat.compatible == null ? 'unknown' : ompCompat.compatible ? 'yes' : 'NO'}`);
  if (ompCompat.reason) console.log(`  → ${ompCompat.reason}`);

  if (remote.error) {
    console.error(`\nGitHub check failed: ${remote.error}`);
  }

  let exitCode = 0;
  if (syncStatus === 'behind') {
    console.log('\nAction: local skill is behind remote; run `git pull` or re-install from GitHub.');
    exitCode = 2;
  }
  if (ompCompat.compatible === false) {
    console.log('\nAction: upgrade OMP or install an older skill release.');
    exitCode = 3;
  }
  if (exitCode === 0) {
    console.log('\nAll green.');
  }
  process.exit(exitCode);
}

main().catch((e) => {
  console.error(`Error: ${e.message}`);
  process.exit(1);
});
