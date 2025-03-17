# ras-rm-performance-tests

This repo contains the RASRM performance test load injection application using the Locust framework

## Application and load configuration

The configuration to increase users, master and workers is in `values.yaml`

A script to clean out the database prior to a re-run can be found in `cleanup.sql`

## Running Locust

The `Locust` application is ran from Monday to Friday in the performance environment. These are run via Concourse. 
Concourse will build out performance, deploy the apps, run Locust and then destroys performance. 
Results are recorded and uploaded to the `ras-rm-performance-20220908-locust` GCP bucket. Although theses can be triggered manually 
by adjusting the values of the `performance.yml` in `ras-rm-concourse` repo and running the fly pipeline command. This
approach is fine if you want to test changes to another application but if changes to locust are made, it is better to
deploy them from your local machine so that changes made to locust, can run quickly and results seen quickly.

The following commands can be run from your local machine and ran in either dev or performance. There is also a database
clear down script that needs to be run when Locust needs to be run more than once.

**NOTE**
When using Concourse to run Locust, it will do everything including the uninstall of Locust. When using the Helm command
without Concourse, you will need to run a command separately to uninstall Locust.

### Using Concourse

```
fly --target development execute --config [FILEPATH-FROM-YOUR-LOCAL-MACHINE]/ras-rm-concourse/tasks/helm/deploy/deploy-locust-manually.yaml \
    --input helm=[FILEPATH-FROM-YOUR-LOCAL-MACHINE]/ras-rm-performance-tests/_infra/helm \
    --var NAMESPACE=[TARGET-NAMESPACE] \
    --var PROJECT=[TARGET-PROJECT]\
    --var ENV=[TARGET-ENV] \
    --var CLUSTER=[TARGET-CLUSTER] \
    --var LOCUST_FILE=[LOCUST-CONFIG-FILE].py \
    --var TEST_RESPONDENTS=8 \
    --var LOCUST_USERS=8 \
    --var LOCUST_SPAWN_RATE=1 \
    --var LOCUST_RUN_TIME=60m \
    --var USER_WAIT_TIME_MIN_SECONDS=2 \
    --var USER_WAIT_TIME_MAX_SECONDS=3 \
    --var TASK_SLEEP_TIME=1800 \
    --include-ignored
   ```

### Using helm

```
helm upgrade --install locust [FILEPATH-FROM-YOUR-LOCAL-MACHINE]ras-rm-performance-tests/_infra/helm/locust \
    --namespace [TARGET-NAMESPACE] \
    --set-string gcp.project=[TARGET-PROJECT] \
    --set-string env=[TARGET-ENV] \
    --set-string namespace=[TARGET-NAMESPACE] \
    --set-string locust.loadtest.environment.test_respondents=8 \
    --set-string locust.loadtest.environment.user_wait_time_min_seconds=2
    --set-string locust.loadtest.environment.user_wait_time_max_seconds=3
    --set-string locust.master.environment.LOCUST_USERS=8 \
    --set-string locust.master.environment.LOCUST_SPAWN_RATE=1 \
    --set-string locust.master.environment.LOCUST_RUN_TIME="60m" \
    --set-string locust.loadtest.locust_locustfile=[LOCUST-CONFIG-FILE].py
```

These below commands are to be used when Performance is not the target project

```
    --set-string locust.loadtest.locust_host=http://frontstage.[TARGET-NAMESPACE].svc.cluster.local:9000 \
    --set-string locust.loadtest.environment.case=http://case.[TARGET-NAMESPACE].svc.cluster.local:8080 \
    --set-string locust.loadtest.environment.collection_exercise=http://collection-exercise.[TARGET-NAMESPACE].svc.cluster.local:8080 \
    --set-string locust.loadtest.environment.collection_instrument=http://collection-instrument.[TARGET-NAMESPACE].svc.cluster.local:8080 \
    --set-string locust.loadtest.environment.party=http://party.[TARGET-NAMESPACE].svc.cluster.local:8080 \
    --set-string locust.loadtest.environment.sample=http://sample.[TARGET-NAMESPACE].svc.cluster.local:8080 \
    --set-string locust.loadtest.environment.sample_file_uploader=http://sample-file-uploader.[TARGET-NAMESPACE].svc.cluster.local:8080 \
    --set-string locust.loadtest.environment.survey=http://survey.[TARGET-NAMESPACE].svc.cluster.local:8080
```

Once completed, run:
`helm uninstall locust --namespace [NAMESPACE] --ignore-not-found`

### Database clear down between tests

**NOTE**: The below commands **should** only ever be ran in dev (under your namespace) or in performance.

Firstly, whitelist your IP using the ras commands for the dev or performance. Then get the database for either dev or 
performance credentials:

**DEV**

`export DEV_PASSWORD_DATABASE=$(kubectl get secret [DB-CREDENTIALS] -o json --namespace=[YOUR-NAMESPACE] | jq -r '.data."[PASSWORD-KEY]"' | base64 -d)`

**PERFORMANCE**

`export PERFORMANCE_PASSWORD_[TARGET-SERVICE]=$(kubectl get secret [DB-CREDENTIALS] -o json --namespace=performance | jq -r '.data."[PASSWORD-KEY]"' | base64 -d)`

The above command for performance will need to be replicated for all the schemas affected by the Locust tests. When 
using dev, this will only be a single command.

Once the password(s) have been exported to your local machine, run one of the following:

**DEV**

`psql postgresql://postgres:$DEV_PASSWORD_DATABASE@localhost:5432/ras -U postgres -f [FILEPATH-FROM-YOUR-LOCAL-MACHINE]Services/ras-rm-cucumber/_infra/helm/acceptance-tests/files/[SCRIPT-NAME]`

**PERFORMANCE**

`psql postgresql://[TARGET-SERVICE]:$PERFORMANCE_PASSWORD_[TARGET-SERVICE]@localhost:5432/[TARGET-SCHEMA-NAME] -U postgres -f [FILEPATH-FROM-YOUR-LOCAL-MACHINE]Services/ras-rm-cucumber/_infra/helm/acceptance-tests/files/[SCRIPT-NAME]`

Again, the above commands for will need to be replicated for all the schemas affected by the Locust tests. The scripts 
referenced in the commands can be found in `ras-rm-cucumber`. When using dev, this will only be a single command. The 
scripts that need running during multiple attempts are:

```
database_case_clear.sql
database_reset_oauth.sql
database_reset_party.sql
database_reset_collection_exercise.sql
database_reset_secure_message.sql
database_reset_uaa.sql
database_reset_sample.sql
database_reset_ras_ci.sql (dev only)
```

## Manual Testing

Files in the `standalone-scripts` folder are intended to run manually and can be run using the commands mentioned above. 
They are **not** part of the daily Locust test runs and so are separated from the files within the `locust` subdirectory.