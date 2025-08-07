# Email Verification Helm Chart

This Helm chart deploys an automated Email Verification app into a Kubernetes cluster. It is intended to be used in the performance tests.

Currently, this is a functional POC with no real logging or exception handling. But it does work as can be seen if you look at the Fronstage logs in your env.

**NOTE:** Ensure the subscription has been edited from `Push` (Cloud Function) to `Pull` or this script won't be able to subscribe to the Pub/Sub topic.

```bash
helm uninstall email-verification --namespace <NAMESPACE>
helm upgrade --install email-verification <YOUR_PATH>/ras-rm-performance-tests/_infra/helm/email-verification \
   --namespace <NAMESPACE> \
   --set-string env.GOOGLE_CLOUD_PROJECT="ras-rm-dev" \
   --set-string env.PUBSUB_SUBSCRIPTION_ID="gcf-ras-rm-notify-<NAMESPACE>-europe-west2-ras-rm-notify-<NAMESPACE>" \
   --set-string env.TIMEOUT_SECONDS=1800
```
