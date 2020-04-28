# ras-rm-performance-tests
Performance Test Scripts

## Running load tests

**Ensure that you're pointed towards the correct (non-prod) environment before running these tests!**

Change `values.yaml` to point at the right namespace (this will be handled for you once Spinnakered)

Install the helm charts for Locust
```bash
helm install locust _infra/helm/locust
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

## Where are the tests?

In `_infra\helm\locust\tasks\tasks.py` - this is a specific location mounted by the helm chart. We can set up a configmap in the future to change this.

## I need more workers!

In `values.yaml`, change `workers.replicaCount`

## Credits

Forked from [the stable Helm charts](https://github.com/helm/charts/tree/master/stable/locust)