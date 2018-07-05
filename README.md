# ras-rm-performance-tests
Performance Test Scripts


## Running load tests locally

First run the server
```bash
SERVER_PORT=1234 apache-jmeter-3.1/bin/jmeter-server -Jserver.rmi.localport=1235 -Jclient.rmi.localport=1236
```

Then trigger the tests against the Server (replacing `-R localhost:1235` with `-R your-ip:1235`)

```bash
$ apache-jmeter-3.1/bin/jmeter.sh \
      -Jclient.rmi.localport=1236 \
      -n -r \
      -R localhost:1235 \
      -t ras-rm-performance-tests/JMeter/Plans/Frontstage_R16.jmx
Writing log file to: /Users/patelt/projects/ras-rm-performance-tests/JMeter/jmeter.log
Creating summariser <summary>
Created the tree successfully using /Users/patelt/projects/ras-rm-performance-tests/JMeter/Plans/Frontstage_R16.jmx
Configuring remote engine: localhost:1234
Starting remote engines
Starting the test @ Thu Jul 05 11:32:36 BST 2018 (1530786756498)
Remote engines have been started
Waiting for possible Shutdown/StopTestNow/Heapdump message on port 4445
summary =      0 in 00:00:00 = ******/s Avg:     0 Min: 9223372036854775807 Max: -9223372036854775808 Err:     0 (0.00%)
Tidying up remote @ Thu Jul 05 11:32:37 BST 2018 (1530786757769)
... end of run
```
