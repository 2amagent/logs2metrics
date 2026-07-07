# log-triage Helm chart

Deploys the log-triage service to a production Kubernetes cluster: a single-replica
Deployment backed by a PVC (SQLite + Drain3 state), an optional S3-compatible
archival backend, and optional Ingress / Prometheus Operator ServiceMonitor.

## Archival is opt-in

`objectStore.backend` defaults to `none` — the service still clusters, counts,
and exposes metrics with no object storage configured at all. Enable `s3` only
if you want the per-line archive (original fields + `cluster_id` + resolved
`severity`/`muted`) on top of whatever your log transporter already ships to
its own destination. See the main project README for what that archive gives
you that transporter-native shipping doesn't (a categorized, per-line audit
trail — useful for later analysis, compliance, or feeding an AI categorization
agent examples; not needed if you only care about raw log durability).

## Why single-replica

The app has one background worker thread that owns Drain3's clustering state and
the SQLite template store — this is a deliberate single-writer design (see the
main project README). Running more than one replica would have two processes
racing on the same PVC-backed SQLite file and Drain3 persistence file, corrupting
both. `replicaCount` defaults to `1` and the Deployment uses `strategy.type:
Recreate` so a rolling update never briefly runs two pods against the same
ReadWriteOnce volume.

Do not scale this chart horizontally until a future release adds Redis-backed
Drain3 persistence and an external database.

## Installation

1. Add/update dependencies as needed, or install directly from a cloned repo:

   ```
   helm install log-triage ./charts/log-triage
   ```

2. If you want the archival backend enabled, create the S3 credentials secret
   ahead of install (recommended over inline values so credentials never touch
   `values.yaml`) — skip this step entirely if leaving `objectStore.backend: none`:

   ```
   kubectl create secret generic log-triage-s3-creds \
     --from-literal=accessKeyId=<key> \
     --from-literal=secretAccessKey=<secret>
   ```

3. Copy `values-production.yaml.example` to `values-production.yaml` and fill in:
   - `persistence.storageClassName` for your cluster
   - `ingress.hosts` if exposing the API externally
   - If enabling archival: `objectStore.backend: s3`, `.s3.bucket`, `.region`,
     `.endpoint` (leave blank for real AWS S3; set for MinIO or another
     S3-compatible provider), and `.s3.existingSecret: log-triage-s3-creds`

4. Install:

   ```
   helm install log-triage ./charts/log-triage \
     -f values-production.yaml \
     -n log-triage --create-namespace
   ```

5. Verify:

   ```
   kubectl -n log-triage rollout status deployment/log-triage
   kubectl -n log-triage port-forward svc/log-triage 8000:8000
   curl localhost:8000/healthz
   curl localhost:8000/readyz
   ```

6. If your cluster runs kube-prometheus-stack / the Prometheus Operator, set
   `serviceMonitor.enabled: true` and `serviceMonitor.labels` to match your
   Prometheus's `serviceMonitorSelector`, then confirm the target appears on
   Prometheus's Targets page.

## Upgrades

```
helm upgrade log-triage ./charts/log-triage -f values-production.yaml -n log-triage
```

The PVC persists across upgrades — SQLite and Drain3 state survive a rollout.
Changing `persistence.size` does **not** automatically resize the PVC; Helm
does not grow or shrink existing PersistentVolumeClaims on upgrade. To resize,
your StorageClass must have `allowVolumeExpansion: true`, and you then edit the
PVC's `spec.resources.requests.storage` directly (`kubectl edit pvc ...`) or
recreate it if the StorageClass doesn't support expansion.

## Uninstall

```
helm uninstall log-triage -n log-triage
```

This does **not** delete the PVC — PersistentVolumeClaims created by a chart are
not owned by the Helm release by default, so data survives an accidental
uninstall. To actually delete the data:

```
kubectl -n log-triage delete pvc log-triage-data
```

## Values reference

See `values.yaml` for the full set of defaults and inline comments. Key sections:

| Key | Purpose |
|---|---|
| `replicaCount` | Fixed at 1 — see "Why single-replica" above |
| `image.pullSecretName` | Name of an existing `kubernetes.io/dockerconfigjson` Secret for pulling from a private registry. Blank = no `imagePullSecrets` on the pod |
| `persistence.*` | PVC size/storageClass for `/data` (SQLite + Drain3 state) |
| `objectStore.s3.*` | Archival bucket, region, endpoint, credentials |
| `config.*` | Mirrors `config.example.yaml` in the app repo |
| `drain3.*` | Similarity threshold / depth / max children rendered into `drain3.ini` |
| `ingress.*` | Optional external exposure |
| `serviceMonitor.*` | Optional Prometheus Operator scrape config |
| `resources.*` | The worker thread is single-core CPU-bound — one core is the practical ceiling regardless of `limits.cpu` |
