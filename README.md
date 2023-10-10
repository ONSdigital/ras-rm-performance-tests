# ras-rm-performance-tests

This repo contains the RASRM performance test load injection application using the Locust framework 

## Running load tests from Spinnaker

The `Locust` application is deployed by Spinnaker in the `performance environment setup` pipeline. This runs the performance tests against the performance environment.

The Locust test script is `_infra/helm/locust/locustfiles/locustfile.py`

## Application and load configuration

The configuration to increase users, master and workers is in `values.yaml`

A script to clean out the database prior to a re-run can be found in `cleanup.sql`
