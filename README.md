# ras-rm-performance-tests
Performance Test Scripts


## Running load tests

**Ensure that you're pointed towards the correct (non-prod) environment before running these tests!**

Install the helm charts for Locust
```bash
helm install _infra/helm/locust locust
```

Port-forward to the Locust Master
```bash
kubectl port-forward locust-master-xxxxxxx 8089
```

Naviagte to [Locust](http://localhost:8089) and spin up a performance test

## Removing Locust

Stop the performance test

Uninstall the helm chart
```bash
helm uninstall locust
```