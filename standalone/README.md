### Standalone API test approach

This is an initial manual approach for testing APIs in a development environment. It will be extended and automated in due course

ensure your GCP account is authenticated and get the GKE cluster credentials
```bash
gcloud container clusters get-credentials <CLUSTER_NAME> --project <PROJECT_ID> --region europe-west2
```
create a curl format file to display the latency results
```bash
cat > curl-format.txt << EOL
           http_code:  %{http_code}\n
       response_code:  %{response_code}\n
              method:  %{method}\n
            errormsg:  %{errormsg}\n
            time_dns:  %{time_namelookup}s\n
     time_namelookup:  %{time_namelookup}s\n
        time_connect:  %{time_connect}s\n
     time_appconnect:  %{time_appconnect}s\n
    time_pretransfer:  %{time_pretransfer}s\n
       time_redirect:  %{time_redirect}s\n
  time_starttransfer:  %{time_starttransfer}s\n
                     ----------\n
          time_total:  %{time_total}s\n
EOL
```
set some env vars and get the pod name to port forward to. The example below is for the collection-exercise service in the dev namespace.
```bash
export NAMESPACE=dev
export SERVICE=collection-exercise
export LOCAL_PORT=8145
export POD=$(kubectl get pods --namespace $NAMESPACE | grep $SERVICE | head -1 | awk '{print $1;}')

echo $SERVICE
echo $NAMESPACE
echo $POD
echo $LOCAL_PORT
```
check the echoed env vars above are correct before port forwarding to the pod container. **NOTE**: some services have scheduled jobs that might be returned by the grep command above. If this is the case, you will need to get the pod name manually. 
```bash
kubectl port-forward --namespace $NAMESPACE $POD $LOCAL_PORT:8080
```
in a second terminal window run the curl command below, for example
```bash
export NAMESPACE=dev
export REQUEST_URL=http://localhost:8145/collectionexercises/221_201712/survey/221
```
or
```bash
export NAMESPACE=preprod
export REQUEST_URL=http://localhost:8002/collection-instrument-api/1.0.2/download/d424e18c-4183-4b49-acce-0da9ee56a83f
```
then run the curl command
```bash
curl -w "@curl-format.txt" -o /dev/null -s --location "$REQUEST_URL" \
-u $(kubectl get secret security-credentials -o json --namespace=$NAMESPACE | \
jq -r '.data."security-user"' | base64 -d):$(kubectl get secret security-credentials -o json --namespace=$NAMESPACE | \
jq -r '.data."security-password"' | base64 -d)
```
