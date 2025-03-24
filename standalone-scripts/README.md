# Stand alone Locust test files

The scripts in this folder are intended to be used when carrying bespoke, point-in-time performance testing. They are intended for controlled, manual deployment and are not intended to be used in automated/scheduled testing.

## How to run the standalone scripts

Locally, move these scripts into the main locust directory (ras-rm-performance-tests/_infra/helm/locust). Once there, follow the instructions in the main README.md (ras-rm-performance-tests/README.md).

**NOTE** when deploying a configMap object of the locustfiles folder, there is a total size limit of ~1BM and if the size of the files in the folder exceeds this it will not fail but cause an empty configMap to be created.
