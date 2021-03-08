# ras-rm-performance-tests
Performance Test Scripts

## Running load tests from Spinnaker
### TODO pipeline doesn't work at present
* Check to see if the cluster you're targeting has a locust namespace already. If it does, you won't need to redeploy it unless you've changed the test scripts
* Run the pipeline in the Locust application (if its missing for some reason, save it from the config in this repository). Target the namespace you've deployed frontstage to
* Port-forward to the Locust Master
```bash
kubectl port-forward locust-master-xxxxxxx -n locust 8089
```
* Navigate to [Locust](http://localhost:8089) and check the target host is the one you wanted - it should be for sandbox/dev environments
* Spin up a performance test

## Running load tests by running Helm yourself

**Ensure that you're pointed towards the performance environment before running these tests!**

If one does not exists then create a kubernetes namespace 
```bash
kubectl create namespace locust
```

Install the helm charts for Locust
```bash
helm install locust _infra/helm/locust --namespace locust
```

Port-forward to the Locust Master
```bash
kubectl port-forward locust-master-xxxxxxx 8089
```

Naviagte to [Locust](http://localhost:8089) and spin up a performance test

### Removing Locust

Stop the performance test

Uninstall the helm chart
```bash
helm uninstall locust
```

## Where are the tests?

In `_infra\helm\locust\tasks`

## I need more workers!

In `values.yaml`, change `workers.replicaCount`

## Re-run

To re-run the tests clean out the database using the commands from cleanup.sql